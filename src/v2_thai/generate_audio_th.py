import asyncio
import os
from dotenv import load_dotenv
import edge_tts
from google import genai
from google.genai import types

# Load API Key
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- CONFIGURATION ---
AUDIO_DIR = "temp_script_workspace"
os.makedirs(AUDIO_DIR, exist_ok=True)

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

async def generate_with_edge_tts(text: str, gender: str, filename: str) -> str:
    """
    Generates audio using MS Edge TTS (Best for Thai).
    """
    voice = EDGE_VOICES.get(gender, "th-TH-PremwadeeNeural")
    output_path = os.path.join(AUDIO_DIR, filename)

    # Adjusting rate for "TikTok Speed" (Thai speakers talk fast online)
    communicate = edge_tts.Communicate(text, voice, rate="+20%")

    print(f" 🎙️ Audio Synthesizing (edge-tts) with {voice}...")
    await communicate.save(output_path)
    return output_path

async def generate_with_gemini(text: str, gender: str, filename: str) -> str:
    """
    Generates audio using Gemini 2.5 Flash Audio Generation.
    WARNING: Thai support is experimental.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is missing!")

    client = genai.Client(api_key=GEMINI_API_KEY)
    voice_name = GEMINI_VOICES.get(gender, "Aoede")
    output_path = os.path.join(AUDIO_DIR, filename)

    print(f" 🎙️ Audio Synthesizing (Gemini API) with {voice_name}...")

    # Configuration for Speech Generation
    # Note: This uses the generate_content with audio modality
    prompt = f"Read this text realistically, naturally in Thai in an appropriate tone/energy for the script: {text}"

    try:
        response = client.models.generate_content(
            model="gemini-2.5-pro",
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

        # Gemini returns raw audio bytes (PCM or MP3 depending on config)
        # We need to save it.
        # Note: The SDK return format for audio needs handling.
        # Often it's in response.candidates[0].content.parts[0].inline_data.data

        # Checking if we got audio back
        if response.candidates and response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            if part.inline_data:
                import base64
                # Decode base64 audio data
                audio_data = base64.b64decode(part.inline_data.data)

                with open(output_path, "wb") as f:
                    f.write(audio_data)
                return output_path
            else:
                print("   ❌ Gemini response contained no audio data.")
                return None
        return None

    except Exception as e:
        print(f"   ❌ Gemini TTS Failed: {e}")
        return None

async def generate_audio_narration_th(script_data: dict, use_gemini: bool = False):
    """
    Main entry point for audio generation.
    Args:
        script_data (dict): From script_generator.py (must contain 'script_thai' and 'gender')
        use_gemini (bool): If True, tries Gemini first. Defaults to False for safety.
    """
    print("2. 🔊 Starting Audio Generation...")

    text = script_data.get("script_thai", "")
    gender = script_data.get("gender", "F")

    # Sanitize filename from title
    cleaned_title = "".join([c for c in script_data.get("title_thai", "audio") if c.isalnum() or c in (' ', '_')]).rstrip()
    filename = f"{cleaned_title[:20].strip().replace(' ', '_')}_{gender}.mp3"

    output_file = None

    # Try Gemini if bool arg is true
    if use_gemini:
        output_file = await generate_with_gemini(text, gender, filename)

    # Fallback or Default to EdgeTTS
    if not output_file:
        if use_gemini: # only print when gemini bool is set to true
            print("   ⚠️ Falling back to EdgeTTS...")
        output_file = await generate_with_edge_tts(text, gender, filename)

    if output_file:
        print(f"   ✅ Audio saved to: {output_file}")

    return output_file

if __name__ == "__main__":
    # Test Data simulating script_generator output
    test_data = {
        "title_thai": "ช็อกโลก! จับได้แฟนแอบกินแม่ตัวเองคาเตียง!",
        "script_thai": "แก เรื่องนี้พีคสุดในชีวิตฉันละ! คือฉันจับได้เว้ย... ว่าแฟนที่คบกันมา 5 ปีอะ... แอบแซ่บกับแม่ฉันเอง!! คือเรื่องมันเป็นงี้ ฉันกลับบ้านเร็วกะจะเซอร์ไพรส์วันครบรอบไง แต่พอเปิดประตูห้องนอนเข้าไปเท่านั้นแหละ... แม่เจ้าโว้ยยย! ภาพที่เห็นคือช็อกตาแตก! แฟนฉันกับแม่... อยู่บนเตียงเดียวกัน! ในสภาพล่อแหลมมากแก! ตอนนั้นคือสติหลุดไปแล้ว กรี๊ดลั่นบ้านเลย! แต่พอฉันตั้งสติได้แล้วเพ่งดูดีๆนะ... พีคในพีคคือ... สองคนนั้นกำลังนั่งพับถุงก๊อบแก๊บกันอย่างเมามันส์! คือแม่ฉันบอก 'ก็แฟนลูกเขาพับเป็นสามเหลี่ยมสวยดี แม่เลยชวนมาช่วย' สรุปนะ... ฉันเกือบจะบ้านแตกเพราะถุงพลาสติก! ชีวิตฉันมันละครเบอร์ไหนก่อนนน!",
        "gender": "F"
    }

    # Run the test
    asyncio.run(generate_audio_narration_th(
        test_data, use_gemini=True)
    )