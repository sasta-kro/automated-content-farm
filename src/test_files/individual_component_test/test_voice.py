import asyncio
import edge_tts

VOICE = "en-US-GuyNeural" # The standard male voice
OUTPUT_FILE = "test_pile/test_audio.mp3"

async def main():
    print(f"Generating audio with voice: {VOICE}")
    communicate = edge_tts.Communicate("Hello! I am your automated content machine.", VOICE)
    await communicate.save(OUTPUT_FILE)
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())