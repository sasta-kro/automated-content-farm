import difflib
import json
import os
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

    tokenized_original_script_words = word_tokenize(original_script, engine="newmm", keep_whitespace=False)

    tokenized_original_script_words = [w for w in tokenized_original_script_words if w.strip()]

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

    matcher = difflib.SequenceMatcher(None, full_original_script_string, whisper_chars_string)

    opcodes = matcher.get_opcodes()

    final_aligned_words = []
    script_char_index = 0

    last_valid_end_time = 0.0

    for word in tokenized_original_script_words:
        word_len = len(word)
        word_start_idx = script_char_index
        word_end_idx = script_char_index + word_len

        matched_audio_indices = []

        for tag, i1, i2, j1, j2 in opcodes:

            if tag == 'equal':

                overlap_start = max(word_start_idx, i1)
                overlap_end = min(word_end_idx, i2)

                if overlap_start < overlap_end:

                    match_len = overlap_end - overlap_start
                    if len(word) > 2 > match_len:
                        continue

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

                if raw_end > last_valid_end_time:

                    if raw_start < last_valid_end_time:
                        raw_start = last_valid_end_time

                    start_time = raw_start
                    end_time = raw_end

                    last_valid_end_time = end_time
                else:

                    start_time = -1
                    end_time = -1

        final_aligned_words.append({
            "word": word,
            "start": start_time,
            "end": end_time
        })

        script_char_index += word_len

    for i in range(len(final_aligned_words)):
        current_word = final_aligned_words[i]

        if current_word['start'] == -1:

            prev_end = 0.0
            if i > 0:
                prev_end = final_aligned_words[i-1]['end']

            next_start = prev_end + 0.5

            for j in range(i + 1, len(final_aligned_words)):
                if final_aligned_words[j]['start'] != -1:
                    next_start = final_aligned_words[j]['start']
                    break

            current_word['start'] = prev_end
            current_word['end'] = next_start

            if current_word['end'] - current_word['start'] < 0.05:
                current_word['end'] = current_word['start'] + 0.1

        current_word['start'] = round(current_word['start'], 2)
        current_word['end'] = round(current_word['end'], 2)

    output_json_file_name = "debug_deletelater_aligned_and_corrected_transcription.json"
    full_json_save_path = os.path.join(output_folder_path, output_json_file_name)
    save_json_file(final_aligned_words, full_json_save_path)

    print()

    return final_aligned_words

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

# prints as a formatted json file

