import asyncio
import os
import numpy as np
from moviepy.editor import TextClip, CompositeVideoClip, ColorClip, VideoFileClip


def generate_subtitle_clips(
        word_data,
        videosize=(1080, 1920),
        font="/Users/saiaikeshwetunaung/Library/Fonts/Chonburi-Regular.ttf", # OR "Prompt-Bold"
        fontsize=120,        # Thai needs slightly smaller font than Eng usually
        color='yellow',     # Yellow is standard for Thai TikTok
        stroke_width=4,
        stroke_color='black'
):
    """
    Generates a list of TextClips based on word timings.
    """
    print(f"   🎬 Generating {len(word_data)} subtitle clips...")

    text_clips = []
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
            print("Try using a generic font like 'Arial' temporarily to debug.")
            raise e

        # Position: Center of the screen
        # Timing: Set start and calculated duration
        txt_clip = txt_clip.set_position(('center', 'center')) \
            .set_start(start_time) \
            .set_duration(duration)

        text_clips.append(txt_clip)

    return text_clips

def create_debug_subtitle_clip(text_clips, output_filename="debug_test_subtitles_vid.mp4"):
    """
    Creates a black video with subtitles to test font rendering.
    """
    # 9:16 Aspect Ratio (Vertical Video)
    W, H = 1080, 1920

    # Background (white)
    # Duration = end of last word + 1 second
    bg_clip = ColorClip(size=(W, H), color=(255,255,255), duration=60.0)


    # Composite
    final_output = CompositeVideoClip([bg_clip] + text_clips)

    # Write
    print(f"   💾 Rendering debug video to {output_filename}...")
    final_output.write_videofile(output_filename, fps=24)


if __name__ == "__main__":
    # === TEST DATA (Based on your output) ===
    # "แก... เรื่องนี้พีค" (Hey... this story is peak)
    mock_word_data = [
        {'word': 'แก', 'start': 0.5, 'end': 0.9},
        {'word': '...', 'start': 0.9, 'end': 1.2},
        {'word': 'เรื่อง', 'start': 1.2, 'end': 1.6},
        {'word': 'นี้', 'start': 1.6, 'end': 1.9},
        {'word': 'พีค', 'start': 1.9, 'end': 2.5},
        {'word': 'มาก', 'start': 2.5, 'end': 3.0},
    ]

    # Run the test
    # Ensure you have the font installed or change "Chonburi-Regular" to "Arial" for testing
    text_clips = generate_subtitle_clips(mock_word_data)
    create_debug_subtitle_clip(text_clips)