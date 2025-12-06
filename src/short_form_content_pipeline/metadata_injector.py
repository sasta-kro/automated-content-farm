from pydantic_settings import BaseSettings
from src.short_form_content_pipeline._CONFIG import SETTINGS
import random
import datetime
import os
import subprocess

def _generate_organic_metadata_params(metadata_settings: BaseSettings):
    """
    Generates FFmpeg flags to make the video file appear to have been
    created by a human editor at a specific location in Thailand (AU),
    using fake metadata defined in the config profile.
    """
    params = []

    if not metadata_settings:
        raise ValueError("Metadata settings not found")

    # CLEANING: Strip original metadata
    # This removes the 'original' camera data from the source clips
    params.extend(["-map_metadata", "-1"])

    # LOCATION: Assumption University (Suvarnabhumi Campus) + Random Jitter
    base_lat = metadata_settings.base_latitude
    base_lon = metadata_settings.base_longitude

    # Random offset between -1km and +1km
    offset_radius = metadata_settings.offset_radius_km
    lat_offset = random.uniform(-offset_radius, offset_radius)
    lon_offset = random.uniform(-offset_radius, offset_radius)

    final_lat = base_lat + lat_offset
    final_lon = base_lon + lon_offset

    # Format as ISO 6709: +13.6121+100.8369/
    location_string = f"{final_lat:+.4f}{final_lon:+.4f}/"
    params.extend(["-metadata", f"location={location_string}"])
    params.extend(["-metadata", f"location-eng={metadata_settings.location_eng_tag}"])



    # TIME: Random creation time  (now - bound_hours)
    seconds_back = random.randint(0, metadata_settings.creation_time_past_bound_hr * 3600)
    fake_creation_dt = datetime.datetime.now() - datetime.timedelta(seconds=seconds_back)
    fake_creation_str = fake_creation_dt.strftime("%Y-%m-%d %H:%M:%S")

    params.extend(["-metadata", f"creation_time={fake_creation_str}"])

    # SOFTWARE SPOOFING: Hide the fact that this is Python/FFmpeg
    selected_software = random.choice(metadata_settings.editing_software_list)

    # Device Specifics
    # If it's a mobile editor, often 'make' and 'model' tags persist from the phone
    # If using desktop software (Mac), 'make'/'model' are typically empty or just "Apple"
    if "(Android)" in selected_software:
        selected_device = random.choice(metadata_settings.android_models)
        # Split "Samsung Galaxy S24" into Make/Model roughly
        parts = selected_device.split(" ", 1)
        make = parts[0] # e.g. Samsung
        model = parts[1] if len(parts) > 1 else parts[0]

        params.extend(["-metadata", f"make={make}"])
        params.extend(["-metadata", f"model={model}"])
    elif "(Macintosh)" in selected_software or "macOS" in selected_software:
        # Subtle Apple signature
        params.extend(["-metadata", "make=Apple"])
        # We don't usually see exact model "MacBook Pro" in exported files, just the software

    # PROJECT METADATA
    fake_title = random.choice(metadata_settings.editing_project_names)
    params.extend(["-metadata", f"title={fake_title}"])
    params.extend(["-metadata", f"comment=Rendered at {fake_creation_str}"])

    # WEB OPTIMIZATION (Faststart)
    # Critical for social platforms to process video quickly
    # This moves the MOOV atom to the front (faststart).
    # Almost all 'human' export settings check this box for web compatibility.
    params.extend(["-movflags", "+faststart"])

    return params



def inject_spoofed_metadata_into_video(
        SETTINGS_metadata: BaseSettings,
        video_file_path: str,
        temp_processing_dir: str,
):
    """
    Public wrapper to inject stealth metadata into an existing video file.

    How it works:
    1. Generates the 'Stealth' flags (Location, Time, Device).
    2. Runs FFmpeg in 'Stream Copy' mode (-c copy). This is instant and does NOT re-encode the video.
    3. Writes to a temp file, then overwrites the original.

    """
    if not os.path.exists(video_file_path):
        raise FileNotFoundError(f"Video file not found: {video_file_path}")

    print(f"   🕵️ Injecting Spoofed Metadata into (Bypassing anti-bot measures): {os.path.basename(video_file_path)}")

    metadata_flags = _generate_organic_metadata_params(SETTINGS_metadata)
    print("     Generated FFmpeg metadata flags:")
    print("     ".join(metadata_flags))



# Create a temporary output path and copy the file to avoid locking the file we are reading
    # because we cannot read from a file and override it at the same time
    temp_output_path = os.path.join(temp_processing_dir, f"temp_metadata_injection_file_deleted_later.mp4")

    try:
        # Construct the FFmpeg command
        # Syntax: ffmpeg -y -i [INPUT] [METADATA_FLAGS...] -c copy [OUTPUT]
        # -y: Overwrite output if exists
        # -c copy: Copy video/audio streams directly (NO RE-ENCODING)
        cmd = (
                ["ffmpeg", "-y", "-i", video_file_path]
                + metadata_flags
                + ["-c", "copy", temp_output_path]
        )

        # Execute silently
        # suppress stdout/stderr unless it fails
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT
        )

        # Overwrite the original file with the new one
        os.replace(temp_output_path, video_file_path)

        print("      ✅ Metadata injection successful.")
        return video_file_path

    except subprocess.CalledProcessError as e:
        print(f"      ❌ FFmpeg Metadata Injection Failed!")
        # Clean up temp file if it exists
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)
        raise e



# --- Debugging ---
if __name__ == "__main__":
    # Test the injection
    SETTINGS.load_profile("thai_funny_story.yaml")

    inject_spoofed_metadata_into_video(
        SETTINGS.metadata,
        "correct_test_files/upload_ready_vid_for_testing.mp4",
        "___debug_dir"
    )

