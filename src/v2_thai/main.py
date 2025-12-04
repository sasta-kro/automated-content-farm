import asyncio
import json
import os
import subprocess

import moviepy.video.fx.all as vfx


from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_merge_video_audio

from src.v2_thai.composite_final_video_mini_pipeline import run_composite_final_video_pipeline
from src.v2_thai.generate_audio_th_from_script import generate_audio_narration_file_th
from src.v2_thai.generate_script_th import generate_thai_script_data, translate_thai_content_to_eng
from src.v2_thai.generate_subtitle_clip import generate_subtitle_clips_data, _create_debug_subtitle_clip
from src.v2_thai.mfa_transcript_alignment_mini_pipeline import run_mfa_pipeline

## Define Directories and files

# Get the directory where 'main.py' is actually located
cwd_PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))

# Name of the folder that have the temp working files
TEMP_PROCESSING_DIR = "___0w0__temp_automation_workspace"

# Join it with the cwd so that the files won't be created in the project root
TEMP_PROCESSING_DIR = os.path.join(cwd_PIPELINE_DIR, TEMP_PROCESSING_DIR)

os.makedirs(TEMP_PROCESSING_DIR, exist_ok=True) # create the folder

## Media file path
# Get the absolute path of the folder containing THIS script (src/v2_thai)
this_script_dir = os.path.dirname(os.path.abspath(__file__))
# Navigate up two levels to finding media_resources. `..` goes up one level. need do it twice.
MEDIA_RESOURCES_DIR = os.path.join(this_script_dir, "..", "..", "media_resources")
# Normalize the path to clean up any '..' (Optional but good for debugging)
MEDIA_RESOURCES_DIR = os.path.normpath(MEDIA_RESOURCES_DIR)

OUTPUT_DIR = ""


def main():
    """
    main entry point of the automated content farm
    """

    """ ========== 1. Generate Script ====================="""
    # Use "random viral story" to let Gemini be creative
    original_script_content_data_json = asyncio.run(
        generate_thai_script_data(
            topic= "i accidentally shat in the urinal",
            time_length="25-35",   # TODO: don't forget to change this
            output_folder_path=TEMP_PROCESSING_DIR
        )
    )

    # translate to English so that I can understand
    if original_script_content_data_json is not None:
        asyncio.run(
            translate_thai_content_to_eng(original_script_content_data_json)
        )
    else:
        print("❌ Script generation or translation failed. Stopping pipeline.")
        return


    """ ========= 2. Generate Audio ===================== """
    narration_audio_file = asyncio.run(
        generate_audio_narration_file_th(
            script_data=original_script_content_data_json,
            output_folder_path=TEMP_PROCESSING_DIR,
            use_gemini=True
        )
    )


    """ ========== 3. Generate transcript with timestamps for dynamic video subtitles via MFA"""

    aligned_transcript_word_and_time_data = run_mfa_pipeline(
        raw_script_text_from_json=original_script_content_data_json.get('script_thai'),
        audio_file_path=narration_audio_file,
        output_dir=TEMP_PROCESSING_DIR
    )


    """ =========== 4. Generate subtitle clips"""
    list_of_moviepyTextClips = generate_subtitle_clips_data(
        word_data_dict=aligned_transcript_word_and_time_data,
    )


    """ =========== 5. Generate The Final Video with Subtitles and Background, along with Sped up Audio  """
    final_video_file_path = run_composite_final_video_pipeline(
        media_folder=MEDIA_RESOURCES_DIR,
        audio_file_path=narration_audio_file,
        subtitle_clips=list_of_moviepyTextClips,
        temp_processing_dir=TEMP_PROCESSING_DIR,
        output_dir=TEMP_PROCESSING_DIR,  # where the output video will resulp in
        final_speed_factor=1.3
    )


    print(">>> ✅ Finished generating full video with subtitles, gameplay background, and sped-up audio :D")
    print(f">>> Video file saved to {final_video_file_path} ")






# ======== EXECUTION =====
if __name__ == "__main__":
    main()
    # TODO: change font, fix sped-up error
