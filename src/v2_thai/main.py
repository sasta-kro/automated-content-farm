import asyncio
import json
import os

from moviepy.video.io.ffmpeg_tools import ffmpeg_merge_video_audio

from src.v2_thai.align_transcription_to_script import align_transcription_to_script_and_correct_timestamps
from src.v2_thai.generate_audio_th import generate_audio_narration_file_th
from src.v2_thai.generate_script_th import generate_thai_script_data, translate_thai_content_to_eng
from src.v2_thai.generate_subtitle_clip import generate_subtitle_clips, create_debug_subtitle_clip
from src.v2_thai.generate_transcript_for_subtitles import generate_whisper_timed_transcript_th

# Define Directories and files
TEMP_PROCESSING_DIR = "___temp_script_workspace"
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
            topic=  "guy discovers my sister working in a brothel",
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


    """ ========== 3. Generate transcription for dynamic video subtitles"""
    if os.path.exists(narration_audio_file):
        whisper_extracted_raw_word_and_time_data = asyncio.run(
            generate_whisper_timed_transcript_th(
                audio_file_path=narration_audio_file,
                output_folder_path=TEMP_PROCESSING_DIR,
            )
        )
    else:
        raise " !!! raw audio file couldn't be found"


    """ =========== 3.5 Align the Transcription to the Original Script and Correct Timestamps to word-level instead of char"""
    aligned_transcript_word_and_time_data = align_transcription_to_script_and_correct_timestamps(
        original_script= original_script_content_data_json['script_thai'] ,
        whisper_word_data=whisper_extracted_raw_word_and_time_data,
        output_folder_path=TEMP_PROCESSING_DIR
    )

    """ =========== 4. Generate subtitle clips"""
    subtitle_text_clips = generate_subtitle_clips(aligned_transcript_word_and_time_data)

    # temp to test out the subtitle clip
    create_debug_subtitle_clip(subtitle_text_clips)






# ======== EXECUTION =====
if __name__ == "__main__":
    main()

    # # temp comment out to merge audio and video
    # ffmpeg_merge_video_audio(
    #     video="debug_test_subtitles_vid.mp4",
    #     audio="___temp_script_workspace/spedup_audio_narration.mp3",
    #     output="debug_subtitle_vid_with_audio.mp4",
    #     vcodec='copy', # 'copy' means don't re-render video (Fast!)
    #     acodec='aac', # audio codec
    #     ffmpeg_output=False, # Hides logs
    #     logger=None
    # )
    # print(f"✅ Final Video")
