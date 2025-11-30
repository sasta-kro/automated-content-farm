import difflib
import json
import os
from pprint import pprint

import numpy as np
from pythainlp.tokenize import word_tokenize

def align_transcription_to_script_and_correct_timestamps(original_script, whisper_word_data):
    """
    Aligns a perfect Thai script with messy, character-level Whisper timestamps.
    Returns a list of word-level segments with start/end times.
    """

    # 1. Tokenize the Perfect Script into Words
    # We use `pythainlp` here because Thai text is written without spaces (e.g., "ilovethai").
    # The `newmm` engine is a dictionary-based algorithm that knows how to split
    # "ilovethai" into ["i", "love", "thai"] correctly.
    tokenized_original_script_words = word_tokenize(original_script, engine="newmm", keep_whitespace=False)

    # Filter out empty strings just in case the tokenizer produced blank items (e.g., from double spaces).
    tokenized_original_script_words = [w for w in tokenized_original_script_words if w.strip()]

    # 2. Flatten Whisper Data for Alignment
    # Whisper returns data in chunks, sometimes grouping multiple characters like "cat" into one timestamp.
    # To compare strictly, we need to flatten this into a character-by-character stream.
    # We create two parallel lists:
    # `whisper_chars_string`: A single string of everything the AI heard (e.g., "c" "a" "t").
    # `whisper_string_time_map`: A list where index N holds the timestamp for the character at index N.
    # e.g. "catsarecute", index=3 will give the start and end timestamps of `s`
    whisper_chars_string = ""
    whisper_string_time_map = [] # stores index mapping to (start, end).
    # e.g. will look like [{'start'=0, 'end'=0.5}, {'start'=0.6, 'end'=1.1}, ...]


    for item in whisper_word_data:
        word_fragment_char = item['word']
        start = item['start']
        end = item['end']

        # Whisper might output multiple chars in one block, or single chars.
        # We loop through them to assign the same timestamp to every character in that block. (thus the nested for-loop)
        # if it is just a char then it just do one loop.
        # Example: if Whisper says "Hi" is at 1.0s, then 'H' is at 1.0s and 'i' is at 1.0s.
        for char in word_fragment_char:
            whisper_chars_string += char
            whisper_string_time_map.append({'start': start, 'end': end})

    # 3. Create a Comparison String from the Script
    # We join our "Perfect Script" words back into one long string.
    # Now we have two massive strings to compare:
    # 1. `full_original_script_string`: The correct text (Reference).
    # 2. `whisper_chars_string`: The messy audio text (Hypothesis).
    full_original_script_string = "".join(tokenized_original_script_words)

    # 4. Use SequenceMatcher to find the best alignment
    # `difflib.SequenceMatcher` is the core engine here. It solves the "Longest Common Subsequence" problem.
    # It compares the two strings and figures out how to align them, even if Whisper had typos
    # (e.g., matching "Hello" in script to "Hullo" in audio).
    matcher = difflib.SequenceMatcher(None, full_original_script_string, whisper_chars_string)

    final_aligned_words = []
    original_script_char_index = 0

    # Iterate through our original perfect script words one by one.
    # We need to find where each specific word lives inside the audio timeline.
    for word in tokenized_original_script_words:
        word_len = len(word)

        # Calculate exactly which characters in `full_original_script_string` belong to this word.
        # Example: If the first word is 2 chars long, we look at index 0 to 2.
        word_start_char_index = original_script_char_index
        word_end_char_index = original_script_char_index + word_len

        # Get the opcodes (match instructions) for this specific word's range.
        # `find_longest_match` asks the matcher:
        # "Look at the audio string (0 to len). Where is the best match for THIS specific script word?"
        matches = matcher.find_longest_match(
            word_start_char_index, word_end_char_index,
            0, len(whisper_chars_string)
        )

        # =========================================================
        # FALLBACK / DEFAULT TIME LOGIC
        # =========================================================
        # Sometimes, the audio is so bad or the script is so different that `matcher` finds NO match.
        # We cannot set the time to 0.0, or the subtitles would flash at the start of the video.
        # Instead, we guess: "This word probably happens right after the previous word."
        start_time = 0.0
        end_time = 0.0

        # now that the start and end times are known, we continue...
        if final_aligned_words:
            # Grab the end time of the word we just finished processing.
            start_time = final_aligned_words[-1]['end']

            # We add a tiny arbitrary duration (0.1s) just so the word exists on the timeline.
            # This ensures the subtitles flow continuously without crashing or resetting to zero.
            end_time = start_time + 0.1

        # =========================================================
        # MATCH FOUND LOGIC
        # =========================================================
        # If `matches.size > 0`, it means `difflib` found this word (or part of it) in the audio text.
        if matches.size > 0:
            # `matches.b` is the starting index in the `whisper_chars_string` (the audio text).
            # `matches.size` is how many characters matched.

            whisper_start_idx = matches.b
            whisper_end_idx = matches.b + matches.size - 1

            # We use these indices to look up the actual floating-point seconds
            # from the map we built in Step 2.

            # Safety check: ensure we don't look past the end of the list.
            if whisper_start_idx < len(whisper_string_time_map):
                start_time = whisper_string_time_map[whisper_start_idx]['start']

            if whisper_end_idx < len(whisper_string_time_map):
                end_time = whisper_string_time_map[whisper_end_idx]['end']

            # HEURISTIC FIX NOTE:
            # Sometimes a script word is 5 chars, but Whisper only pronounced 3 of them clearly.
            # `difflib` might say "I only matched 3 chars".
            # Ideally, we might want to extend the end_time to fill the gap, but the current
            # implementation keeps it simple and strictly uses the matched time.

        # Append the Correct Word with the found (or fallback) Audio Timestamp
        final_aligned_words.append({
            "word": word,
            "start": float(start_time),
            "end": float(end_time)
        })

        # Advance the index tracker so the next loop knows where the next word begins
        original_script_char_index += word_len

    # 5. Post-Processing Cleanup (Fill gaps)
    # Because `difflib` is fuzzy, and audio data is messy, we might end up with illogical times.
    # Example: Word A ends at 5.0s, but Word B starts at 4.8s. This overlap looks bad on screen.
    for i in range(len(final_aligned_words) - 1):
        current_word = final_aligned_words[i]
        next_word = final_aligned_words[i+1]

        # Check for overlap: If the current word runs past the start of the next word.
        if current_word['end'] > next_word['start']:
            # We fix it by cutting the current word short.
            # We set the current word's end time exactly to the next word's start time.
            # This creates a seamless "karaoke" transition with no overlaps.
            current_word['end'] = next_word['start']


        # we also want to keep the decimals max 2 to avoid floating point trailing numbers (e.g. 34.74000000000001)
        current_word['start'] = round(current_word['start'], 2)
        current_word['end'] = round(current_word['end'], 2)

    # --- 6? save the data as a json file for inspection
    output_json_file_name = "aligned_and_corrected_transcription.json"
    if final_aligned_words:
        with open(
                os.path.join("___temp_script_workspace", output_json_file_name), # hard-coded temp workspace path
                "w", encoding="utf-8"
        ) as f:
            json.dump(final_aligned_words, f, ensure_ascii=False, indent=4)
        print(f"  >>> Saved full transcript to '{output_json_file_name}' ")
    else:
        raise f"Couldn't save JSON for transcription. name: {output_json_file_name}"

    return final_aligned_words

# ================== EXECUTION

if __name__ == "__main__":
    test_perfect_thai_script = "แก! ฉันจะเล่าเรื่องสุดพีคให้ฟัง คือเพื่อนแฟนฉันอะ ไปเจอพี่สาวฉันทำงานอยู่ที่…อาบอบนวด! คือเรื่องของเรื่องนะ เพื่อนแฟนนางไปเที่ยวกัน แล้วก็ไปเจอผู้หญิงคนนึงหน้าเหมือนพี่สาวฉันเป๊ะๆ เลยแอบถ่ายรูปส่งมาให้แฟนฉันดู พอฉันเห็นรูปนะ คือช็อคตาแตกไปเลยอะแก มันใช่เลย! ทั้งไฝ ทั้งรอยยิ้ม แต่คือแบบ…งงมาก พี่สาวฉันเนี่ยนะดาวคณะ จะไปทำงานแบบนั้นเพื่ออะไรก่อน?! ฉันทนไม่ไหว เลยตัดสินใจไลน์ไปถามตรงๆ เลยเว้ย ส่งรูปไปให้ดูแล้วถามว่า 'นี่มันอะไรกัน?!' แล้วสิ่งที่พี่สาวฉันตอบกลับมานะแก…นางส่งรูปเซลฟี่ในชุดเดียวกันมา แล้วบอกว่า… 'อ๋อ ร้านคาเฟ่คอสเพลย์เปิดใหม่อะจ้ะ กูทำพาร์ทไทม์เองแหละ อีโง่!' สรุปนะแก ที่เพื่อนแฟนเห็นอะ คือคาเฟ่เมด ไม่ใช่อาบอบนวด! โลเคชั่นมันดันอยู่ติดกันเฉยๆ แม่เจ้า! เกือบได้หยุมหัวพี่สาวตัวเองแล้วมั้ยล่ะ!"

    sample_raw_whisper_word_data = [{'word': 'แ', 'start': np.float64(0.0), 'end': np.float64(0.2)}, {'word': 'ก', 'start': np.float64(0.2), 'end': np.float64(0.24)}, {'word': 'ฉ', 'start': np.float64(0.46), 'end': np.float64(0.66)}, {'word': 'ั', 'start': np.float64(0.66), 'end': np.float64(0.72)}, {'word': 'น', 'start': np.float64(0.72), 'end': np.float64(0.72)}, {'word': 'จะ', 'start': np.float64(0.72), 'end': np.float64(0.84)}, {'word': 'เล', 'start': np.float64(0.84), 'end': np.float64(0.92)}, {'word': '่', 'start': np.float64(0.92), 'end': np.float64(0.92)}, {'word': 'า', 'start': np.float64(0.92), 'end': np.float64(0.98)}, {'word': 'เร', 'start': np.float64(0.98), 'end': np.float64(1.12)}, {'word': 'ื่', 'start': np.float64(1.12), 'end': np.float64(1.12)}, {'word': 'อง', 'start': np.float64(1.12), 'end': np.float64(1.12)}, {'word': 'ส', 'start': np.float64(1.12), 'end': np.float64(1.26)}, {'word': 'ุ', 'start': np.float64(1.26), 'end': np.float64(1.26)}, {'word': 'ด', 'start': np.float64(1.26), 'end': np.float64(1.3)}, {'word': 'พ', 'start': np.float64(1.3), 'end': np.float64(1.42)}, {'word': 'ิ', 'start': np.float64(1.42), 'end': np.float64(1.42)}, {'word': 'ข', 'start': np.float64(1.42), 'end': np.float64(1.48)}, {'word': 'ให', 'start': np.float64(1.48), 'end': np.float64(1.58)}, {'word': '้', 'start': np.float64(1.58), 'end': np.float64(1.6)}, {'word': 'ฟ', 'start': np.float64(1.6), 'end': np.float64(1.7)}, {'word': 'ั', 'start': np.float64(1.7), 'end': np.float64(1.76)}, {'word': 'ง', 'start': np.float64(1.76), 'end': np.float64(1.78)}, {'word': 'ค', 'start': np.float64(1.86), 'end': np.float64(1.94)}, {'word': 'ื', 'start': np.float64(1.94), 'end': np.float64(1.94)}, {'word': 'อ', 'start': np.float64(1.94), 'end': np.float64(1.94)}, {'word': 'เพ', 'start': np.float64(1.94), 'end': np.float64(2.06)}, {'word': 'ื่', 'start': np.float64(2.06), 'end': np.float64(2.06)}, {'word': 'อน', 'start': np.float64(2.06), 'end': np.float64(2.12)}, {'word': 'แ', 'start': np.float64(2.12), 'end': np.float64(2.24)}, {'word': 'ฟ', 'start': np.float64(2.24), 'end': np.float64(2.24)}, {'word': 'น', 'start': np.float64(2.24), 'end': np.float64(2.3)}, {'word': 'ฉ', 'start': np.float64(2.3), 'end': np.float64(2.44)}, {'word': 'ั', 'start': np.float64(2.44), 'end': np.float64(2.46)}, {'word': 'น', 'start': np.float64(2.46), 'end': np.float64(2.5)}, {'word': 'เอ', 'start': np.float64(2.5), 'end': np.float64(2.62)}, {'word': 'า', 'start': np.float64(2.62), 'end': np.float64(2.62)}, {'word': 'ไป', 'start': np.float64(2.62), 'end': np.float64(2.7)}, {'word': 'เจ', 'start': np.float64(2.7), 'end': np.float64(2.82)}, {'word': 'อ', 'start': np.float64(2.82), 'end': np.float64(2.86)}, {'word': 'พ', 'start': np.float64(2.86), 'end': np.float64(2.98)}, {'word': 'ี่', 'start': np.float64(2.98), 'end': np.float64(3.04)}, {'word': 'ส', 'start': np.float64(3.04), 'end': np.float64(3.18)}, {'word': 'า', 'start': np.float64(3.18), 'end': np.float64(3.18)}, {'word': 'ว', 'start': np.float64(3.18), 'end': np.float64(3.22)}, {'word': 'ฉ', 'start': np.float64(3.22), 'end': np.float64(3.32)}, {'word': 'ั', 'start': np.float64(3.32), 'end': np.float64(3.34)}, {'word': 'น', 'start': np.float64(3.34), 'end': np.float64(3.36)}, {'word': 'ทำ', 'start': np.float64(3.36), 'end': np.float64(3.52)}, {'word': 'ง', 'start': np.float64(3.52), 'end': np.float64(3.64)}, {'word': 'าน', 'start': np.float64(3.64), 'end': np.float64(3.7)}, {'word': 'อย', 'start': np.float64(3.7), 'end': np.float64(3.8)}, {'word': 'ู่', 'start': np.float64(3.8), 'end': np.float64(3.84)}, {'word': 'ท', 'start': np.float64(3.84), 'end': np.float64(3.94)}, {'word': 'ี่', 'start': np.float64(3.94), 'end': np.float64(4.0)}, {'word': 'อ', 'start': np.float64(4.0), 'end': np.float64(4.14)}, {'word': 'ั', 'start': np.float64(4.14), 'end': np.float64(4.16)}, {'word': 'บ', 'start': np.float64(4.16), 'end': np.float64(4.22)}, {'word': 'อ', 'start': np.float64(4.22), 'end': np.float64(4.3)}, {'word': 'บ', 'start': np.float64(4.3), 'end': np.float64(4.34)}, {'word': 'carboh', 'start': np.float64(4.34), 'end': np.float64(4.4)}, {'word': 'carboh', 'start': np.float64(4.4), 'end': np.float64(4.5)}, {'word': 'ข', 'start': np.float64(4.5), 'end': np.float64(4.8)}, {'word': 'อง', 'start': np.float64(4.8), 'end': np.float64(4.96)}, {'word': 'carboh', 'start': np.float64(4.96), 'end': np.float64(5.54)}, {'word': 'carboh', 'start': np.float64(5.54), 'end': np.float64(5.54)}, {'word': 'carboh', 'start': np.float64(5.54), 'end': np.float64(5.6)}, {'word': 'carboh', 'start': np.float64(5.6), 'end': np.float64(5.9)}, {'word': 'carboh', 'start': np.float64(5.9), 'end': np.float64(7.54)}, {'word': 'carboh', 'start': np.float64(7.54), 'end': np.float64(7.56)}, {'word': 'carboh', 'start': np.float64(7.56), 'end': np.float64(7.66)}, {'word': 'carboh', 'start': np.float64(7.66), 'end': np.float64(7.66)}, {'word': 'carboh', 'start': np.float64(7.66), 'end': np.float64(7.92)}, {'word': 'carboh', 'start': np.float64(7.92), 'end': np.float64(7.92)}, {'word': 'carboh', 'start': np.float64(7.92), 'end': np.float64(7.92)}, {'word': 'carboh', 'start': np.float64(7.92), 'end': np.float64(7.98)}, {'word': 'carboh', 'start': np.float64(8.620000000000001), 'end': np.float64(8.82)}, {'word': 'carboh', 'start': np.float64(8.82), 'end': np.float64(8.82)}, {'word': 'carboh', 'start': np.float64(8.82), 'end': np.float64(8.9)}, {'word': 'carboh', 'start': np.float64(8.9), 'end': np.float64(8.9)}, {'word': 'carboh', 'start': np.float64(9.32), 'end': np.float64(9.52)}, {'word': 'carboh', 'start': np.float64(9.52), 'end': np.float64(9.6)}, {'word': 'carboh', 'start': np.float64(9.6), 'end': np.float64(9.7)}, {'word': 'carboh', 'start': np.float64(9.7), 'end': np.float64(9.86)}, {'word': 'carboh!', 'start': np.float64(9.86), 'end': np.float64(9.9)}, {'word': 'carboh!!!!!', 'start': np.float64(11.16), 'end': np.float64(11.36)}, {'word': 'carboh!', 'start': np.float64(13.180000000000001), 'end': np.float64(13.38)}, {'word': 'carboh!', 'start': np.float64(13.56), 'end': np.float64(13.68)}, {'word': 'carboh', 'start': np.float64(23.16), 'end': np.float64(23.36)}, {'word': 'พ', 'start': np.float64(23.36), 'end': np.float64(23.36)}, {'word': 'ี่', 'start': np.float64(23.36), 'end': np.float64(23.42)}, {'word': 'ส', 'start': np.float64(23.42), 'end': np.float64(23.56)}, {'word': 'า', 'start': np.float64(23.56), 'end': np.float64(23.58)}, {'word': 'ว', 'start': np.float64(23.58), 'end': np.float64(23.62)}, {'word': 'ฉ', 'start': np.float64(23.62), 'end': np.float64(23.72)}, {'word': 'ั', 'start': np.float64(23.72), 'end': np.float64(23.74)}, {'word': 'น', 'start': np.float64(23.74), 'end': np.float64(23.78)}, {'word': 'ต', 'start': np.float64(23.78), 'end': np.float64(23.88)}, {'word': 'อ', 'start': np.float64(23.88), 'end': np.float64(23.9)}, {'word': 'บ', 'start': np.float64(23.9), 'end': np.float64(23.98)}, {'word': 'ก', 'start': np.float64(23.98), 'end': np.float64(24.1)}, {'word': 'ล', 'start': np.float64(24.1), 'end': np.float64(24.1)}, {'word': 'ั', 'start': np.float64(24.1), 'end': np.float64(24.1)}, {'word': 'บ', 'start': np.float64(24.1), 'end': np.float64(24.14)}, {'word': 'มา', 'start': np.float64(24.14), 'end': np.float64(24.26)}, {'word': 'นะ', 'start': np.float64(24.26), 'end': np.float64(24.36)}, {'word': 'แ', 'start': np.float64(24.36), 'end': np.float64(24.48)}, {'word': 'ก', 'start': np.float64(24.48), 'end': np.float64(24.56)}, {'word': 'น', 'start': np.float64(25.5), 'end': np.float64(25.62)}, {'word': 'ั่', 'start': np.float64(25.62), 'end': np.float64(25.66)}, {'word': 'ง', 'start': np.float64(25.66), 'end': np.float64(25.7)}, {'word': 'ส', 'start': np.float64(25.7), 'end': np.float64(25.8)}, {'word': '่', 'start': np.float64(25.8), 'end': np.float64(25.82)}, {'word': 'ง', 'start': np.float64(25.82), 'end': np.float64(25.9)}, {'word': 'ร', 'start': np.float64(25.9), 'end': np.float64(26.0)}, {'word': 'ู', 'start': np.float64(26.0), 'end': np.float64(26.02)}, {'word': 'ป', 'start': np.float64(26.02), 'end': np.float64(26.06)}, {'word': 'เซ', 'start': np.float64(26.06), 'end': np.float64(26.2)}, {'word': 'ล', 'start': np.float64(26.2), 'end': np.float64(26.24)}, {'word': 'ฟ', 'start': np.float64(26.24), 'end': np.float64(26.36)}, {'word': 'ี่', 'start': np.float64(26.36), 'end': np.float64(26.38)}, {'word': 'ใ', 'start': np.float64(26.38), 'end': np.float64(26.46)}, {'word': 'น', 'start': np.float64(26.46), 'end': np.float64(26.5)}, {'word': 'ช', 'start': np.float64(26.5), 'end': np.float64(26.62)}, {'word': 'ุ', 'start': np.float64(26.62), 'end': np.float64(26.64)}, {'word': 'ด', 'start': np.float64(26.64), 'end': np.float64(26.68)}, {'word': 'เด', 'start': np.float64(26.68), 'end': np.float64(26.76)}, {'word': 'ี', 'start': np.float64(26.76), 'end': np.float64(26.78)}, {'word': 'ย', 'start': np.float64(26.78), 'end': np.float64(26.84)}, {'word': 'วก', 'start': np.float64(26.84), 'end': np.float64(26.9)}, {'word': 'ั', 'start': np.float64(26.9), 'end': np.float64(26.98)}, {'word': 'น', 'start': np.float64(26.98), 'end': np.float64(27.02)}, {'word': 'มา', 'start': np.float64(27.02), 'end': np.float64(27.24)}, {'word': 'แล', 'start': np.float64(28.08), 'end': np.float64(28.2)}, {'word': '้', 'start': np.float64(28.2), 'end': np.float64(28.24)}, {'word': 'ว', 'start': np.float64(28.24), 'end': np.float64(28.28)}, {'word': 'บ', 'start': np.float64(28.28), 'end': np.float64(28.36)}, {'word': 'อก', 'start': np.float64(28.36), 'end': np.float64(28.42)}, {'word': 'ว', 'start': np.float64(28.42), 'end': np.float64(28.56)}, {'word': '่', 'start': np.float64(28.56), 'end': np.float64(28.64)}, {'word': 'า', 'start': np.float64(28.64), 'end': np.float64(28.74)}, {'word': 'อ', 'start': np.float64(28.94), 'end': np.float64(29.06)}, {'word': '๋', 'start': np.float64(29.06), 'end': np.float64(29.14)}, {'word': 'อ', 'start': np.float64(29.14), 'end': 29.36}, {'word': 'ร', 'start': np.float64(30.04), 'end': np.float64(30.16)}, {'word': '้', 'start': np.float64(30.16), 'end': np.float64(30.2)}, {'word': 'าน', 'start': np.float64(30.2), 'end': np.float64(30.24)}, {'word': 'ค', 'start': np.float64(30.24), 'end': np.float64(30.38)}, {'word': 'า', 'start': np.float64(30.38), 'end': np.float64(30.42)}, {'word': 'เฟ', 'start': np.float64(30.42), 'end': np.float64(30.48)}, {'word': '้', 'start': np.float64(30.48), 'end': np.float64(30.52)}, {'word': 'ค', 'start': np.float64(30.52), 'end': np.float64(30.62)}, {'word': 'อ', 'start': np.float64(30.62), 'end': np.float64(30.72)}, {'word': 'ส', 'start': np.float64(30.72), 'end': np.float64(30.74)}, {'word': 'เพ', 'start': np.float64(30.74), 'end': np.float64(30.84)}, {'word': 'ล', 'start': np.float64(30.84), 'end': np.float64(30.88)}, {'word': 'ิ', 'start': np.float64(30.88), 'end': np.float64(30.88)}, {'word': '่', 'start': np.float64(30.88), 'end': np.float64(30.9)}, {'word': 'ม', 'start': np.float64(30.9), 'end': np.float64(31.14)}, {'word': 'ให', 'start': np.float64(31.14), 'end': np.float64(31.16)}, {'word': 'ม', 'start': np.float64(31.16), 'end': np.float64(31.22)}, {'word': '่', 'start': np.float64(31.22), 'end': np.float64(31.28)}, {'word': 'อ', 'start': np.float64(31.28), 'end': np.float64(31.36)}, {'word': 'า', 'start': np.float64(31.36), 'end': np.float64(31.42)}, {'word': 'จ', 'start': np.float64(31.42), 'end': np.float64(31.44)}, {'word': 'ก', 'start': np.float64(31.44), 'end': np.float64(31.54)}, {'word': 'ู', 'start': np.float64(31.54), 'end': np.float64(31.62)}, {'word': 'ทำ', 'start': np.float64(31.62), 'end': np.float64(31.78)}, {'word': 'พ', 'start': np.float64(31.78), 'end': np.float64(31.9)}, {'word': 'า', 'start': np.float64(31.9), 'end': np.float64(31.92)}, {'word': 'ท', 'start': np.float64(31.92), 'end': np.float64(32.0)}, {'word': 'ธ', 'start': np.float64(32.0), 'end': np.float64(32.08)}, {'word': 'าม', 'start': np.float64(32.08), 'end': np.float64(32.12)}, {'word': 'เ', 'start': np.float64(32.12), 'end': np.float64(32.28)}, {'word': 'อง', 'start': np.float64(32.28), 'end': np.float64(32.36)}, {'word': 'ห', 'start': np.float64(32.36), 'end': np.float64(32.46)}, {'word': 'ล', 'start': np.float64(32.46), 'end': np.float64(32.48)}, {'word': 'ะ', 'start': np.float64(32.48), 'end': np.float64(32.52)}, {'word': 'อ', 'start': np.float64(32.52), 'end': np.float64(32.64)}, {'word': 'ี', 'start': np.float64(32.64), 'end': np.float64(32.66)}, {'word': 'โ', 'start': np.float64(32.66), 'end': np.float64(32.7)}, {'word': 'ง', 'start': np.float64(32.7), 'end': np.float64(32.78)}, {'word': '่', 'start': np.float64(32.78), 'end': np.float64(32.98)}, {'word': 'ส', 'start': np.float64(32.98), 'end': np.float64(33.22)}, {'word': 'ร', 'start': np.float64(33.22), 'end': np.float64(33.32)}, {'word': 'ุ', 'start': np.float64(33.32), 'end': np.float64(33.32)}, {'word': 'ป', 'start': np.float64(33.32), 'end': np.float64(33.38)}, {'word': 'นะ', 'start': np.float64(33.38), 'end': np.float64(33.48)}, {'word': 'แ', 'start': np.float64(33.48), 'end': np.float64(33.6)}, {'word': 'ก', 'start': np.float64(33.6), 'end': np.float64(33.62)}, {'word': 'ท', 'start': np.float64(33.62), 'end': np.float64(33.76)}, {'word': 'ี่', 'start': np.float64(33.76), 'end': np.float64(33.8)}, {'word': 'เพ', 'start': np.float64(33.8), 'end': np.float64(33.9)}, {'word': 'ื่', 'start': np.float64(33.9), 'end': np.float64(33.9)}, {'word': 'อน', 'start': np.float64(33.9), 'end': np.float64(34.0)}, {'word': 'แ', 'start': np.float64(34.0), 'end': np.float64(34.1)}, {'word': 'ฟ', 'start': np.float64(34.1), 'end': np.float64(34.14)}, {'word': 'น', 'start': np.float64(34.14), 'end': np.float64(34.18)}, {'word': 'เห', 'start': np.float64(34.18), 'end': np.float64(34.28)}, {'word': '็', 'start': np.float64(34.28), 'end': np.float64(34.3)}, {'word': 'น', 'start': np.float64(34.3), 'end': np.float64(34.34)}, {'word': 'อ', 'start': np.float64(34.34), 'end': np.float64(34.42)}, {'word': '่', 'start': np.float64(34.42), 'end': np.float64(34.48)}, {'word': 'ะ', 'start': np.float64(34.48), 'end': np.float64(34.5)}, {'word': 'ค', 'start': np.float64(34.5), 'end': np.float64(34.56)}, {'word': 'ื', 'start': np.float64(34.56), 'end': np.float64(34.56)}, {'word': 'อ', 'start': np.float64(34.56), 'end': np.float64(34.6)}, {'word': 'ค', 'start': np.float64(34.6), 'end': np.float64(34.7)}, {'word': 'า', 'start': np.float64(34.7), 'end': np.float64(34.76)}, {'word': 'เฟ', 'start': np.float64(34.76), 'end': np.float64(34.86)}, {'word': '้', 'start': np.float64(34.86), 'end': np.float64(34.88)}, {'word': 'เม', 'start': np.float64(34.88), 'end': np.float64(35.04)}, {'word': 'ต', 'start': np.float64(35.04), 'end': np.float64(35.1)}, {'word': 'ร', 'start': np.float64(35.1), 'end': np.float64(35.12)}, {'word': 'ไม', 'start': np.float64(35.12), 'end': np.float64(35.2)}, {'word': '่', 'start': np.float64(35.2), 'end': np.float64(35.24)}, {'word': 'ใช', 'start': np.float64(35.24), 'end': np.float64(35.32)}, {'word': '่', 'start': np.float64(35.32), 'end': np.float64(35.38)}, {'word': 'อ', 'start': np.float64(35.38), 'end': np.float64(35.44)}, {'word': 'ั', 'start': np.float64(35.44), 'end': np.float64(35.46)}, {'word': 'บ', 'start': np.float64(35.46), 'end': np.float64(35.5)}, {'word': 'อ', 'start': np.float64(35.5), 'end': np.float64(35.58)}, {'word': 'บ', 'start': np.float64(35.58), 'end': np.float64(35.62)}, {'word': 'หน', 'start': np.float64(35.62), 'end': np.float64(35.74)}, {'word': 'ว', 'start': np.float64(35.74), 'end': np.float64(35.8)}, {'word': 'ด', 'start': np.float64(35.8), 'end': np.float64(35.88)}, {'word': 'โ', 'start': np.float64(36.03999999999999), 'end': np.float64(36.16)}, {'word': 'ล', 'start': np.float64(36.16), 'end': np.float64(36.18)}, {'word': 'เค', 'start': np.float64(36.18), 'end': np.float64(36.28)}, {'word': 'ช', 'start': np.float64(36.28), 'end': np.float64(36.44)}, {'word': 'ั', 'start': np.float64(36.44), 'end': np.float64(36.52)}, {'word': 'น', 'start': np.float64(36.52), 'end': np.float64(36.52)}, {'word': 'ม', 'start': np.float64(36.52), 'end': np.float64(36.62)}, {'word': 'ั', 'start': np.float64(36.62), 'end': np.float64(36.66)}, {'word': 'น', 'start': np.float64(36.66), 'end': np.float64(36.66)}, {'word': 'ด', 'start': np.float64(36.66), 'end': np.float64(36.76)}, {'word': 'ั', 'start': np.float64(36.76), 'end': np.float64(36.76)}, {'word': 'น', 'start': np.float64(36.76), 'end': np.float64(36.8)}, {'word': 'อย', 'start': np.float64(36.8), 'end': np.float64(36.88)}, {'word': 'ู่', 'start': np.float64(36.88), 'end': np.float64(36.92)}, {'word': 'ต', 'start': np.float64(36.92), 'end': np.float64(36.98)}, {'word': 'ิ', 'start': np.float64(36.98), 'end': np.float64(37.0)}, {'word': 'ด', 'start': np.float64(37.0), 'end': np.float64(37.06)}, {'word': 'ก', 'start': np.float64(37.06), 'end': np.float64(37.16)}, {'word': 'ั', 'start': np.float64(37.16), 'end': np.float64(37.16)}, {'word': 'น', 'start': np.float64(37.16), 'end': np.float64(37.2)}, {'word': 'เฉ', 'start': np.float64(37.2), 'end': np.float64(37.32)}, {'word': 'ย', 'start': np.float64(37.32), 'end': np.float64(37.36)}, {'word': 'ๆ', 'start': np.float64(37.36), 'end': np.float64(37.48)}, {'word': 'แ', 'start': np.float64(37.58), 'end': np.float64(37.64)}, {'word': 'ม', 'start': np.float64(37.64), 'end': np.float64(37.66)}, {'word': '่', 'start': np.float64(37.66), 'end': np.float64(37.7)}, {'word': 'เจ', 'start': np.float64(37.7), 'end': np.float64(37.84)}, {'word': '้', 'start': np.float64(37.84), 'end': np.float64(37.92)}, {'word': 'า', 'start': np.float64(37.92), 'end': np.float64(38.0)}, {'word': 'เก', 'start': np.float64(38.16), 'end': np.float64(38.28)}, {'word': 'ื', 'start': np.float64(38.28), 'end': np.float64(38.3)}, {'word': 'อ', 'start': np.float64(38.3), 'end': np.float64(38.32)}, {'word': 'บ', 'start': np.float64(38.32), 'end': np.float64(38.36)}, {'word': 'ได', 'start': np.float64(38.36), 'end': np.float64(38.44)}, {'word': '้', 'start': np.float64(38.44), 'end': np.float64(38.48)}, {'word': 'ห', 'start': np.float64(38.48), 'end': np.float64(38.56)}, {'word': 'ย', 'start': np.float64(38.56), 'end': np.float64(38.56)}, {'word': 'ุ', 'start': np.float64(38.56), 'end': np.float64(38.58)}, {'word': 'ม', 'start': np.float64(38.58), 'end': np.float64(38.64)}, {'word': 'ห', 'start': np.float64(38.64), 'end': np.float64(38.72)}, {'word': 'ั', 'start': np.float64(38.72), 'end': np.float64(38.74)}, {'word': 'ว', 'start': np.float64(38.74), 'end': np.float64(38.78)}, {'word': 'พ', 'start': np.float64(38.78), 'end': np.float64(38.88)}, {'word': 'ี่', 'start': np.float64(38.88), 'end': np.float64(38.96)}, {'word': 'ส', 'start': np.float64(38.96), 'end': np.float64(39.06)}, {'word': 'า', 'start': np.float64(39.06), 'end': np.float64(39.12)}, {'word': 'ว', 'start': np.float64(39.12), 'end': np.float64(39.16)}, {'word': 'ต', 'start': np.float64(39.16), 'end': np.float64(39.24)}, {'word': 'ั', 'start': np.float64(39.24), 'end': np.float64(39.3)}, {'word': 'ว', 'start': np.float64(39.3), 'end': np.float64(39.3)}, {'word': 'เ', 'start': np.float64(39.3), 'end': np.float64(39.38)}, {'word': 'อง', 'start': np.float64(39.38), 'end': np.float64(39.46)}, {'word': 'แล', 'start': np.float64(39.46), 'end': np.float64(39.56)}, {'word': '้', 'start': np.float64(39.56), 'end': np.float64(39.6)}, {'word': 'ว', 'start': np.float64(39.6), 'end': np.float64(39.64)}, {'word': 'ไ', 'start': np.float64(39.64), 'end': np.float64(39.7)}, {'word': 'หม', 'start': np.float64(39.7), 'end': np.float64(39.74)}, {'word': 'ล', 'start': np.float64(39.74), 'end': np.float64(39.86)}, {'word': '่', 'start': np.float64(39.86), 'end': np.float64(39.88)}, {'word': 'ะ', 'start': np.float64(39.88), 'end': np.float64(39.94)}]

    print("before alignment")

    aligned_word_data = align_transcription_to_script_and_correct_timestamps(
        original_script=test_perfect_thai_script,
        whisper_word_data = sample_raw_whisper_word_data
    )

    print("after alignment")
    # pprint(aligned_word_data, sort_dicts=False) # prints as a formatted json file