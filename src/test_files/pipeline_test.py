import asyncio # for async functions
import os
import shutil  # For deleting folders

from dotenv import load_dotenv # to load env variables
from google import genai
import edge_tts
from moviepy.editor import ColorClip, TextClip, CompositeVideoClip, AudioFileClip # ImageMagick is installed

# to use FFMPEG directly to merge streams without re-encoding the video. It is instant and lossless.
from moviepy.video.io.ffmpeg_tools import ffmpeg_merge_video_audio

# ==========================================
# CONFIGURATION
# ==========================================
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

VOICE = "en-US-GuyNeural"

# 1. Define Directories
TEMP_DIR = "temp_moviepy_workspace"
OUTPUT_DIR = f"Final_render"

# 2. Define File Paths
# We use os.path.join for Windows/Mac compatibility
TEMP_AUDIO = os.path.join(TEMP_DIR, "raw_audio.mp3")
TEMP_VIDEO = os.path.join(TEMP_DIR, "silent_visuals.mp4")
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
# THE PIPELINE
# ==========================================

async def generate_script(api_key):
    """Step 1: Get text from Gemini"""
    print("1. 🧠 Asking Gemini for a script...")

    client = genai.Client(api_key=api_key)

    # We ask for something short for this test
    prompt = "Generate a 1-sentence fun fact about biology in the tone of Patrick from Spongebob."

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    script = response.text.strip()
    print(f"   Script: {script}")
    return script



async def generate_audio(text):
    """Step 2: Convert text to MP3 using Edge-TTS"""
    print("2. 🗣️ Generating Audio to temp...")

    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(TEMP_AUDIO)

    print(f"   Audio saved to {TEMP_AUDIO}")



def generate_silent_video(script_text):
    """Step 3: Build the video using MoviePy"""
    print("3. 🎬 Rendering Silent Video Stream...")

    # A. Load the Audio to get exact duration
    audio_clip = AudioFileClip(TEMP_AUDIO)
    duration = audio_clip.duration + 0.5  # Add 0.5s padding at the end
    audio_clip.close() # Close file explicitly to avoid permission errors


    # B. Create Background (Black, Vertical 9:16)
    bg_clip = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=duration)

    # C. Create Text (White, Centered)
    txt_clip = TextClip(
        script_text,
        fontsize=70,
        color='white',
        size=(900, 1600), # Text box slightly smaller than screen to add padding
        method='caption'  # 'caption' wraps the text automatically
    )
    txt_clip = txt_clip.set_position('center').set_duration(duration)

    final_video = CompositeVideoClip([bg_clip, txt_clip])

    # IMPORTANT: Export with audio=False.
    # This renders pixels ONLY. It is faster and creates the temp video file.
    final_video.write_videofile(
        TEMP_VIDEO,
        fps=24,
        codec="libx264",
        audio=False,       # <--- No audio here
        verbose=False,
        logger=None
    )
    print(f"   Soundless Video saved to {TEMP_VIDEO}")

def merge_assets():
    print("4. 🔗 Merging Video and Audio...")

    # This uses FFMPEG directly to merge streams without re-encoding the video.
    # It is instant and lossless.
    ffmpeg_merge_video_audio(
        TEMP_VIDEO,
        TEMP_AUDIO,
        FINAL_OUTPUT,
        vcodec='copy', # 'copy' means don't re-render video (Fast!)
        acodec='aac',
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

        # generate script
        script = await generate_script(gemini_api_key)

        # temp Audio to Temp
        await generate_audio(script)

        # temp Video to Temp (Soundless)
        generate_silent_video(script)

        # Combine in Output to get final result
        merge_assets()

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        # This runs whether the code succeeds or fails
        cleanup_temp()  # Optional; comment to see the temp files

if __name__ == "__main__":
    asyncio.run(main())