import os
from dotenv import load_dotenv
from google import genai

# Initialize the client
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print(f"{'Model ID':<50} | {'Audio/TTS Capable?'}")
print("-" * 75)

for m in client.models.list():
    # Filter for generation models only
    if "generateContent" in m.supported_actions:

        # HEURISTIC: As of late 2025, audio models explicitly have "tts" or "audio" in their name.
        # There isn't a direct boolean attribute for this yet like there is for 'thinking'.
        is_audio_model = "tts" in m.name.lower() or "audio" in m.name.lower()

        # Optional: You can also check m.display_name if m.name is obscure
        if not is_audio_model and m.display_name:
            is_audio_model = "tts" in m.display_name.lower()

        # Only print if it supports audio/TTS, or print all with a True/False flag
        # (Printing all here so you can see the difference)
        if is_audio_model:
            print(f"{m.name:<50} | ✅ YES")
        # else:
        #     print(f"{m.name:<50} | ❌")