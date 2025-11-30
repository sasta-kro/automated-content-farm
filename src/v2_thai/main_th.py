import asyncio
import json
import os

from src.v2_thai.generate_audio_th import generate_audio_narration_file_th
from src.v2_thai.generate_script_th import generate_thai_script_data, translate_thai_content_to_eng
from src.v2_thai.generate_subtitle_clip import generate_subtitle_clips, create_debug_subtitle_clip
from src.v2_thai.generate_transcript_for_subtitles import generate_timed_transcript_th

# Define Directories and files
TEMP_PROCESSING_DIR = "___temp_script_workspace"
os.makedirs(TEMP_PROCESSING_DIR, exist_ok=True) # create the folder


OUTPUT_DIR = ""


def main():
    """
    main function of the automated content farm
    """

    """ ========== 1. Generate Script """
    # Use "random viral story" to let Gemini be creative
    script_and_content_data_th = asyncio.run(
        generate_thai_script_data(
            topic=  "guy discovers my sister working in a brothel",
            time_length="30-45",
            output_folder=TEMP_PROCESSING_DIR
        )
    )

    # translate to English so that I can understand
    if script_and_content_data_th is not None:
        asyncio.run(
            translate_thai_content_to_eng(script_and_content_data_th)
        )


    """ ========= 2. Generate Audio """
    narration_audio_file = asyncio.run(
        generate_audio_narration_file_th(
            script_data=script_and_content_data_th,
            output_folder_path=TEMP_PROCESSING_DIR,
            use_gemini=True
        )
    )


    """ ========== 3. Generate transcription for dynamic video subtitles"""
    if os.path.exists(narration_audio_file):
        word_and_time_data = asyncio.run(
            generate_timed_transcript_th(narration_audio_file)
        )
    else:
        raise " !!! raw audio file couldn't be found"


    """ =========== 4. Generate subtitle clips"""
    subtitle_text_clips = generate_subtitle_clips(word_and_time_data)

    # temp to test out the subtitle clip
    create_debug_subtitle_clip(subtitle_text_clips)




# ======== EXECUTION =====
if __name__ == "__main__":
    main()
