import difflib  # <--- Add this to your imports

def _repair_unknown_tokens_with_difflib(original_script_text, mfa_data):
    """
    Replaces <unk> tokens in the MFA output by aligning them with the
    original tokenized script using SequenceMatcher.
    """

    # 1. Re-generate the "Ground Truth" tokens using the EXACT same logic sent to MFA
    # We must ensure we are comparing apples to apples.
    clean_text = _preprocess_thai_text(original_script_text)
    tokenized_string = _tokenize_thai_script(clean_text)
    expected_tokens = tokenized_string.split() # List['แก', 'รร', 'ร', 'เรื่อง'...]

    # 2. Extract the "Noisy" tokens from MFA output
    mfa_tokens = [item['word'] for item in mfa_data]

    # 3. Create the Sequence Matcher
    # We want to transform mfa_tokens INTO expected_tokens where there are errors
    matcher = difflib.SequenceMatcher(None, expected_tokens, mfa_tokens)

    repaired_data = []

    # 4. Iterate through the "Opcodes" (instructions to match the lists)
    # tag: 'equal', 'replace', 'delete', 'insert'
    # i1, i2: indices for expected_tokens (Source Script)
    # j1, j2: indices for mfa_tokens (MFA Output)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():

        if tag == 'equal':
            # The words match perfectly. Keep the MFA data (it has the timestamps).
            repaired_data.extend(mfa_data[j1:j2])

        elif tag == 'replace':
            # This is where <unk> usually happens.
            # Example: expected='เสียงสั่นๆ', mfa='<unk>'

            mfa_chunk = mfa_data[j1:j2]
            script_chunk = expected_tokens[i1:i2]

            # If we have MFA timing data available for this chunk
            if len(mfa_chunk) > 0:
                start_time = mfa_chunk[0]['start']
                end_time = mfa_chunk[-1]['end']

                # Case A: 1-to-1 replacement (Most common)
                # MFA: [<unk>] -> Script: ["เสียงสั่นๆ"]
                if len(mfa_chunk) == len(script_chunk):
                    for k, word in enumerate(script_chunk):
                        repaired_data.append({
                            "word": word,
                            "start": mfa_chunk[k]['start'],
                            "end": mfa_chunk[k]['end']
                        })

                # Case B: N-to-M replacement (Mismatched counts)
                # We distribute the total duration of the MFA chunk across the script words
                else:
                    total_duration = end_time - start_time
                    word_duration = total_duration / len(script_chunk)

                    current_start = start_time
                    for word in script_chunk:
                        repaired_data.append({
                            "word": word,
                            "start": round(current_start, 3),
                            "end": round(current_start + word_duration, 3)
                        })
                        current_start += word_duration

        elif tag == 'insert':
            # MFA has words that aren't in the script? (Rare, usually hallucination or noise)
            # We generally ignore these or keep them if they aren't <unk>
            pass

        elif tag == 'delete':
            # The Script has words, but MFA missed them entirely (skipped over).
            # We can't recover timestamps easily here without interpolation.
            # For now, we skip to avoid breaking the timeline.
            pass

    return repaired_data



def run_mfa_pipeline(
        raw_script_text_from_json,
        audio_file_path,
        output_dir,
        mfa_cmd="mfa"
):
    """
    Transcribes subtitles and timestamps data from input audio and script files with MFA.
    """

    # 1. Setup Environment
    mfa_input_dir, mfa_output_dir = _setup_mfa_directories(output_dir=output_dir)

    # 2. Prepare Text (Clean & Tokenize)
    cleaned_script_text = _preprocess_thai_text(raw_text=raw_script_text_from_json)
    tokenized_clean_script_text = _tokenize_thai_script(thai_text=cleaned_script_text)

    # 3. Stage files
    _stage_audio_and_script_files_for_mfa(
        audio_file_path=audio_file_path,
        tokenized_text=tokenized_clean_script_text,
        mfa_input_dir=mfa_input_dir,
    )

    # 4. Execute Alignment
    _execute_mfa_subprocess(
        input_dir=mfa_input_dir,
        output_dir=mfa_output_dir
    )

    # 5. Parse Results (Contains <unk>)
    raw_aligned_data = _parse_mfa_results(mfa_output_dir=mfa_output_dir)

    # ================================================================
    # 6. REPAIR STEP: Fix <unk> using difflib
    # ================================================================
    print("  🔧 Repairing <unk> tokens...")
    final_aligned_data = _repair_unknown_tokens_with_difflib(
        original_script_text=raw_script_text_from_json,
        mfa_data=raw_aligned_data
    )

    # 7. Save json data
    save_json_file(
        dict_or_json_data=final_aligned_data,
        json_file_name_path=os.path.join(output_dir, "mfa_aligned_transcript_word_timestamp_data.json")
    )

    return final_aligned_data