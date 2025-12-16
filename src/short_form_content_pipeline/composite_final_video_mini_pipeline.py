import datetime
import json
import os
import random

import PIL.Image
from moviepy.video.fx.speedx import speedx

from src.short_form_content_pipeline.Util_functions import display_print_ffmpeg_metadata_parameters, \
    set_debug_dir_for_module_of_pipeline

# important: register ANTIALIAS as LANCZOS for Pillow 10.x compatibility
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

import ffmpeg
from moviepy.editor import VideoFileClip, CompositeVideoClip, AudioFileClip, TextClip
from moviepy.video.fx.all import crop, resize, mirror_x # if the imports are red, it is fine to ignore


from src.short_form_content_pipeline.generate_subtitle_clip_moviepy import generate_speed_adjusted_subtitle_clips_moviepy_obj

# ==========================================
#        PRIVATE SUB-FUNCTIONS
# ==========================================


def _scan_media_folder(folder_path, minimum_time_s: float=90, allowed_exts=('.webm', '.mp4', '.mkv')):
    """
    Scans the folder and returns a list of dicts:
    [{'path': '...', 'duration': 1200}, ...]
    """
    valid_videos = []
    print(f"   📂 Scanning media folder: {folder_path}")

    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Media folder not found: {folder_path}")

    for file in os.listdir(folder_path):
        if file.lower().endswith(allowed_exts):
            full_path = os.path.join(folder_path, file)
            try:
                # Quick probe to get duration without loading the full clip
                probe = ffmpeg.probe(full_path)
                duration = float(probe['format']['duration'])

                # Only accept videos longer than the requested minimum
                if duration > minimum_time_s:
                    valid_videos.append({'path': full_path, 'duration': duration})
            except Exception as e:
                print(f"   ⚠️ Skipping broken file {file}: {e}")

    if not valid_videos:
        raise Exception("No valid video files found in media folder!")

    print(f"      Found {len(valid_videos)} valid background videos.")
    return valid_videos

def _select_weighted_random_video(video_list):
    """
    Selects a video. Longer videos have a higher probability of being chosen.
    Logic: Probability = Duration / Total_Duration
    """
    total_duration = sum(v['duration'] for v in video_list)
    pick = random.uniform(0, total_duration)
    current = 0

    selected_video = video_list[0] # Fallback
    for vid in video_list:
        current += vid['duration']
        if current > pick:
            selected_video = vid
            break

    print(f"    Randomly Selected BG Video: {os.path.basename(selected_video['path'])} ({int(selected_video['duration']/60)} mins)")
    return selected_video

def _prepare_background_clip(video_info, target_duration, target_resolution=(1080, 1920)):
    """
    Loads video, selects random segment, mirror flips (anti-copyright), crops to 9:16.
    """
    vid_path = video_info['path']
    vid_duration = video_info['duration']

    # Random Start Time
    # Ensure we don't pick a start time too close to the end
    max_start = vid_duration - target_duration - 5 # 5s buffer

    # not gonna happen since we already checked earlier but just in case
    if max_start < 0:
        raise Exception("Background video is shorter than the script audio!")

    start_time = random.uniform(0, max_start)
    end_time = start_time + target_duration

    print(f"      Cutting segment from video: {int(start_time)}s to {int(end_time)}s")

    # Load & Process with MoviePy
    # Load only the specific chunk to save memory
    clip = VideoFileClip(vid_path).subclip(start_time, end_time)

    # Mirror Flip
    # Randomly decide to flip or not (adds more variance)
    if random.choice([True, False]):
        clip = mirror_x(clip)

    # Resize & Crop to 9:16 (Vertical)
    # Logic: Resize height to 1920 (target H), then crop width to 1080 (target W)
    # We use 'height=1920' which maintains aspect ratio, so width becomes > 1080
    clip_resized = resize(clip, height=target_resolution[1])

    # Center Crop
    clip_final = crop(clip_resized,
                      width=target_resolution[0],
                      height=target_resolution[1],
                      x_center=clip_resized.w / 2,
                      y_center=clip_resized.h / 2)

    return clip_final




# ==========================================
#        PUBLIC ORCHESTRATOR
# ==========================================

def run_composite_final_video_pipeline(
        media_folder,
        normal_speed_audio_file_path,
        sped_up_audio_file_path,
        bg_video_speed_factor: float,
        subtitle_clips_speed_adjusted,
        temp_processing_dir,
        output_dir,
):
    """
    Orchestrator to build the final vertical video.
    """
    print("\n5. 🏗️ Assembling Final Video...")

    # Get audio duration (needed for BG video selection)
    # using a context manager to ensure file handles are closed immediately
    with AudioFileClip(normal_speed_audio_file_path) as temp_clip:
        original_audio_duration = temp_clip.duration

    # Select bg video & Prepare background clip (1x normal speed at first)
    available_videos = _scan_media_folder(
        folder_path=media_folder,
        minimum_time_s=original_audio_duration
    )
    selected_video_info = _select_weighted_random_video(available_videos)

    background_clip = _prepare_background_clip(
        video_info=selected_video_info,
        target_duration=original_audio_duration
    )

    # Mute Background Video (setting audio to None first to remove game sounds)
    background_clip = background_clip.without_audio()

    # Apply speed adjustment ONLY to the background clip since the subtitles are already sped up
    background_clip_speed_adjusted = background_clip.fx(speedx, factor=bg_video_speed_factor)

    # Composite BG and Subtitles (both at the same speed now)
    # background is at bottom, subs on top
    final_composite_video = CompositeVideoClip(
        [background_clip_speed_adjusted] + subtitle_clips_speed_adjusted
    )

    # Load the sped-up audio file
    sped_up_audio_clip = AudioFileClip(sped_up_audio_file_path)

    # Merge the just sped-up video & pre-sped-up audio
    # trim any tiny floating point excesses to match audio exactly to avoid black frames at end
    final_composite_video = final_composite_video.set_duration(sped_up_audio_clip.duration)
    final_composite_video = final_composite_video.set_audio(sped_up_audio_clip)

    print("   💾 Rendering composite video (bg gameplay + subtitles + audio)...")


    # Generate timestamp: YearMonthDay_HourMinuteSecond (e.g., 20231203_193045) to put at the end of a file name
    timestamp_for_video = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # first datetime is module name, 2nd datetime is class name
    final_output_video_file_name = os.path.join(output_dir, f"UploadReady_{timestamp_for_video}.mp4")

    final_composite_video.write_videofile(
        filename=final_output_video_file_name,
        fps=30,
        codec='h264_videotoolbox',
        audio_codec='aac',
        threads=4,
        logger='bar',
    )

    print(f"\n🎉 VIDEO GENERATION COMPLETE: {final_output_video_file_name}")
    return final_output_video_file_name



#=========== Debug run

if __name__ == "__main__":


    # Get the absolute path of the folder containing THIS script (src/xxx)
    this_script_dir = os.path.dirname(os.path.abspath(__file__))
    # Navigate up two levels to finding media_resources. `..` goes up one level. need do it twice.
    MEDIA_RESOURCES_DIR = os.path.join(this_script_dir, "..", "..", "media_resources")
    # Normalize the path to clean up any '..' (Optional but good for debugging)
    MEDIA_RESOURCES_DIR = os.path.normpath(MEDIA_RESOURCES_DIR)

    debug_audio_dir = "___debug_dir/_d_audio_generation"
    debug_audio_file_1x_speed = os.path.join(debug_audio_dir, "raw_original_audio_1x.wav")
    debug_audio_file_sped_up = os.path.join(debug_audio_dir, "narration_audio_sped_up_1.3x.wav")

    sub_debug_dir_for_this = "_d_composite_final_video_pipeline"
    full_debug_dir = set_debug_dir_for_module_of_pipeline(sub_debug_dir_for_this)

    # load word data json file to generate transcript data
    with open("___debug_dir/_d_mfa_pipeline/mfa_aligned_transcript_1x_speed_data.json", 'r', encoding='utf-8') as f:
        aligned_word_data = json.load(f)

    list_of_debug_moviepyTextClips = generate_speed_adjusted_subtitle_clips_moviepy_obj(
        word_data_for_normal_speed_dict=aligned_word_data,
        speed_factor=1.3
    )

    final_video_path = run_composite_final_video_pipeline(
        media_folder=MEDIA_RESOURCES_DIR,
        normal_speed_audio_file_path=debug_audio_file_1x_speed,
        sped_up_audio_file_path=debug_audio_file_sped_up,
        bg_video_speed_factor=1.3,
        subtitle_clips_speed_adjusted=list_of_debug_moviepyTextClips,
        temp_processing_dir=full_debug_dir,
        output_dir=full_debug_dir,  # this is fine since this is testing
    )



