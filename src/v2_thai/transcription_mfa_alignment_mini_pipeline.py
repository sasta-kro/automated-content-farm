import os
import subprocess
import json
import shutil
import textgrid
from pythainlp.tokenize import word_tokenize
from pythainlp.util import normalize, dict_trie

from src.v2_thai.Util_functions import save_json_file


def post_process_alignment(mfa_json_data, original_tokenized_list):
    """
    Replaces <unk> or mis-spelled words in MFA output with the
    correct word from the original PyThaiNLP tokenization.
    """

    # Check for length mismatch (Crucial Warning)
    if len(mfa_json_data) != len(original_tokenized_list):
        print(f"⚠️ Warning: Token mismatch! Original: {len(original_tokenized_list)} vs MFA: {len(mfa_json_data)}")
        # If lengths don't match, MFA might have skipped a word or merged two.
        # We proceed cautiously, stopping at the shorter length.
        limit = min(len(mfa_json_data), len(original_tokenized_list))
    else:
        limit = len(mfa_json_data)

    fixed_data = []

    for i in range(limit):
        mfa_item = mfa_json_data[i]
        original_word = original_tokenized_list[i]

        # Use the timestamp from MFA
        final_item = {
            "start": mfa_item['start'],
            "end": mfa_item['end'],
            # ALWAYS use the original word for the subtitle text,
            # ignoring what MFA thinks the text is (which might be <unk>)
            "word": original_word
        }
        fixed_data.append(final_item)

    return fixed_data


def run_mfa_pipeline(raw_script_text_from_json, audio_file_path, output_dir, mfa_cmd="mfa"):
    """
    1. Prepares data (tokenizes Thai) for MFA from the inputs.
    2. Calls MFA via subprocess (External Tool).
    3. Parses TextGrid back to JSON.
    """

    # === A. DATA PREPARATION for mfa ===

    # firstly cleaning the thai text from the original script
    #  Normalize Thai chars (fixes weird unicode ordering)
    cleaned_script_text_from_json = normalize(raw_script_text_from_json)

    # Remove invisible chars / zero-width spaces that mess up tokenizers
    cleaned_script_text_from_json = cleaned_script_text_from_json.replace("\u200b", "")

    '''
    MFA cannot "guess" what is being said in the .wav file 
    (it is not a Speech-to-Text engine like Whisper in this mode). 
    It needs the text_script tell it exactly what words are in the audio so it can figure out when those words happen.
    
    The MFA Pairing Logic: When we point MFA to a folder, it looks for pairs with matching names:
    - It finds source.wav → "Okay, here is the sound."
    - It looks for source.lab → "Okay, here are the words I need to find in that sound."

    If we only provided the .wav, MFA would throw an error because it wouldn't know what words to align.
    '''


    # making a folder to put in the prepared data for mfa, and a folder to put in the output files
    temp_mfa_input = os.path.join(output_dir, "mfa_input_data")
    temp_mfa_output = os.path.join(output_dir, "mfa_output_data")
    os.makedirs(temp_mfa_input, exist_ok=True)
    os.makedirs(temp_mfa_output, exist_ok=True)

    # 1. Clean up old files to prevent errors
    for f in os.listdir(temp_mfa_input):
        os.remove(os.path.join(temp_mfa_input, f))

    # 2. Tokenize Thai Script (Must add spaces for MFA)

    # creating a custom dictionary to put inject into tokenization
    # Words that PyThaiNLP usually breaks incorrectly
    custom_words = {
        "อาบอบนวด",  # Brothel (Might get split into อา-บอบ-นวด)
        "ป้ะ",       # Slang for "Right?"
        "แกรร",      # Dragged out "Girl"
        "พอดี",      # Sometimes splits if next to a name
        "ช็อค",      # Shock
        "แม่เจ้าโว้ย", # Exclamation
    }

    # Create a Trie (a specialized data structure for tokenization)
    custom_dictionary_trie = dict_trie(custom_words)

    # 'newmm' is standard dictionary-based tokenizer for Thai? language
    # keep_whitespace=False removes newlines/tabs
    words = word_tokenize(
        cleaned_script_text_from_json,
        engine="newmm",
        custom_dict=custom_dictionary_trie,
        keep_whitespace=False
    )
    tokenized_clean_script_text = " ".join(words) # 1 string

    # 3. Move Audio & Create .lab file
    # We copy and rename audio to 'source.wav' temporarily to keep it simple
    # thus `temp_mfa_input` became a copy of the input audio file
    shutil.copy(src=audio_file_path, dst=os.path.join(temp_mfa_input, "source.wav"))

    # writing the tokenized and clean script text to a .lab file named source
    # .lab file is just a text file .txt but researchers decided to use .lab to
    # denote files that contain the transcript (the words) corresponding to an audio file.
    with open(os.path.join(temp_mfa_input, "source.lab"), "w", encoding="utf-8") as f:
        f.write(tokenized_clean_script_text)


    # === B. EXECUTION (The Bridge to the main pipeline) ===
    print("  ⏳ Running MFA Alignment (this might take a moment)...")

    '''
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
    '''

    command = [
        "conda", "run", "-n", "mfa", "mfa", "align",
        temp_mfa_input, "thai_mfa", "thai_mfa", temp_mfa_output,
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

    # === C. PARSING ===
    # parsing mfa output to json to use in the main pipeline
    textgrid_path = os.path.join(temp_mfa_output, "source.TextGrid")

    if not os.path.exists(textgrid_path):
        raise FileNotFoundError("MFA finished but no .TextGrid file found.")

    textgrid_file = textgrid.TextGrid.fromFile(textgrid_path)
    word_tier = textgrid_file[0] # Usually index 0 is words, 1 is phones

    final_json = []

    for interval in word_tier:
        word = interval.mark
        if not word or word in ["", "<eps>"]:
            continue

        final_json.append({
            "word": word,
            "start": round(interval.minTime, 3),
            "end": round(interval.maxTime, 3)
        })


    # write json for debug
    save_json_file(final_json, os.path.join(output_dir, "mfa_aligned_transcript_word_timestamp_data.json"))

    return final_json




# ========== Testing

if __name__ == "__main__":
    narration_audio_file = 'correct_test_files/raw_original_audio_F_Gem.wav'

    with open('correct_test_files/original_script_data_th.json', "r", encoding="utf-8") as f:
        original_script_content_data_json = json.load(f)

    TEMP_PROCESSING_DIR = "___debug_mfa_pipeline"

    if os.path.exists(narration_audio_file):
        try:
            aligned_transcript_word_and_time_data = run_mfa_pipeline(
                raw_script_text_from_json=original_script_content_data_json['script_thai'],
                audio_file_path=narration_audio_file,
                output_dir=TEMP_PROCESSING_DIR
            )
            print(f"✅ Alignment Complete: {len(aligned_transcript_word_and_time_data)} words aligned.")

        except Exception as e:
            print(f"❌ Alignment Failed: {e}")

    else:
        raise Exception("!!! Raw audio file couldn't be found")











