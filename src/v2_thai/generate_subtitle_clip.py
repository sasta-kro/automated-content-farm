import asyncio
import json
import os
import numpy as np
from moviepy.editor import TextClip, CompositeVideoClip, ColorClip, VideoFileClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_merge_video_audio


def generate_subtitle_clips(
        word_data,
        videosize=(1080, 1920),
        # font="/Users/saiaikeshwetunaung/Library/Fonts/Chonburi-Regular.ttf", # OR
        font= "/Users/saiaikeshwetunaung/Library/Fonts/Prompt-Bold.ttf",
        # Ansananew

        fontsize=120,        # Thai needs slightly smaller font than Eng usually
        color='yellow',     # Yellow is standard for Thai TikTok
        stroke_width=4,
        stroke_color='black',
        output_directory=""
):
    """
    Generates a list of TextClips based on word timings.
    """
    print(f"4. 🎬 Generating {len(word_data)} subtitle clips...")

    TextClips_list = []
    # Iterate through words
    for item in word_data:
        word_text = item['word']
        start_time = item['start']
        end_time = item['end']

        # Duration sanity check:
        # If a word is faster than 0.1s, it flickers too hard. We extend it slightly to make it readable.
        duration = end_time - start_time
        if duration < 0.15:
            duration = 0.15

        # Create the clip
        try:
            txt_clip = TextClip(
                word_text,
                fontsize=fontsize,
                color=color,
                font=font,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                method='label' # 'label' is faster/cleaner for short text than 'caption'
            )

        except Exception as e:
            print(f"❌ Font Error: {e}")
            raise e

        # Position: Center of the screen
        # Timing: Set start and calculated duration
        txt_clip = txt_clip.set_position(('center', 'center')) \
            .set_start(start_time) \
            .set_duration(duration)

        TextClips_list.append(txt_clip)

    return TextClips_list

def create_debug_subtitle_clip(TextClips_list, output_dir=""):
    """
    Creates a white video with subtitles to test font rendering.
    """
    W, H = 1080, 1920  # 9:16 Aspect Ratio (Vertical Video)

    # Background (white)
    # Duration = 60 seconds placeholder
    bg_clip = ColorClip(size=(W, H), color=(255,255,255), duration=60.0)


    # Composite
    final_output = CompositeVideoClip([bg_clip] + TextClips_list)

    # Write
    os.makedirs(output_dir, exist_ok=True) # create the folder if it doesn't exist
    filename = os.path.join(output_dir, "debug_test_subtitle_clip.mp4")

    print(f"   💾 Rendering debug video to {filename}...")
    final_output.write_videofile(filename, fps=24)
    return filename


# ------------------ Testing


if __name__ == "__main__":
    with open("correct_test_files/mfa_aligned_transcript_data_with_unk.json") as f:
        test_word_timestamp_data = json.load(f)

    debug_directory = "___debug_generated_subtitle_clips"

    # generate text clips
    text_clips = generate_subtitle_clips(
        word_data=test_word_timestamp_data,
        output_directory=debug_directory,
    )

    # create debug video
    create_debug_subtitle_clip(
        TextClips_list=text_clips,
        output_dir=debug_directory
    )


    # temp comment out to merge audio and video
    ffmpeg_merge_video_audio(
        video=os.path.join(debug_directory, "debug_test_subtitle_clip.mp4"),
        audio="correct_test_files/raw_original_audio_F_Gem.wav",
        output=os.path.join(debug_directory, "debug_test_subtitles_vid_with_sound.mp4"),
        vcodec='copy', # 'copy' means don't re-render video (Fast!)
        acodec='aac', # audio codec
        ffmpeg_output=False, # Hides logs
        logger=None
    )
    print(f"✅ Debug subtitle vid with sound ")