import asyncio
import json
import os
import numpy as np
from PIL import ImageFont, Image, ImageDraw
from moviepy.editor import TextClip, CompositeVideoClip, ColorClip, VideoFileClip
from moviepy.video.VideoClip import ImageClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_merge_video_audio

from src.short_form_content_pipeline.Util_functions import set_debug_dir_for_module_of_pipeline


def _create_pil_text_clip(text, font_path, fontsize, color, stroke_color, stroke_width):
    """
    Generates a MoviePy ImageClip using Pillow for better font rendering (Thai support).
    """
    # 1. Load the font
    try:
        font = ImageFont.truetype(font_path, fontsize)
    except OSError:
        raise Exception(f"Could not load font at: {font_path}")

    # 2. Calculate text size (using getbbox for accuracy with strokes)
    # Create a dummy image to calculate size
    dummy_img = Image.new('RGBA', (1, 1))
    draw = ImageDraw.Draw(dummy_img)

    # getbbox returns (left, top, right, bottom)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    text_width = right - left
    text_height = bottom - top

    # Add a little padding to prevent cutting off edges
    width = text_width + 20
    height = text_height + 20

    # 3. Create the actual image with transparent background
    img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # 4. Draw text (Center it in the image)
    # We offset by -left and -top to align the bounding box to 0,0 + padding
    x_pos = 10 - left
    y_pos = 10 - top

    draw.text(
        (x_pos, y_pos),
        text,
        font=font,
        fill=color,
        stroke_width=stroke_width,
        stroke_fill=stroke_color
    )

    # 5. Convert to numpy array for MoviePy
    img_np = np.array(img)

    # 6. Create ImageClip
    # We set the duration later in the main loop
    clip = ImageClip(img_np)

    return clip

def generate_subtitle_clips_moviepy_obj(
        word_data_dict,
        videosize=(1080, 1920),
        font= "/Users/saiaikeshwetunaung/Documents/PythonProjects/Automated_content_farm/media_resources/thai_fonts/Prompt-Bold.ttf",

        fontsize=120,
        color='yellow',     # Yellow is standard for Thai TikTok
        stroke_width=4,
        stroke_color='black',
):
    """
    Generates a list of TextClips based on word timings.
    """
    print(f"4. 🎬 Generating {len(word_data_dict)} subtitle clips...")

    TextClips_list = []
    # Iterate through words
    for item in word_data_dict:
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
            txt_clip = _create_pil_text_clip(
                text=word_text,
                font_path=font,
                fontsize=fontsize,
                color=color,
                stroke_color=stroke_color,
                stroke_width=stroke_width
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

def _create_debug_subtitle_clip(TextClips_list, output_dir=""):
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
    with open("correct_test_files/mfa_aligned_transcript_data.json") as f:
        test_word_timestamp_data = json.load(f)

    sub_debug_dir = "_d_generate_moviepy_subtitle_clips"
    full_debug_dir = set_debug_dir_for_module_of_pipeline(sub_debug_dir)

    # generate text clips
    text_clips = generate_subtitle_clips_moviepy_obj(
        word_data_dict=test_word_timestamp_data,
    )

    # create debug video
    _create_debug_subtitle_clip(
        TextClips_list=text_clips,
        output_dir=full_debug_dir
    )


    # # temp comment out to merge audio and video
    # ffmpeg_merge_video_audio(
    #     video=os.path.join(debug_directory, "debug_test_subtitle_clip.mp4"),
    #     audio="correct_test_files/raw_original_audio.wav",
    #     output=os.path.join(debug_directory, "debug_test_subtitles_vid_with_sound.mp4"),
    #     vcodec='copy', # 'copy' means don't re-render video (Fast!)
    #     acodec='aac', # audio codec
    #     ffmpeg_output=False, # Hides logs
    #     logger=None
    # )
    print(f"✅ Debug subtitle vid with sound ")