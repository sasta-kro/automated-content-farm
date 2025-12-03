import json
import os
import random

import PIL.Image
# FIX: Register ANTIALIAS as LANCZOS for Pillow 10.x compatibility
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

import ffmpeg
from moviepy.editor import VideoFileClip, CompositeVideoClip, AudioFileClip, TextClip
from moviepy.video.fx.all import crop, resize, mirror_x


from src.v2_thai.generate_subtitle_clip import generate_subtitle_clips_data

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

                # Only accept videos longer than 2 minutes to ensure we have wiggle room
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

    # Mirror Flip (Anti-Copyright Technique #1)
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

def assemble_final_video_with_bg_subtitle_audio(
        media_folder,
        audio_file_path,
        subtitle_clips,
        output_dir,
        final_speed_factor=1.3
):
    """
    Orchestrator to build the final vertical video.
    """
    print("\n4. 🏗️ Assembling Final Video...")

    # Get Audio Duration to get time length for bg video
    audio_clip = AudioFileClip(audio_file_path)
    content_duration: float = audio_clip.duration

    # Select bg video & Prepare background clip
    available_videos = _scan_media_folder(
        folder_path=media_folder,
        minimum_time_s=content_duration
    )
    selected_video_info = _select_weighted_random_video(available_videos)

    background_clip = _prepare_background_clip(
        video_info=selected_video_info,
        target_duration=content_duration
    )

    # Mute Background Video & Attach Narration
    # We set audio to None first to remove game sounds, then set new audio
    background_clip = background_clip.without_audio()
    background_clip = background_clip.set_audio(audio_clip)

    # Composite (Overlay Subtitles)
    # Background is at bottom, subs on top
    final_composite = CompositeVideoClip([background_clip] + subtitle_clips)

    # Render Initial Version (Normal Speed)
    temp_normal_speed_video_path = os.path.join(output_dir, "temp_render_normal_speed.mp4")
    print("   💾 Rendering composite video (bg gameplay + subtitles + audio)...")

    final_composite.write_videofile(
        temp_normal_speed_video_path,
        fps=30,
        codec='libx264',
        audio_codec='aac',
        threads=4,
        logger=None # Hide massive progress bar logs if desired, or use 'bar'
    )



    print(f"\n🎉 VIDEO GENERATION COMPLETE: {temp_normal_speed_video_path}")
    return temp_normal_speed_video_path



#=========== Debug run

if __name__ == "__main__":


    # Get the absolute path of the folder containing THIS script (src/v2_thai)
    this_script_dir = os.path.dirname(os.path.abspath(__file__))
    # Navigate up two levels to finding media_resources. `..` goes up one level. need do it twice.
    MEDIA_RESOURCES_DIR = os.path.join(this_script_dir, "..", "..", "media_resources")
    # Normalize the path to clean up any '..' (Optional but good for debugging)
    MEDIA_RESOURCES_DIR = os.path.normpath(MEDIA_RESOURCES_DIR)

    debug_audio_file = "correct_test_files/raw_original_audio.wav"

    output_path = "___debug_composite_final_video"
    os.makedirs(output_path, exist_ok=True) # create the folder


    # load word data json file to generate transcript data
    with open("correct_test_files/mfa_aligned_transcript_data.json", 'r', encoding='utf-8') as f:
        aligned_word_data = json.load(f)

    list_of_debug_moviepyTextClips = generate_subtitle_clips_data(
        word_data_dict=aligned_word_data
    )

    final_video_path = assemble_final_video_with_bg_subtitle_audio(
        media_folder=MEDIA_RESOURCES_DIR,
        audio_file_path=debug_audio_file,
        subtitle_clips=list_of_debug_moviepyTextClips,
        output_dir=output_path,
        final_speed_factor=1.3
    )



