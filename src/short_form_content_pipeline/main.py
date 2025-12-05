import asyncio
import json
import os
import subprocess
import moviepy.video.fx.all as vfx

from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_merge_video_audio
from proglog.proglog import SETTINGS

from src.short_form_content_pipeline.composite_final_video_mini_pipeline import run_composite_final_video_pipeline
from src.short_form_content_pipeline.generate_audio_from_script import generate_audio_narration_file_th
from src.short_form_content_pipeline.generate_script_text import generate_script_data_json, translate_text_to_eng
from src.short_form_content_pipeline.generate_subtitle_clip_moviepy import generate_subtitle_clips_moviepy_obj, _create_debug_subtitle_clip
from src.short_form_content_pipeline.mfa_transcript_alignment_mini_pipeline import run_mfa_pipeline


""" ========== 0. Initialize Settings and Configurations =========="""
from src.short_form_content_pipeline._CONFIG import SETTINGS
SETTINGS.load_profile("thai_funny_story.yaml")

# --- commonly used variables
language = SETTINGS.content.language
gemini_api_key = SETTINGS.GEMINI_API_KEY

# ---  Define Directories and files
# Get the directory where 'main.py' is actually located
cwd_PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))

# Name of the folder that have the temp working files
TEMP_PROCESSING_DIR = SETTINGS.temp_processing_dir_name

# Join it with the cwd so that the files won't be created in the project root
TEMP_PROCESSING_DIR = os.path.join(cwd_PIPELINE_DIR, TEMP_PROCESSING_DIR)

os.makedirs(TEMP_PROCESSING_DIR, exist_ok=True) # create the folder if it doesn't exist

## Media file path
# Get the absolute path of the folder containing THIS script (src/short_form...)
this_script_dir = os.path.dirname(os.path.abspath(__file__))
# Navigate up two levels to finding media_resources. `..` goes up one level. need do it twice.
MEDIA_RESOURCES_DIR = os.path.join(this_script_dir, "..", "..", "media_resources")
# Normalize the path to clean up any '..' (Optional but good for debugging)
MEDIA_RESOURCES_DIR = os.path.normpath(MEDIA_RESOURCES_DIR)

OUTPUT_DIR = os.path.join(this_script_dir, SETTINGS.output_dir_name)


def main():
    """
    main entry point of the automated content farm
    """

    """ ========== 1. Generate Script ====================="""
    # Use "random viral story" to let Gemini be creative
    original_script_content_data_json = asyncio.run(
        generate_script_data_json(
            language=language,
            topic= SETTINGS.content.topic,
            time_length=SETTINGS.content.time_length,
            gemini_model_id=SETTINGS.content.script_ai_model,
            gemini_api_key= gemini_api_key,
            temperature=SETTINGS.script_generation_temperature,
            output_folder_path=TEMP_PROCESSING_DIR,
        )
    )

    # translate to English so that I can understand
    if original_script_content_data_json is not None:
        asyncio.run(
            translate_text_to_eng(
                non_english_content=original_script_content_data_json,
                language=language,
                gemini_api_key=gemini_api_key,
                gemini_model_id=SETTINGS.content.translation_ai_model,
            )
        )
    else:
        print("❌ Script generation or translation failed. Stopping pipeline.")
        return


    """ ========= 2. Generate Audio ===================== """
    narration_audio_file = asyncio.run(
        generate_audio_narration_file(
            script_data=original_script_content_data_json,
            output_folder_path=TEMP_PROCESSING_DIR,
            language=language,
            tts_provider=SETTINGS.tts_provider,
            gemini_api_key=gemini_api_key,
            audio_ai_model=SETTINGS.audio.audio_ai_model,
            speed_factor=SETTINGS.audio.audio_speed_factor,
        )
    )


    """ ========== 3. Generate transcript with timestamps for dynamic video subtitles via MFA"""

    aligned_transcript_word_and_time_data = run_mfa_pipeline(
        raw_script_text_from_json=original_script_content_data_json.get('script_thai'),
        audio_file_path=narration_audio_file,
        output_dir=TEMP_PROCESSING_DIR
    )


    """ =========== 4. Generate subtitle clips"""
    list_of_moviepyTextClips = generate_subtitle_clips_moviepy_obj(
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
