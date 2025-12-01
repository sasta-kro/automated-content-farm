import difflib
import json
import os
import re
from pprint import pprint

import numpy as np
from pythainlp.tokenize import word_tokenize

# Assuming this exists in your project structure
from src.v2_thai.Util_functions import save_json_file

def align_transcription_to_script_and_correct_timestamps(original_script, whisper_word_data, output_folder_path=""):
    """
    Aligns a perfect Thai script with messy, character-level Whisper timestamps.
    1. Removes punctuation (!, ?, etc).
    2. Aligns text.
    3. Enforces strict timeline (no overlaps).
    4. Interpolates missing timestamps evenly instead of using hardcoded 0.5s.
    """

    print(f"   ⚙️ Starting script correction and timestamp alignment ... .")

    # --- 1. PREPROCESSING: Tokenize and Clean Punctuation ---
    raw_tokens = word_tokenize(original_script, engine="newmm", keep_whitespace=False)

    # Filter out empty strings AND specific punctuation marks you don't want
    # You can add more symbols to the regex string if needed.
    punctuation_pattern = r'[!?. இவ்"\'\(\)\-]'

    tokenized_original_script_words = []
    for w in raw_tokens:
        clean_w = w.strip()
        # If it's not empty and not just a punctuation mark
        if clean_w and not re.fullmatch(punctuation_pattern, clean_w):
            tokenized_original_script_words.append(clean_w)

    # --- 2. PREPARE WHISPER DATA FOR DIFFLIB ---
    whisper_chars_string = ""
    whisper_string_time_map = []

    for item in whisper_word_data:
        word_fragment_char = item['word']
        start = item['start']
        end = item['end']

        for char in word_fragment_char:
            whisper_chars_string += char
            whisper_string_time_map.append({'start': start, 'end': end})

    full_original_script_string = "".join(tokenized_original_script_words)

    # --- 3. ALIGNMENT (Script Chars vs Whisper Chars) ---
    matcher = difflib.SequenceMatcher(None, full_original_script_string, whisper_chars_string)
    opcodes = matcher.get_opcodes()

    final_aligned_words = []
    script_char_index = 0

    # Track the end of the previous word to prevent "Time Travel"
    global_last_end_time = 0.0

    for word in tokenized_original_script_words:
        word_len = len(word)
        word_start_idx = script_char_index
        word_end_idx = script_char_index + word_len

        matched_audio_indices = []

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'equal':
                # Check for overlap between this word's script indices and the matched block
                overlap_start = max(word_start_idx, i1)
                overlap_end = min(word_end_idx, i2)

                if overlap_start < overlap_end:
                    # Heuristic: Ignore very tiny matches for long words to reduce noise
                    match_len = overlap_end - overlap_start
                    if len(word) > 2 and match_len < 1:
                        continue

                    # Calculate corresponding audio indices
                    audio_start = j1 + (overlap_start - i1)
                    audio_end = j1 + (overlap_end - i1)
                    matched_audio_indices.extend(range(audio_start, audio_end))

        start_time = -1
        end_time = -1

        if matched_audio_indices:
            valid_indices = [i for i in matched_audio_indices if i < len(whisper_string_time_map)]

            if valid_indices:
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

    # --- 4. INTERPOLATION (Fixing the -1s) ---
    # Instead of hardcoding 0.5s, we fill gaps proportionally.

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

    # Save output
    output_json_file_name = "debug_deletelater_aligned_and_corrected_transcription.json"
    full_json_save_path = os.path.join(output_folder_path, output_json_file_name)
    save_json_file(final_aligned_words, full_json_save_path)

    print(f"   ✅ Alignment Complete. Removed punctuation and fixed timestamps.")
    return final_aligned_words

if __name__ == "__main__":
    # Ensure directories exist for testing
    os.makedirs("___temp_script_workspace", exist_ok=True)

    # LOAD DATA (Mock loading for standalone test)
    # Ideally, point this to your actual file paths
    try:
        with open("___temp_script_workspace/original_script_data_th.json", "r", encoding="utf-8") as f:
            full_script_data = json.load(f)
            sample_original_thai_script = full_script_data['script_thai']

        with open("___temp_script_workspace/word_and_timestamps_data_extracted_from_whisper.json", "r", encoding="utf-8") as f:
            sample_raw_whisper_word_data = json.load(f)

        print("--- Before Alignment (Processing...) ---")

        aligned_word_data = align_transcription_to_script_and_correct_timestamps(
            original_script=sample_original_thai_script,
            whisper_word_data = sample_raw_whisper_word_data,
            output_folder_path = "___temp_script_workspace"
        )

        print("--- After Alignment (First 5 words) ---")
        pprint(aligned_word_data[:5])

    except FileNotFoundError:
        print("⚠️  Files not found. Please ensure JSON files exist in '___temp_script_workspace/'")