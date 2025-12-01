import difflib
import json
import os
import re
from pprint import pprint

import numpy as np
from pythainlp.tokenize import word_tokenize

from src.v2_thai.Util_functions import save_json_file


def align_transcription_to_script_and_correct_timestamps(original_script, whisper_word_data, output_folder_path =""):
    """
    Aligns a perfect Thai script with messy, character-level Whisper timestamps.
    Returns a list of word-level segments with start/end times.
    """

    print(f"   ⚙️ Starting script correction and timestamp alignment ... .")


    # --- 1. PREPROCESSING: Tokenize and Clean Punctuation ---
    # We use `pythainlp` here because Thai text is written without spaces (e.g., "ilovethai").
    # The `newmm` engine is a dictionary-based algorithm that knows how to split
    # "ilovethai" into ["i", "love", "thai"] correctly.
    tokenized_original_script_words = word_tokenize(original_script, engine="newmm", keep_whitespace=False)

    # Filter out empty strings just in case the tokenizer produced blank items (e.g., from double spaces).
    # and specific punctuation marks
    punctuation_pattern = r'[!?."\'\]'

    tokenized_original_script_words = []
    for w in tokenized_original_script_words:
        clean_w = w.strip()
        # If it's not empty and not just a punctuation mark
        if clean_w and not re.fullmatch(punctuation_pattern, clean_w):
            tokenized_original_script_words.append(clean_w)


    # 2. Flatten Whisper Data for difflib Alignment
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
    # FIX: Instead of a loop, we align the ENTIRE string at once.
    # This guarantees the timeline is monotonic (never jumps back).
    matcher = difflib.SequenceMatcher(None, full_original_script_string, whisper_chars_string)

    # get_opcodes() returns a list of (tag, i1, i2, j1, j2)
    # i1, i2: range in script
    # j1, j2: range in whisper audio
    opcodes = matcher.get_opcodes()

    final_aligned_words = []
    script_char_index = 0

    global_last_end_time = 0.0

    # We iterate through the words and look up their position in the opcodes
    for word in tokenized_original_script_words:
        word_len = len(word)
        word_start_idx = script_char_index
        word_end_idx = script_char_index + word_len

        # Find which audio characters correspond to this script word
        matched_audio_indices = []

        for tag, i1, i2, j1, j2 in opcodes:
            # We only care about 'equal' matches (where text matches audio)
            if tag == 'equal':
                # Check if this opcode block overlaps with our current word
                overlap_start = max(word_start_idx, i1)
                overlap_end = min(word_end_idx, i2)

                if overlap_start < overlap_end:
                    # If the word is 5 chars long, don't match it based on just 1 matching char.
                    match_len = overlap_end - overlap_start
                    if len(word) > 2 > match_len:
                        continue

                    # Calculate the corresponding indices in the audio string
                    # Logic: If script index is K, audio index is J1 + (K - I1)
                    audio_start = j1 + (overlap_start - i1)
                    audio_end = j1 + (overlap_end - i1)

                    matched_audio_indices.extend(range(audio_start, audio_end))

        # 5. Extract Timestamps
        start_time = -1
        end_time = -1

        if matched_audio_indices:
            # Filter indices that are out of bounds
            valid_indices = [i for i in matched_audio_indices if i < len(whisper_string_time_map)]

            if valid_indices:
                # Get raw times
                raw_start = min(whisper_string_time_map[i]['start'] for i in valid_indices)
                raw_end = max(whisper_string_time_map[i]['end'] for i in valid_indices)

                # --- FIX: Strict Monotonicity ---
                # Ensure this word starts AFTER the previous one ended.
                if raw_start < global_last_end_time:
                    raw_start = global_last_end_time

                # Ensure end is after start
                if raw_end <= raw_start:
                    raw_end = raw_start + 0.1 # Minimum duration safety

                start_time = raw_start
                end_time = raw_end

                # Update global tracker
                global_last_end_time = end_time



        final_aligned_words.append({
            "word": word,
            "start": start_time,
            "end": end_time
        })

        script_char_index += word_len

    # 6. Gap Filling (Interpolation)
    # Global alignment leaves gaps (-1) where the audio didn't match the script.
    # We must fill these so subtitles don't disappear.
    # Helper to process a "gap" of missing words
    def fill_gap(start_index, end_index, time_start, time_end):
        count = end_index - start_index
        if count <= 0: return

        duration = time_end - time_start
        step = duration / count

        current_step_time = time_start
        for k in range(start_index, end_index):
            final_aligned_words[k]['start'] = round(current_step_time, 2)
            current_step_time += step
            final_aligned_words[k]['end'] = round(current_step_time, 2)

    # Identify gaps
    gap_start_index = -1

    # 1. Start of file handling
    current_time_anchor = 0.0

    for i in range(len(final_aligned_words)):
        word_obj = final_aligned_words[i]

        if word_obj['start'] == -1:
            # We are in a gap
            if gap_start_index == -1:
                gap_start_index = i
        else:
            # We found a valid word, check if we just closed a gap
            if gap_start_index != -1:
                fill_gap(gap_start_index, i, current_time_anchor, word_obj['start'])
                gap_start_index = -1

            # Update anchor
            current_time_anchor = word_obj['end']

    # 2. End of file handling (if script ends with missing words)
    if gap_start_index != -1:
        # Extrapolate: Assume average word length is 0.5s for the trailing text
        projected_end = current_time_anchor + (0.5 * (len(final_aligned_words) - gap_start_index))
        fill_gap(gap_start_index, len(final_aligned_words), current_time_anchor, projected_end)

    # --- 5. FINAL ROUNDING ---
    for item in final_aligned_words:
        item['start'] = round(item['start'], 2)
        item['end'] = round(item['end'], 2)

    #  save the data as a json file for inspection
    output_json_file_name = "debug_deletelater_aligned_and_corrected_transcription.json"
    full_json_save_path = os.path.join(output_folder_path, output_json_file_name)
    save_json_file(final_aligned_words, full_json_save_path)

    print()

    return final_aligned_words

# ================== EXECUTION

if __name__ == "__main__":

    with open("___temp_script_workspace/original_script_data_th.json", "r", encoding="utf-8") as f:
        full_script_data = json.load(f)
        sample_original_thai_script = full_script_data['script_thai']

    with open("___temp_script_workspace/word_and_timestamps_data_extracted_from_whisper.json", "r", encoding="utf-8") as f:
        sample_raw_whisper_word_data = json.load(f)

    print("before alignment")

    aligned_word_data = align_transcription_to_script_and_correct_timestamps(
        original_script=sample_original_thai_script,
        whisper_word_data = sample_raw_whisper_word_data,
        output_folder_path = "___temp_script_workspace"
    )

    print("after alignment")
    pprint(aligned_word_data[:5])
    # pprint(aligned_word_data, sort_dicts=False) # prints as a formatted json file