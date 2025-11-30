import mlx_whisper
import json
import os
import asyncio

async def generate_timed_transcript_th(audio_file_path: str):
    """
    Transcribes audio using Apple Silicon optimized Whisper (MLX)
    to get precise word-level timestamps for TikTok dynamic captions.
    """
    print(f"3. 📝 Transcribing Audio for Subtitles: {audio_file_path}")

    if not os.path.exists(audio_file_path):
        print("   ❌ Error: Audio file not found!")
        return None

    try:
        # Transcribe using MLX
        # `word_timestamps=True`    enables it to make dynamic subtitles with accurate timing
        result = mlx_whisper.transcribe(
            audio_file_path,

            # used Turbo model since the largest whisper turbo model only uses ~4-5gb
            path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
            word_timestamps=True,   # This gives us start/end time per word,
            language="th", # forcing to let it know that it is Thai language (ignore warning, it works)
            verbose=False,
        )

        # Parse the result to flatten it into a simple list of words
        # Whisper returns: {'segments': [{'words': [...]}, ...]}

        words_and_time_data = []
        for segment in result.get('segments', []):
            for word_obj in segment.get('words', []):

                # Clean up the word (Whisper often adds spaces)
                clean_word = word_obj['word'].strip()

                if clean_word:      # checks for empty strings
                    words_and_time_data.append({
                        "word": clean_word,
                        "start": word_obj['start'],
                        "end": word_obj['end']
                    })

        print(f"   ✅ Transcription Complete! Found {len(words_and_time_data)} words.")
        print(f"   Sample: {words_and_time_data[:4]}\n")

        return words_and_time_data

    except Exception as e:
        print(f"   ❌ Transcription Failed: {e}")
        return None



if __name__ == "__main__":
    # Test execution
    TEST_AUDIO = "___temp_script_workspace/spedup_audio_narration.mp3"

    if os.path.exists(TEST_AUDIO):
        word_data = asyncio.run(generate_timed_transcript_th(TEST_AUDIO))

    else:
        print("audio file not found")
