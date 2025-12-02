import asyncio
import json
import os
import subprocess

import moviepy.video.fx.all as vfx


from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_merge_video_audio

from src.v2_thai.generate_audio_th_from_script import generate_audio_narration_file_th
from src.v2_thai.generate_script_th import generate_thai_script_data, translate_thai_content_to_eng
from src.v2_thai.generate_subtitle_clip import generate_subtitle_clips, create_debug_subtitle_clip
from src.v2_thai.mfa_transcript_alignment_mini_pipeline import run_mfa_pipeline

## Define Directories and files

# Get the directory where 'main.py' is actually located
cwd_PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))

# Name of the folder that have the temp working files
TEMP_PROCESSING_DIR = "___0w0__temp_automation_workspace"

# Join it with the cwd so that the files won't be created in the project root
TEMP_PROCESSING_DIR = os.path.join(cwd_PIPELINE_DIR, TEMP_PROCESSING_DIR)

os.makedirs(TEMP_PROCESSING_DIR, exist_ok=True) # create the folder

OUTPUT_DIR = ""


def main():
    """
    main function of the automated content farm
    """

    """ ========== 1. Generate Script ====================="""
    # Use "random viral story" to let Gemini be creative
    original_script_content_data_json = asyncio.run(
        generate_thai_script_data(
            topic=  "found my dad in a gay bar",
            time_length="15-20",   # TODO: don't forget to change this
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


    # TODO: the without_unkfix one is better, i just need to replace the unk with ... in a post processing function
    # i plan to archive both and make a new file with 'unkfix' and modify it to just replace unk with `...`


    """ =========== 4. Generate subtitle clips"""
    list_of_moviepyTextClips = generate_subtitle_clips(
        word_data=aligned_transcript_word_and_time_data,
        output_directory=TEMP_PROCESSING_DIR,
    )

    # temp to test out the subtitle clip
    test_subtitle_clip_file = create_debug_subtitle_clip(
        TextClips_list=list_of_moviepyTextClips,
        output_dir=TEMP_PROCESSING_DIR
    )

    # temp to test out the sutitle clip with sound
    ffmpeg_merge_video_audio(
        video=test_subtitle_clip_file,
        audio=narration_audio_file,
        output=os.path.join(TEMP_PROCESSING_DIR, "test_temp_subtitles_vid_with_sound.mp4"),
        vcodec='copy', # 'copy' means don't re-render video (Fast!)
        acodec='aac', # audio codec
        ffmpeg_output=False, # Hides logs
        logger=None
    )
    print(">>> ✅ finished combing subtitle clip with audio narration :D")





# ======== EXECUTION =====
if __name__ == "__main__":
    main()

