import asyncio
import json
import os

from dotenv import load_dotenv
import edge_tts
from google import genai
from google.genai import types


import wave # to write/save gemini's audio file as .wav since it returns that
import ffmpeg # to speed up the audio clip


# ==================== Config

# Load API Key
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Voice Mapping
# 1. Edge TTS (Reliable Thai Voices)
EDGE_VOICES = {
    "M": "th-TH-NiwatNeural",
    "F": "th-TH-PremwadeeNeural"
}

# 2. Gemini Voices (Experimental for Thai, Good for English)
# Mappings to closest "Dipper" and "Vega" equivalents
GEMINI_VOICES = {
    "M": "Charon", # Deep, Storyteller (closest to Dipper)
    "F": "Aoede"   # Breezy, Confident (closest to Vega)
}


# ========================== Edge

async def generate_with_edge_tts(text: str, gender: str, filename: str) -> str:
    """
    Generates audio using MS Edge TTS (Best for Thai).
    """
    voice = EDGE_VOICES.get(gender, "th-TH-PremwadeeNeural")
    output_file_path = filename

    # Adjusting rate for "TikTok Speed" (Thai speakers talk fast online)
    communicate = edge_tts.Communicate(text, voice)

    print(f" 🎙️ Audio Synthesizing (edge-tts) with {voice}...")
    await communicate.save(output_file_path)
    return output_file_path



# ===================== Gemini

async def generate_with_gemini(text: str, gender: str, filename: str):
    """
    Generates audio using Gemini 2.5 Flash Audio Generation.
    WARNING: Thai support is experimental.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is missing!")

    client = genai.Client(api_key=GEMINI_API_KEY)
    voice_name = GEMINI_VOICES.get(gender, "Aoede")


    filename = filename.replace(".mp3", ".wav")
    output_file_path = filename

    print(f" 🎙️ Audio Synthesizing (Gemini API) with voice: {voice_name}...")

    # Configuration for Speech Generation
    # Note: This uses the generate_content with audio modality
    prompt = f"Read this text realistically, naturally in Burmese in an appropriate tone/energy for the script: {text}"

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"], # important: make it reply in audio
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name
                        )
                    )
                )
            )
        )

        print("         response received")

        # Gemini returns raw audio bytes (PCM or MP3 depending on config)
        # We need to save it.
        # Note: The SDK return format for audio needs handling.
        # Often it's in response.candidates[0].content.parts[0].inline_data.data

        if response.candidates and response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]

            if part.inline_data and part.inline_data.data:
                # 2. Get the raw PCM bytes (Linear16)
                audio_data = part.inline_data.data

                # optional
                print(f"   Received {len(audio_data)} bytes of raw PCM audio.")

                # 3. Write to WAV file with correct 24kHz header
                with wave.open(output_file_path, "wb") as wf:
                    wf.setnchannels(1)      # Mono
                    wf.setsampwidth(2)      # 16-bit (2 bytes per sample)
                    wf.setframerate(24000)  # 24kHz (Standard for Gemini Flash)
                    wf.writeframes(audio_data)

                return output_file_path
            else:
                print("   ❌ Gemini response contained no inline audio data.")

    except Exception as e:
        print(f"   ❌ Gemini TTS Failed: {e}")


# ====================== Helper for the main wrapper function, to speed up the audio (i will use this later in the pipeline, need to refactor as well)

async def speed_up_audio_with_ffmpeg(input_path: str, speed: float = 1.2) -> str:
    """
    Speeds up audio using ffmpeg-python without pitch shifting (No Chipmunk Effect).
    """
    # Determine TTS Model based on input string (not used anymore to make it easier to use the file name)
    tts_model = "Unknown"
    if "Gem" in input_path:   tts_model = "Gem"
    elif "Edg" in input_path: tts_model = "Edg"

    # rename output file
    input_dir = os.path.dirname(input_path)
    new_filename = f"spedup_audio_narration.mp3"
    output_path = os.path.join(input_dir, new_filename)

    print(f"   ⏩ Speeding up audio by {int((speed-1)*100)}% (HQ MP3)...")

    try:
        # Build the FFmpeg stream graph
        #    - input: load the file
        #    - filter('atempo', speed): Speed up TEMPO only (maintains pitch)
        #    - output: save as mp3 with 320k bitrate (High Quality)
        stream = ffmpeg.input(input_path)
        stream = ffmpeg.filter(stream, 'atempo', speed)
        stream = ffmpeg.output(stream, output_path, **{'b:a': '320k'})

        # Run it
        #    overwrite_output=True adds the '-y' flag
        #    quiet=True suppresses the huge wall of text logs
        ffmpeg.run(stream, overwrite_output=True, quiet=True)
        return output_path

    except ffmpeg.Error as e:
        print(f"   ❌ FFmpeg Error: {e.stderr.decode('utf8') if e.stderr else str(e)}")
        return input_path
    except Exception as e:
        print(f"   ❌ General Error: {e}")
        return input_path



# ========================== main wrapper function

async def generate_audio_narration_file_th(
        script_data: dict,
        output_folder_path: str = "",
        use_gemini: bool = False
):
    """
    Main entry point for audio generation.
    Args:
        script_data (dict): From script_generator.py (must contain 'script_thai' and 'gender')
        output_folder_path: where the output audio file will be stored in
        use_gemini (bool): If True, tries Gemini first. Defaults to False for safety.
    """
    print("2. 🔊 Starting Audio Generation...")

    text = script_data.get("script_thai", "")
    gender = script_data.get("gender", "F")

    # Sanitize filename from title
    cleaned_title = "".join([c for c in script_data.get("title_thai", "audio") if c.isalnum() or c in (' ', '_')]).rstrip()

    filename_supported_thai_title = cleaned_title[:20].strip().replace(' ', '_') # optional, in case I want to have thai filename

    # joined with the output folder
    # no extension yet. Extension will be added later since edge gives mp3 and gemini give wav
    filename = os.path.join(output_folder_path, f"raw_original_audio")

    raw_audio_output_file = None

    # Try Gemini if bool arg is true
    if use_gemini:
        raw_audio_output_file = await generate_with_gemini(
            text=text,
            gender=gender,
            filename= f"{filename}.wav"
        )

    # Fallback or Default to EdgeTTS (or stop function)
    if not use_gemini: # only print when gemini bool is set to true
        try:
            raw_audio_output_file = await generate_with_edge_tts(
                text=text,
                gender=gender,
                filename= f"{filename}.mp3"
            )
        except Exception as e:
            raise e

    if raw_audio_output_file:
        print(f"  >>> Raw Audio saved to: {raw_audio_output_file}")
        print("✅ Finished generating audio file.\n")
        return raw_audio_output_file # returns the un-sped-up audio
    else:
        print("❌ Raw audio file generation failed or not found or not generated")
        return


# ================ Execution

if __name__ == "__main__":
    # Test Data simulating script_generator output



    try:
        with open('___debug_generated_script/original_script_data_burmese.json', 'r') as f:
            script_data_json = json.load(f)
    except FileNotFoundError:
        print("Error: File not found.")

    # Run the test
    os.makedirs("___debug_audio_generation", exist_ok=True) # create the folder

    asyncio.run(generate_audio_narration_file_th(
        script_data=script_data_json,
        output_folder_path="___debug_audio_generation",
        use_gemini=True)
    )