# -----------------------------------
# COMPATIBILITY PATCH (or else the script crashes during the resizing of the downloaded clip from Pexels)
import PIL.Image

# FIX: Pillow 10.0.0 removed ANTIALIAS, but MoviePy needs it
# We restore it by mapping it to LANCZOS (the new standard).
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS # dont worry when warning shows up

# --------------------------------

import asyncio # for async functions
import os
import shutil  # For deleting folders
import requests # for Pexels API
import random # to choose random footage from Pexels

from dotenv import load_dotenv # to load env variables

from google import genai # import gemini
from google.genai import types  # thinking mode

# text to speech
import edge_tts

from moviepy.editor import ColorClip, TextClip, CompositeVideoClip, AudioFileClip # ImageMagick is installed

# to use FFMPEG directly to merge streams without re-encoding the video. It is instant and lossless.
from moviepy.video.io.ffmpeg_tools import ffmpeg_merge_video_audio

# to loop video clip when audio is longer than video
import moviepy.video.fx.all as vfx

# to use the downloaded binary stock video (wrapper)
from moviepy.video.io.VideoFileClip import VideoFileClip

# for tiktok style captions with whisper
import mlx_whisper


# ==========================================
# CONFIGURATION
# ==========================================
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

VOICE = "en-US-GuyNeural"

# Define Directories
TEMP_DIR = "___temp_script_workspace"
OUTPUT_DIR = f"___Final_render"

# Define File Paths
# using os.path.join for Windows/Mac compatibility
TEMP_AUDIO = os.path.join(TEMP_DIR, "raw_audio.mp3")
TEMP_VIDEO_BG = os.path.join(TEMP_DIR, "downloaded_bg.mp4")
TEMP_VIDEO_BG_WITH_SUBTITLES = os.path.join(TEMP_DIR, "overlay_visuals.mp4")

FINAL_OUTPUT = os.path.join(OUTPUT_DIR, "finished_video.mp4")

# ==========================================
# FILE MANAGEMENT
# ==========================================
def setup_folders():
    """Create necessary folders if they don't exist"""
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def cleanup_temp():
    """Delete the temp folder and its contents"""
    print(f"🧹 Cleaning up {TEMP_DIR}...")
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    print("✨ Workspace clean.")

# ==========================================
# 1. Generating Script
# ==========================================

async def generate_script_and_keywords(api_key):
    """Generates Script AND Visual Search Query"""
    print("1. 🧠 Asking Gemini for script and visual keywords...")
    client = genai.Client(api_key=api_key)

    # Updated Prompt: Longer script + Search Term extraction
    prompt = (
        """
        Generate a reddit story that is interesting and engaging (e.g. weird cheating story, dark first then wholesome plot twist).
        This is for a script for a short form vertical video like a Instagram reel or a TikTok or a YT shorts.
        The video should last around 40 seconds so generate the script accordingly.
        The tone should be from the pov of the reddit post owner, concerned or suspicious or anything that fits the story and 
        isn't dry. Make it have a personality.
        
        AFTER the script, add a separator '|||' followed by a visual search query for a stock video site for generic visual engagement.
        search query keywords for clips such as oddly satisfying things such as Hydraulic pressing, soap cutting, sand slicing, satisfying gameplay. 
        "\n\nFormat: [Script] ||| [Search Term] \n"
        "(e.g. `This is the example script ... about a cheating payback story ||| asmr video`)"
                """
    )

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(
            # This enables the thinking capability
            thinking_config=types.ThinkingConfig(
                # include_thoughts=True, # Returns the 'thoughts' in the response
                thinking_budget=1024   # Token budget for thinking (1024 is a good start)
            )
        )
    )

    raw_text = response.text.strip()

    # Parse the result
    if "|||" in raw_text:
        script, search_term = raw_text.split("|||")
        script = script.strip()
        search_term = search_term.strip()
    else:
        # Fallback if AI fails formatting
        script = raw_text
        search_term = "Abstract background"

    print(f"   📜 Script: {script}...")
    print(f"   Word count: { len(script.split()) }")
    print(f"   🔍 Search term for footage: {search_term}")
    return script, search_term

# ==========================================
# 2. AUDIO GENERATION
# ==========================================

async def generate_audio(text):
    """Step 2: Convert text to MP3 using Edge-TTS"""
    print("2. 🗣️ Generating temp Audio based on script...")
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(TEMP_AUDIO)
    print(f"   Audio saved to {TEMP_AUDIO}")


# ==========================================
# 3. TRANSCRIPTION
# ==========================================

def transcribe_audio_get_subtitles():
    """Step 3: Transcribe the audio with timestamps for captions"""
    print("3. 🤖📝 Transcribing with MLX-Whisper ...")

    # We use the Turbo model since the largest whisper turbo model only uses ~4-5gb
    result = mlx_whisper.transcribe(
        TEMP_AUDIO,
        path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
        word_timestamps=True # This gives us start/end time per word,
    )

    # Extract just the word list from the segments
    word_segments = []
    for segment in result['segments']:
        for word in segment['words']:
            word_segments.append({
                "word": word['word'].strip(),
                "start": word['start'],
                "end": word['end']
            })

    print(f"   Extracted {len(word_segments)} words.")
    return word_segments

# ==========================================
# 4. VISUAL FETCHING (Pexel)
# ==========================================

def download_stock_footage(query):
    """Fetches a vertical video from Pexels based on query"""
    print(f"4. 🎬  Fetching stock footage for: '{query}'...")

    headers = {"Authorization": PEXELS_API_KEY}

    # `orientation=portrait` = only return vertical videos (tall, 9:16 aspect ratio)
    # `per_page=3` = limit search results to 3 items
    url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=3"

    try:
        r = requests.get(url, headers=headers)
        data = r.json() # converts the json result to a python dict

        if not data['videos']:
            print("   ⚠️ No videos found. Using fallback.")
            return False # Handle fallback in next step if needed

        # Pick a random video from the top 3 results
        video_data = random.choice(data['videos'])

        # Find the best quality video file link (HD preferred)
        # We want the one closest to 1080w.
        video_files = video_data['video_files'] # Pexels returns a list of files with different qualities (dimensions).

        # simple logic: biggest width
        best_video = max(video_files, key=lambda x: x['width']) # looks for the highest `x['width']` among the files
        download_link = best_video['link']

        # Download
        # The first request (at the top) got information about the video.
        print(f"   ⬇️ Downloading video ID {video_data['id']}...")
        video_content = requests.get(download_link).content

        # This second request downloads the actual video file (the bytes).
        with open(TEMP_VIDEO_BG, 'wb') as f: # `wb` = write binary, `f` is just a buffered binary writer
            f.write(video_content) # writes/downloads the binary to the TEMP_VIDEO_BG

        print("   ✅ Background video downloaded.")
        return True

    except Exception as e:
        print(f"   ❌ Pexels Error: {e}")
        return False


# ==========================================
# 5. VIDEO COMPOSITION
# ==========================================

def generate_composed_video(word_data):
    print("5. 🎬 Compositing Video Layers...")

    # A. Load the Audio to get exact duration
    audio_clip = AudioFileClip(TEMP_AUDIO)
    duration = audio_clip.duration + 0.5 # Buffer 0.5 sec at the end
    # so that video doesn't cut off while the last word is being spoken
    audio_clip.close() # Close file explicitly to avoid permission errors

    # B. Background Video Logic
    if os.path.exists(TEMP_VIDEO_BG):
        bg_clip = VideoFileClip(TEMP_VIDEO_BG)

        # Loop video if it's shorter than audio
        if bg_clip.duration < duration:
            bg_clip = vfx.loop(bg_clip, duration=duration) # warning here on `.loop()` can be ignored, the function exists.
        else:
            bg_clip = bg_clip.subclip(0, duration)

        # Resize/Crop to ensure 9:16 (1080x1920), handles both portrait and landscape
        # We ensure the video covers 1080x1920 completely before cropping.
        target_ratio = 1080 / 1920
        video_ratio = bg_clip.w / bg_clip.h

        if video_ratio > target_ratio:
            # Case A: Video is wider than 9:16 (Landscape, Square, or Standard Vertical)
            # We match height to 1920. Width will be >= 1080.
            bg_clip = bg_clip.resize(height=1920)
        else:
            # Case B: Video is skinnier than 9:16 (Tall thin videos)
            # We match width to 1080. Height will be >= 1920.
            bg_clip = bg_clip.resize(width=1080)

        # Now that the video is guaranteed to be large enough, we center crop.
        bg_clip = bg_clip.crop(width=1080, height=1920, x_center=bg_clip.w/2, y_center=bg_clip.h/2)
        # ---------------------------------------------------------

    else:
        # Fallback to Black Screen if download failed
        print("   ⚠️ Using Black Background fallback.")
        from moviepy.editor import ColorClip
        bg_clip = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=duration)

    # C. Create Text Overlay (TikTok Style captions/subtitles)
    text_clips = [] # stores only text clips (bg will be combined latr)
    for item in word_data:
        word_text = item['word']
        start_time = item['start']
        end_time = item['end']

        # Create a text clip for THIS specific word
        # Note: 'stroke_color' and 'stroke_width' make it pop like subtitles
        txt_clip = TextClip(
            word_text,
            fontsize=140, # Bigger font for single words
            color='white',
            font='Proxima Nova',
            stroke_color='black',
            stroke_width=3.5,
            method='label'   # 'label' is better for single words than 'caption'
        )
        # Set when this specific word appears and disappears
        txt_clip = txt_clip.set_position('center').set_start(start_time).set_duration(end_time - start_time)

        text_clips.append(txt_clip)

    # D. Composite -  Combine all the little text clips onto the background clip
    final_video = CompositeVideoClip([bg_clip] + text_clips)

    # Write soundless video. It is faster and creates the temp video file.
    final_video.write_videofile(
        TEMP_VIDEO_BG_WITH_SUBTITLES,
        fps=30,
        codec="libx264",
        audio=False,
        verbose=False,
        # preset="ultrafast", # Faster for testing, otherwise turn off
        logger='bar',
    )

    # Close clips to release memory
    bg_clip.close()
    final_video.close()
    print(f"   Soundless Video (bg and subtitles) saved to {TEMP_VIDEO_BG_WITH_SUBTITLES}")

# ==========================================
# 6. MERGE
# ==========================================

def merge_assets():
    print("6. 🔗 Merging Video and Audio...")

    # This uses FFMPEG directly to merge streams without re-encoding the video.
    # It is instant and lossless.
    ffmpeg_merge_video_audio(
        video=TEMP_VIDEO_BG_WITH_SUBTITLES,
        audio=TEMP_AUDIO,
        output=FINAL_OUTPUT,
        vcodec='copy', # 'copy' means don't re-render video (Fast!)
        acodec='aac', # audio codec
        ffmpeg_output=False, # Hides logs
        logger=None
    )
    print(f"✅ Final Video: {FINAL_OUTPUT}")


# ==========================================
# MAIN EXECUTION
# ==========================================
async def main():
    try:
        setup_folders()

        # 1. generate script and keywords
        script, stock_footage_query = await generate_script_and_keywords(gemini_api_key)

        # 2. Audio
        await generate_audio(script)

        # 3. Download background stock footage from Pexels
        download_stock_footage(stock_footage_query)

        # 4. get each word timestamps from audio clip
        word_data = transcribe_audio_get_subtitles()


        # 5. Render video (bg + subtitles)
        # word_data instead of raw script to make tiktok style captions
        generate_composed_video(word_data)

        # 6. Final Merge: Combine in Output to get final result
        merge_assets()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # This runs whether the code succeeds or fails
        cleanup_temp()  # comment to see the temp files (need to clean or else the next vid will use old assets)

        pass

if __name__ == "__main__":
    asyncio.run(main())
    # TODO: get satisfying gameplay stock footage vids. > choose random vid > choose random segment from vid > use as bg