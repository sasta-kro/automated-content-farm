import copy
import json
import os
import shutil
import subprocess
import textgrid  # Assuming import
from pythainlp import word_tokenize  # Assuming import
from pythainlp.util import normalize, dict_trie # Assuming import


# Import Constants
from src.short_form_content_pipeline._CONSTANTS import MFA_THAI_SLANG_DICTIONARY
from src.short_form_content_pipeline.Util_functions import save_json_file, set_debug_dir_for_module_of_pipeline



# ==========================================
#        SUB-FUNCTIONS (modules of the mfa mini pipeline)
# ==========================================

def _setup_mfa_directories(output_dir):
    """
    Creates necessary folders and cleans up previous input data.
    Make a folder to put in the prepared data for mfa, and a folder to put in the output files.

    > why do we need to do this? Why are we preparing folders to prepare data for mfa?
    MFA cannot "guess" what is being said in the .wav file
    (it is not a Speech-to-Text engine like Whisper in this mode).
    It needs the text_script tell it exactly what words are in the audio so it can figure out when those words happen.

    The MFA Pairing Logic: When we point MFA to a folder, it looks for pairs with matching names:
    - It finds source.wav → "Okay, here is the sound."
    - It looks for source.lab → "Okay, here are the words I need to find in that sound."

    If we only provided the .wav, MFA would throw an error because it wouldn't know what words to align.
    """


    temp_mfa_input = os.path.join(output_dir, "mfa_input_data")
    temp_mfa_output = os.path.join(output_dir, "mfa_output_data")

    os.makedirs(temp_mfa_input, exist_ok=True)
    os.makedirs(temp_mfa_output, exist_ok=True)

    # Clean up old files in input to prevent errors
    for f in os.listdir(temp_mfa_input):
        os.remove(os.path.join(temp_mfa_input, f))

    return temp_mfa_input, temp_mfa_output


def _preprocess_thai_text(raw_text):
    """Normalizes Thai characters and removes invisible zero-width spaces."""
    # Normalize Thai chars (fixes weird unicode ordering)
    cleaned = normalize(raw_text)
    # Remove invisible chars
    cleaned = cleaned.replace("\u200b", "")
    return cleaned


def _tokenize_thai_script(thai_text):
    """
    Tokenizes Thai text using PyThaiNLP with a custom dictionary injected
    to handle slang/specific words correctly. Returns a space-separated string.

    This is how the words will the seperated for the subtitle. MFA will just align timestamps.
    """

    # Create a Trie (specialized data structure for tokenization)
    custom_dictionary_trie = dict_trie(MFA_THAI_SLANG_DICTIONARY)

    # 'newmm' is standard dictionary-based tokenizer
    words = word_tokenize(
        thai_text,
        engine="newmm",
        custom_dict=custom_dictionary_trie,
        keep_whitespace=False
    )

    # Join into a single string with spaces for MFA
    tokenized_text = " ".join(words)

    return tokenized_text


def _stage_audio_and_script_files_for_mfa(audio_file_path, tokenized_text, mfa_input_dir):
    """
    Copies the audio source file and creates the .lab file from the tokenized words
    These 2 paired files with the same name are required by MFA in the input dir
    """

    # Copy and rename audio to 'source.wav'  temporarily to keep it simple
    # thus `temp_mfa_input` became a copy of the input audio file
    shutil.copy(src=audio_file_path, dst=os.path.join(mfa_input_dir, "source.wav"))

    #  Write the .lab file (transcript)
    # writing the tokenized and clean script text to a .lab file named source.lab
    # .lab file is just a text file .txt but researchers decided to use .lab to
    # denote files that contain the transcript (the words) corresponding to an audio file.
    lab_file_path = os.path.join(mfa_input_dir, "source.lab")
    with open(lab_file_path, "w", encoding="utf-8") as f:
        f.write(tokenized_text)

    # now we should have both the audio and .lab in the same input folder for mfa


def _execute_mfa_subprocess(input_dir, output_dir):
    """
    Constructs the Conda run command and executes MFA alignment via subprocess.

    Set up conda and download mfa first.

    Syntax of mfa:
    `mfa align [input_folder] [dictionary] [acoustic_model] [output_folder]`

    Example command: mfa align ./mfa_input_data thai_mfa thai_mfa ./mfa_output_data --clean --beam 100
    `--beam 100`: Increases the search space. Helps if there are pauses or slight speed variations.
    `--clean`: Clears old cache to prevent errors.


    Usually, we have to do this in the terminal
    ```
    conda activate mfa   # Modifies shell PATH to point to mfa/bin
    mfa align ...        # Runs command
    conda deactivate     # Restores shell PATH
    ```
    but it is a long and there is a short-hand way with just 1 line of command.

    Shorthand 'Exex' Way
    `conda run -n mfa [mfa command]`
    This spins up a temporary sub-shell, sets the `PATH` strictly for that command, executes it, and immediately closes the sub-shell.


    So, the command we want to run in terminal:
    `conda run -n mfa mfa align [input_folder] [dictionary] [acoustic_model] [output_folder] --clean --beam 100`
    Note: we assume 'mfa' env is set up.
    """


    print("  ⏳ Running MFA Alignment (this might take a moment)...")

    # Constructing command to run inside 'mfa' conda environment
    # In the future, we could pull 'mfa' env name from SETTINGS if needed
    command = [
        "conda", "run", "-n", "mfa", "mfa", "align",
        input_dir, "thai_mfa", "thai_mfa", output_dir,
        "--clean", "--beam", "100", "--output_format", "long_textgrid"
    ]

    try:
        # This halts Python until MFA finishes
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(result.stdout) # Uncomment for debugging

    except subprocess.CalledProcessError as e:
        print("❌ MFA Failed!")
        print(e.stderr)
        raise e


def _parse_mfa_results(mfa_output_dir):
    """
    Reads the resulting .TextGrid file from the mfa execution and converts it
    to a clean JSON format that can be used in the main pipeline.
    """
    textgrid_path = os.path.join(mfa_output_dir, "source.TextGrid")

    if not os.path.exists(textgrid_path):
        raise FileNotFoundError("MFA finished but no .TextGrid file found.")

    textgrid_file = textgrid.TextGrid.fromFile(textgrid_path)
    word_tier = textgrid_file[0] # Usually index 0 is words,  1 is phones

    parsed_transcript_timestamp_data = []

    for interval in word_tier:
        word = interval.mark
        # Filter out empty strings or MFA specific silence markers
        if not word or word in ["", "<eps>"]:
            continue

        parsed_transcript_timestamp_data.append({
            "word": word,
            "start": round(interval.minTime, 3),
            "end": round(interval.maxTime, 3)
        })

    return parsed_transcript_timestamp_data


def _repair_unknown_tokens(raw_extracted_mfa_data_json: list[dict]):
    """
    Replaces <unk> tokens in the MFA output with just a blank string for now
    """
    # deep copy since i want the unmodified data to preserve
    repaired_mfa_data_json = copy.deepcopy(raw_extracted_mfa_data_json)

    unknown_token_count = 0

    for segment in repaired_mfa_data_json:
        if segment.get("word") == "<unk>":
            segment["word"] = ""
            unknown_token_count += 1

    print(f"    {unknown_token_count} unknown tokens (<unk>) found. {round(unknown_token_count/len(raw_extracted_mfa_data_json), 2)}% of words were <unk>.")

    return repaired_mfa_data_json


# ==========================================
#        Orchestrator function that runs the mfa pipeline
# ==========================================


def run_mfa_pipeline(
        raw_script_text_from_json: str,
        original_speed_audio_file_path: str,
        output_dir: str,
):
    """
    Orchestrator function for the MFA alignment pipeline.
    Transcribes subtitles and timestamps data from input audio and script files with MFA.
    """

    print("3. 📝 Generating Transcript with word and timestamps for subtitles...")
    print(f"    script: {raw_script_text_from_json[:70]}...")

    # Setup Environment
    mfa_input_dir, mfa_output_dir = _setup_mfa_directories(output_dir=output_dir)

    # Prepare Text (Clean & Tokenize)
    cleaned_script_text = _preprocess_thai_text(raw_text=raw_script_text_from_json)
    tokenized_clean_script_text = _tokenize_thai_script(thai_text=cleaned_script_text)

    # 3. Stage files for mfa (check function description for more info)
    _stage_audio_and_script_files_for_mfa(
        audio_file_path=original_speed_audio_file_path,
        tokenized_text=tokenized_clean_script_text,
        mfa_input_dir=mfa_input_dir,
    )

    # 4. Execute Alignment with MFA in terminal -> this will output file in the output dir
    _execute_mfa_subprocess(
        input_dir=mfa_input_dir,
        output_dir=mfa_output_dir
    )

    # 5. Parse Results to json
    raw_aligned_transcript_data_json = _parse_mfa_results(mfa_output_dir=mfa_output_dir)

    # 6. Repair transcript: Fix <unk> tokens (currently just replacing with empty string)
    repaired_aligned_transcript_data = _repair_unknown_tokens(raw_aligned_transcript_data_json)


    # 7. Save json data as a file for inspection
    save_json_file(
        dict_or_json_data=repaired_aligned_transcript_data,
        json_file_name_path=os.path.join(output_dir, "mfa_aligned_transcript_1x_speed_data.json")
    )

    print(f"✅ Transcription and Timestamp Alignment Complete: {len(repaired_aligned_transcript_data)} words aligned.\n")

    return repaired_aligned_transcript_data


# ==========================================
#        debug main
# ==========================================


if __name__ == "__main__":
    # narration_audio_file = 'correct_test_files/raw_original_audio.wav'

    narration_audio_file = '___debug_dir/_d_audio_generation/raw_original_audio_1x.wav'

    script_path = '___debug_dir/_d_script_generation/original_script_data.json'


    if os.path.exists(script_path) and os.path.exists(narration_audio_file):
        with open(script_path, "r", encoding="utf-8") as f:
            original_script_content_data_json = json.load(f)

        sub_debug_dir = "_d_mfa_pipeline"
        full_debug_dir = set_debug_dir_for_module_of_pipeline(sub_debug_dir)

        try:
            script_text = original_script_content_data_json.get('script_text')

            aligned_transcript_word_and_time_data = run_mfa_pipeline(
                raw_script_text_from_json=script_text,
                original_speed_audio_file_path=narration_audio_file,
                output_dir=full_debug_dir,
            )

            print(f"✅ Transcription and Timestamp Alignment Complete: {len(aligned_transcript_word_and_time_data)} words aligned.\n")

        except Exception as e:
            print(f"❌ Alignment Failed: {e}")
    else:
        print("⚠️ Test files not found. Run previous steps first.")
