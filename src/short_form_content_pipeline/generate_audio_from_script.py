import asyncio
import json
import os

from dotenv import load_dotenv
import edge_tts
from google import genai
from google.genai import types


import wave # to write/save gemini's audio file as .wav since it returns that
import ffmpeg # to speed up the audio clip

from src.short_form_content_pipeline.Util_functions import set_debug_dir_for_module_of_pipeline

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

# 2. Gemini Voices
# Mappings to closest "Dipper" and "Vega" equivalents
GEMINI_VOICES = {
    "M": "Charon", # Deep, Storyteller (closest to Dipper)
    "F": "Aoede"   # Breezy, Confident (closest to Vega)
}



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



# ========================== Edge (just for backup)

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

    # Fallback or Default to EdgeTTS
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

    try:
        with open('___debug_dir/_d_script_generation/original_script_data_burmese.json', 'r') as f:
            script_data_json = json.load(f)
    except FileNotFoundError:
        print("Error: File not found.")

    sub_debug_dir_for_this_module = "_d_audio_generation"
    full_debug_dir = set_debug_dir_for_module_of_pipeline(sub_debug_dir_for_this_module)

    asyncio.run(generate_audio_narration_file_th(
        script_data=script_data_json,
        output_folder_path=full_debug_dir,
        use_gemini=True)
    )