import asyncio # for async functions
import os
import shutil  # For deleting folders

from dotenv import load_dotenv # to load env variables
from google import genai
import edge_tts
from moviepy.editor import ColorClip, TextClip, CompositeVideoClip, AudioFileClip # ImageMagick is installed

# to use FFMPEG directly to merge streams without re-encoding the video. It is instant and lossless.
from moviepy.video.io.ffmpeg_tools import ffmpeg_merge_video_audio

# for tiktok style captions with whisper
import mlx_whisper


# ==========================================
# CONFIGURATION
# ==========================================
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

VOICE = "en-US-GuyNeural"

# Define Directories
TEMP_DIR = "temp_moviepy_workspace"
OUTPUT_DIR = f"Final_render"

# Define File Paths
# using os.path.join for Windows/Mac compatibility
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
    # short and simple for test
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
    print("2. 🗣️ Generating temp Audio based on script...")
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(TEMP_AUDIO)
    print(f"   Audio saved to {TEMP_AUDIO}")


def transcribe_audio():
    """Step 3: Transcribe the audio with timestamps for captions"""
    print("3. 🤖📝 Transcribing with MLX-Whisper (M3 Optimized)...")

    # We use the Turbo model since the largest whisper turbo model only uses ~4-5gb
    result = mlx_whisper.transcribe(
        TEMP_AUDIO,
        path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
        word_timestamps=True # CRITICAL: This gives us start/end per word,
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



def generate_silent_video(word_data):
    """Step 4: Build the video using MoviePy"""
    print("4. 🎬 Rendering Silent Video Stream...")

    # A. Load the Audio to get exact duration
    audio_clip = AudioFileClip(TEMP_AUDIO)
    duration = audio_clip.duration + 0.5  # Add 0.5s padding at the end
    audio_clip.close() # Close file explicitly to avoid permission errors


    # B. Create Background (Black, Vertical 9:16)
    bg_clip = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=duration)

    # C. Create Dynamic Text Clips
    video_clips = [bg_clip] # Start list with background

    for item in word_data:
        word_text = item['word']
        start_time = item['start']
        end_time = item['end']

        # Create a text clip for THIS specific word
        # Note: 'stroke_color' and 'stroke_width' make it pop like subtitles
        txt_clip = TextClip(
            word_text,
            fontsize=120,          # Bigger font for single words
            color='yellow',        # Yellow is classic for captions
            font='Arial-Bold',     # Ensure you have a nice bold font
            stroke_color='black',
            stroke_width=4,
            method='label'         # 'label' is better for single words than 'caption'
        )

        # Set when this specific word appears and disappears
        txt_clip = txt_clip.set_position('center').set_start(start_time).set_duration(end_time - start_time)

        video_clips.append(txt_clip)

    # Combine all the little text clips onto the background
    final_video = CompositeVideoClip(video_clips)

    # This renders pixels ONLY, no audio. It is faster and creates the temp video file.
    final_video.write_videofile(
        TEMP_VIDEO,
        fps=24,
        codec="libx264",
        audio=False,
        verbose=False,
        logger=None
    )
    print(f"   Soundless Video saved to {TEMP_VIDEO}")

def merge_assets():
    """Step5"""
    print("5. 🔗 Merging Video and Audio...")

    # This uses FFMPEG directly to merge streams without re-encoding the video.
    # It is instant and lossless.
    ffmpeg_merge_video_audio(
        video=TEMP_VIDEO,
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

        # generate script
        script = await generate_script(gemini_api_key)

        # temp Audio to Temp
        await generate_audio(script)

        # get each word timestamps from audio clip
        word_data = transcribe_audio()


        # temp Video to Temp (Soundless)
        # word_data instead of raw script to make tiktok style captions
        generate_silent_video(word_data)

        # Combine in Output to get final result
        merge_assets()

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        # This runs whether the code succeeds or fails
        cleanup_temp()  # Optional; comment to see the temp files

        pass

if __name__ == "__main__":
    asyncio.run(main())