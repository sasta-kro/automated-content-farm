import datetime
import json
import os
import random

import PIL.Image
from moviepy.video.fx.speedx import speedx

from src.v2_thai.Util_functions import display_print_ffmpeg_metadata_parameters

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

def _create_sped_up_audio_file(original_audio_input_path, output_dir, speed_factor):
    """
    Uses FFmpeg 'atempo' to create a high-quality sped-up audio file.
    Returns the duration of the new file for precise syncing, and file path
    Returns: (output_file_path, new_duration)
    """
    print(f"   🔊 Generating sped-up audio ({speed_factor}x)...")

    # extracting extension from the original audio (.mp3, .wav)
    _, audio_extension = os.path.splitext(original_audio_input_path)

    # Calculate filter string. 'atempo' only accepts 0.5 to 2.0.
    # If speed > 2.0, we would need to chain them, but for 1.3 it's fine.
    sped_up_audio_file_path = os.path.join(
        output_dir, f"sped up {speed_factor} audio{audio_extension}"
    )


    try:
        stream = ffmpeg.input(original_audio_input_path)
        stream = ffmpeg.filter(stream, 'atempo', speed_factor)

        # Note: 'b:a': '192k' sets bitrate. If using WAV, FFmpeg usually ignores this and defaults to PCM (lossless)
        out = ffmpeg.output(stream, sped_up_audio_file_path, **{'b:a': '192k'})
        ffmpeg.run(out, overwrite_output=True, quiet=True)

        # Get exact duration of new file for precision sync
        probe = ffmpeg.probe(sped_up_audio_file_path)
        new_duration = float(probe['format']['duration'])
        return sped_up_audio_file_path, new_duration

    except ffmpeg.Error as e:
        print(f"   ❌ Audio Speedup Failed: {e.stderr.decode('utf8')}")
        raise e


def _prepare_final_audio_and_sync_factor(original_audio_path, output_dir, target_speed_factor, original_duration):
    """
    Handles audio speedup logic.
    Returns: (AudioFileClip object, float sync_factor)
    """
    # Case A: No speed up needed
    if target_speed_factor == 1.0:
        print("   🔊 Audio speed is 1.0x (No change).")
        return AudioFileClip(original_audio_path), 1.0

    # Case B: Speed up required
    sped_up_audio_path, new_duration = _create_sped_up_audio_file(
        original_audio_input_path=original_audio_path,
        output_dir=output_dir,
        speed_factor=target_speed_factor
    )

    # Calculate Precision Sync Factor
    # We use the ratio of (Old / New) to ensure the video stretches exactly to the audio's end
    sync_factor = original_duration / new_duration

    return AudioFileClip(sped_up_audio_path), sync_factor


def _generate_organic_metadata_params():
    """
    Generates FFmpeg flags to make the video file appear to have been
    created by a human editor at a specific location in Thailand (AU),
    using various software, sometime in the last 10 days.
    """
    params = []

    # CLEANING: Strip original metadata
    # This removes the 'original' camera data from the source clips
    params.extend(["-map_metadata", "-1"])

    # LOCATION: Assumption University (Suvarnabhumi Campus) + Random Jitter
    # Center coords: 13.6121° N, 100.8369° E
    # 1km is roughly 0.009 degrees lat/lon in Thailand
    base_lat = 13.6121
    base_lon = 100.8369

    # Random offset between -1km and +1km
    lat_offset = random.uniform(-0.009, 0.009)
    lon_offset = random.uniform(-0.009, 0.009)

    final_lat = base_lat + lat_offset
    final_lon = base_lon + lon_offset

    # Format as ISO 6709: +13.6121+100.8369/
    location_string = f"{final_lat:+.4f}{final_lon:+.4f}/"
    params.extend(["-metadata", f"location={location_string}"])

    if random.random() > 0.5:
        params.extend(["-metadata", "location-eng=Bangkok, Thailand"])
    else:
        params.extend(["-metadata", "location-eng=Bang Sao Thong, Samut Prakan"])


    # TIME: Random creation time (Now minus 0 to 240 hours)
    seconds_back = random.randint(0, 240 * 3600)
    fake_creation_dt = datetime.datetime.now() - datetime.timedelta(seconds=seconds_back)
    fake_creation_str = fake_creation_dt.strftime("%Y-%m-%d %H:%M:%S")

    params.extend(["-metadata", f"creation_time={fake_creation_str}"])

    # SOFTWARE SPOOFING: Hide the fact that this is Python/FFmpeg
    # We rotate through common "Human" video editors so not every file looks identical.
    human_editors = [
        "Adobe Premiere Pro 2023.0 (Windows)",
        "DaVinci Resolve Studio 18.5",
        "CapCut for Windows 2.5.0",
        "Final Cut Pro 10.6.5",
        "Sony Vegas Pro 20.0",

        # Mobile (Android/iOS style signatures)
        "CapCut 9.6.0 (Android)",
        "InShot Pro 1.952.1415 (Android)",
        "KineMaster 7.2.5.30855.GP",
        "VN Video Editor 2.1.5 (iOS)",
        "Splice - Video Editor & Maker 5.1 (iOS)"
    ]
    fake_software = random.choice(human_editors)

    # Note: 'encoder' tag often persists as Lavf in stream info, but 'tool'
    # or 'software' tags in the container can be overwritten.
    params.extend(["-metadata", f"encoder={fake_software}"])
    params.extend(["-metadata", f"software={fake_software}"])
    params.extend(["-metadata", f"comment=Rendered at {fake_creation_str}"])


    # Project Name metadata (names usually look like "Final", "Edit 2", "Project 4", etc.)
    project_names = ["Final Cut", "Vlog_Export", "Project 1", "My Video", "Edit_v2", "Render 1"]
    fake_title = random.choice(project_names)
    params.extend(["-metadata", f"title={fake_title}"])

    # If it's a mobile editor, often 'make' and 'model' tags persist from the phone
    if "Android" in fake_software or "iOS" in fake_software:
        phones = [("Apple", "iPhone 14 Pro"), ("Samsung", "Galaxy S23 Ultra"), ("Google", "Pixel 7")]
        make, model = random.choice(phones)
        params.extend(["-metadata", f"make={make}"])
        params.extend(["-metadata", f"model={model}"])

    # STRUCTURE: Web Optimization
    # This moves the MOOV atom to the front (faststart).
    # Almost all 'human' export settings check this box for web compatibility.
    params.extend(["-movflags", "+faststart"])

    return params



# ==========================================
#        PUBLIC ORCHESTRATOR
# ==========================================

def run_composite_final_video_pipeline(
        media_folder,
        audio_file_path,
        subtitle_clips,
        temp_processing_dir,
        output_dir,
        final_speed_factor=1.3
):
    """
    Orchestrator to build the final vertical video.
    """
    print("\n5. 🏗️ Assembling Final Video...")

    # Get audio duration (needed for BG video selection)
    # using a context manager or close immediately to free the file handle (idk what this means)
    with AudioFileClip(audio_file_path) as temp_clip:
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

    # Composite BG and Subtitles
    # background is at bottom, subs on top
    bg_and_subtitles_clip_normal_speed = CompositeVideoClip([background_clip] + subtitle_clips)


    # Prepare Final Audio & Sync Factor
    sped_up_audio_clip, sync_speed_factor = _prepare_final_audio_and_sync_factor(
        original_audio_path=audio_file_path,
        output_dir=temp_processing_dir,
        target_speed_factor=final_speed_factor,
        original_duration=original_audio_duration
    )

    # Apply Speed Effects to Video
    if sync_speed_factor != 1.0:
        final_composite_video = bg_and_subtitles_clip_normal_speed.fx(speedx, factor=sync_speed_factor)
    else:
        final_composite_video = bg_and_subtitles_clip_normal_speed


    # Merge video & audio and render
    # trim any tiny floating point excesses to match audio exactly
    final_composite_video = final_composite_video.set_duration(sped_up_audio_clip.duration)
    final_composite_video = final_composite_video.set_audio(sped_up_audio_clip)

    print("   💾 Rendering composite video (bg gameplay + subtitles + audio)...")


    # Generate timestamp: YearMonthDay_HourMinuteSecond (e.g., 20231203_193045) to put at the end of a file name
    timestamp_for_video = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # first datetime is module name, 2nd datetime is class name
    final_output_video_file_name = os.path.join(output_dir, f"FINAL_UPLOAD_READY_{timestamp_for_video}.mp4")


    ffmpeg_organic_params = _generate_organic_metadata_params()
    display_print_ffmpeg_metadata_parameters(ffmpeg_organic_params)  # for the pretty prints

    final_composite_video.write_videofile(
        filename=final_output_video_file_name,
        fps=30,
        codec='libx264',
        audio_codec='aac',
        threads=4,
        logger='bar',
        ffmpeg_params=ffmpeg_organic_params
    )

    print(f"\n🎉 VIDEO GENERATION COMPLETE: {final_output_video_file_name}")
    return final_output_video_file_name



#=========== Debug run

if __name__ == "__main__":


    # Get the absolute path of the folder containing THIS script (src/v2_thai)
    this_script_dir = os.path.dirname(os.path.abspath(__file__))
    # Navigate up two levels to finding media_resources. `..` goes up one level. need do it twice.
    MEDIA_RESOURCES_DIR = os.path.join(this_script_dir, "..", "..", "media_resources")
    # Normalize the path to clean up any '..' (Optional but good for debugging)
    MEDIA_RESOURCES_DIR = os.path.normpath(MEDIA_RESOURCES_DIR)

    debug_audio_file = "correct_test_files/raw_original_audio.wav"

    temp_processing_dir = "___debug_composite_final_video"
    os.makedirs(temp_processing_dir, exist_ok=True) # create the folder


    # load word data json file to generate transcript data
    with open("correct_test_files/mfa_aligned_transcript_data.json", 'r', encoding='utf-8') as f:
        aligned_word_data = json.load(f)

    list_of_debug_moviepyTextClips = generate_subtitle_clips_data(
        word_data_dict=aligned_word_data
    )

    final_video_path = run_composite_final_video_pipeline(
        media_folder=MEDIA_RESOURCES_DIR,
        audio_file_path=debug_audio_file,
        subtitle_clips=list_of_debug_moviepyTextClips,
        temp_processing_dir=temp_processing_dir,
        output_dir=temp_processing_dir,  # this is fine since this is testing
        final_speed_factor=1.3
    )



