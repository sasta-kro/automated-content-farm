import asyncio
import os
import wave
import edge_tts
import ffmpeg
from google import genai
from google.genai import types

# Import Constants
from src.short_form_content_pipeline._CONSTANTS import (
    AUDIO_VOICE_MAPPING_EDGE,
    AUDIO_VOICE_MAPPING_GEMINI,
    AUDIO_GEMINI_PROMPT_TEMPLATE
)
from src.short_form_content_pipeline.Util_functions import set_debug_dir_for_module_of_pipeline

# ==================== Audio Processing (FFmpeg) ====================

def change_audio_speed(
        input_path: str,
        output_path: str,
        speed_factor: float
):
    """
        Uses FFmpeg 'atempo' to create a high-quality sped-up audio file
         WITHOUT changing pitch.

         Returns the sped up audio file path
    """
    if speed_factor == 1.0:
        # Just copy if speed is 1.0
        # return input_path # TODO (Optimization: Handle this in main logic)
        pass

    print(f"   ⚡ Speeding up audio by {speed_factor}x using FFmpeg...")

    try:
        # `atempo` is the anti-chipmunk filter
        # Note: atempo is limited to [0.5, 2.0]. If we need > 2, chaining is required
        stream = ffmpeg.input(input_path)
        stream = ffmpeg.filter(stream, 'atempo', speed_factor)
        stream = ffmpeg.output(stream, output_path)
        ffmpeg.run(stream, overwrite_output=True, quiet=True)

        return output_path

    except ffmpeg.Error as e:
        print(f"❌ Audio Speedup Failed. FFmpeg Error: {e.stderr.decode('utf8') if e.stderr else str(e)}")
        raise e

# ==================== Gemini Generator ====================

async def generate_with_gemini(
        text: str,
        gender: str,
        language: str,
        api_key: str,
        audio_ai_model: str,
        audio_filename: str
):
    """
    Generates audio using Gemini 2.5 Flash Audio Generation.
    """
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing!")

    client = genai.Client(api_key=api_key)
    voice_name = AUDIO_VOICE_MAPPING_GEMINI.get(gender, "Aoede")

    # Force .wav extension for Gemini raw output
    audio_filename = audio_filename.replace(".mp3", ".wav")

    print(f" 🎙️ Audio Synthesizing (Gemini) | Voice: {voice_name}...")

    prompt = AUDIO_GEMINI_PROMPT_TEMPLATE.format(language=language, text=text)

    # Configuration for Speech Generation
    # Note: This uses the generate_content with audio modality
    try:
        response = client.models.generate_content(
            model=audio_ai_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name
                        )
                    )
                )
            )
        )

        print("         response received") # for debug

        # Gemini returns raw audio bytes (PCM or MP3 depending on config)
        # We need to save it.
        # Note: The SDK return format for audio needs handling.
        # Often it's in response.candidates[0].content.parts[0].inline_data.data

        if response.candidates and response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]

            if part.inline_data and part.inline_data.data:
                # Get the raw PCM bytes (Linear16)
                audio_data = part.inline_data.data

                print(f"   Received {len(audio_data)} bytes of raw PCM audio.")


                #  Write to WAV file with correct 24kHz header
                with wave.open(audio_filename, "wb") as wf:
                    wf.setnchannels(1)    # Mono
                    wf.setsampwidth(2)     # 16-bit (2 bytes per sample)
                    wf.setframerate(24000)  # 24kHz (Standard for Gemini Flash)
                    wf.writeframes(audio_data)

                return audio_filename
            else:
                print("   ❌ Gemini response contained no inline audio data.")
                return None

    except Exception as e:
        print(f"   ❌ Gemini TTS Failed: {e}")
        return None

# ==================== Edge TTS Generator (just for backup) ====================

async def generate_with_edge_tts(
        text: str,
        gender: str,
        language: str,
        filename: str
) -> str:
    """
    (Dropped feature because Gemini works well, plus I don't wanna bother indexing all language speakers)
    Generates audio using MS Edge TTS.
    """
    voice = AUDIO_VOICE_MAPPING_EDGE.get(gender, "th-TH-PremwadeeNeural")

    # Ensure .mp3
    if not filename.endswith(".mp3"):
        filename = filename + ".mp3"

    communicate = edge_tts.Communicate(text, voice)

    print(f" 🎙️ Audio Synthesizing (EdgeTTS) | Voice: {voice}...")
    await communicate.save(filename)
    return filename

# ==================== Main wrapper function ====================

async def generate_audio_narration_file(
        script_data: dict,
        output_folder_path: str,

        # Settings Injection
        language: str,
        tts_provider: str, # "gemini" or "edge-tts"
        gemini_api_key: str,  # edge-tts doesn't need api key
        audio_ai_model: str,
        speed_factor: float
):
    """
    Main entry point for audio generation.
    1. Generates Raw Audio (Normal Speed).
    2. Processes Speed with FFmpeg (speed up).
    3. Returns path to Final Audio.

    script_data (dict): From script_generator.py (must contain 'script_text' and 'gender')
    output_folder_path: where the output audio file will be stored in
    """
    print("2. 🔊 Starting Audio Generation...")

    # Extract Data
    text = script_data.get("script_text")
    gender = script_data.get("gender", "F") # f is default

    if not text:
        raise ValueError("❌ No script text found in data object!")

    # Prepare Filenames
    # no extension yet. Extension will be added later since edge gives mp3 and gemini give wav
    base_name = "raw_original_audio"

    # joined with the output folder
    raw_path_no_ext = os.path.join(output_folder_path, base_name)

    normal_audio_file_path = None # temporarily declaring

    # --- Generation Phase ---
    if tts_provider == "gemini":
        normal_audio_file_path = await generate_with_gemini(
            text=text,
            gender=gender,
            language=language,
            api_key=gemini_api_key,
            audio_ai_model=audio_ai_model,
            audio_filename=raw_path_no_ext + ".wav"
        )

    # Fallback / Default to Edge
    if not normal_audio_file_path or tts_provider == "edge-tts":
        normal_audio_file_path = await generate_with_edge_tts(
            text=text, gender=gender, language=language, filename=raw_path_no_ext + ".mp3"
        )

    if not normal_audio_file_path or not os.path.exists(normal_audio_file_path):
        raise RuntimeError("❌ Audio generation failed. Audio file cannot be found or not generated.")

    print(f"   ✅ Raw Audio saved: {normal_audio_file_path}")

    # --- Processing audio (Speed Up) ---
    if speed_factor > 1.0:
        final_filename = f"narration_audio_sped_up_{speed_factor}x.mp3"
        final_spedup_audio_output_path = os.path.join(output_folder_path, final_filename)

        # Run FFmpeg helper function
        change_audio_speed(
            input_path=normal_audio_file_path,
            output_path=final_spedup_audio_output_path,
            speed_factor=speed_factor)

        return final_spedup_audio_output_path
    else:
        # If speed is 1.0, just return the raw file
        return normal_audio_file_path


# ================ Testing

if __name__ == "__main__":
    import json
    # Import Settings
    from src.short_form_content_pipeline._CONFIG import SETTINGS
    # Load Profile
    SETTINGS.load_profile("thai_funny_story.yaml")

    # We try to load the file generated by previous step if it exists
    mock_input_path = "___debug_dir/_d_script_generation/original_script_data.json"

    if os.path.exists(mock_input_path):
        with open(mock_input_path, 'r', encoding='utf-8') as f:
            script_data_json = json.load(f)
    else:
        raise Exception("Audio file not found")

    sub_debug_dir = "_d_audio_generation"
    full_debug_dir = set_debug_dir_for_module_of_pipeline(sub_debug_dir)


    final_audio = asyncio.run(   generate_audio_narration_file(
        script_data=script_data_json,
        output_folder_path=full_debug_dir,
        # Inject from SETTINGS
        language=SETTINGS.content.language,
        tts_provider=SETTINGS.audio.tts_provider,
        gemini_api_key=SETTINGS.GEMINI_API_KEY,
        audio_ai_model=SETTINGS.audio.audio_ai_model,
        speed_factor=SETTINGS.audio.speed_factor
    ))

    print(f"\n Final Result: {final_audio}")