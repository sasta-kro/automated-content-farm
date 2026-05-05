import os
import unicodedata

from src.short_form_content_pipeline.Util_functions import save_json_file


MYANMAR_BLOCKS = (
    ("\u1000", "\u109F"),
    ("\uAA60", "\uAA7F"),
    ("\uA9E0", "\uA9FF"),
)


def character_is_myanmar(character: str) -> bool:
    for block_start, block_end in MYANMAR_BLOCKS:
        if block_start <= character <= block_end:
            return True
    return False


def character_is_latin_letter(character: str) -> bool:
    return ("A" <= character <= "Z") or ("a" <= character <= "z")


def token_contains_myanmar_character(token: str) -> bool:
    return any(character_is_myanmar(character) for character in token)


def token_is_only_punctuation_or_symbol(token: str) -> bool:
    return all(
        unicodedata.category(character).startswith(("P", "S"))
        for character in token
    )


def validate_burmese_script_text(raw_script_text: str) -> None:
    """
    Fail early when another writing system leaks into a Burmese alignment run.

    The Burmese word tokenizer and CTC alignment path are being tested as a Burmese-only
    subtitle path. Mixed Latin or Thai text can shift token boundaries and produce bad
    subtitle timing.
    """
    latin_script_characters = []
    non_myanmar_letter_characters = []

    for character in raw_script_text:
        if character_is_latin_letter(character):
            latin_script_characters.append(character)
        elif unicodedata.category(character).startswith("L") and not character_is_myanmar(character):
            non_myanmar_letter_characters.append(character)

    if latin_script_characters:
        unique_latin_characters = "".join(dict.fromkeys(latin_script_characters))
        raise ValueError(
            "Latin-script text found in Burmese script. "
            f"Characters: {unique_latin_characters}"
        )

    if non_myanmar_letter_characters:
        unique_non_myanmar_characters = "".join(dict.fromkeys(non_myanmar_letter_characters))
        raise ValueError(
            "Non-Myanmar script text found in Burmese script. "
            f"Characters: {unique_non_myanmar_characters}"
        )


def tokenize_burmese_script_into_words(raw_script_text: str) -> list[str]:
    validate_burmese_script_text(raw_script_text=raw_script_text)

    try:
        from myword import WordTokenizer
    except ImportError as import_error:
        raise ImportError(
            "Burmese word tokenization requires `myword`. "
            "Install the Burmese alignment dependencies before running Burmese subtitles."
        ) from import_error

    normalized_script_text = unicodedata.normalize("NFC", raw_script_text)
    word_tokenizer = WordTokenizer()
    word_tokens = []

    for raw_line in normalized_script_text.splitlines():
        line_text = raw_line.strip()
        if not line_text:
            continue

        for raw_token in word_tokenizer.tokenize(line_text):
            token = raw_token.strip()
            if not token:
                continue
            if token_is_only_punctuation_or_symbol(token):
                continue
            if token_contains_myanmar_character(token):
                word_tokens.append(token)

    return word_tokens


def _generate_burmese_ctc_alignment(
        audio_file_path: str,
        tokenized_script_text: str,
) -> list[dict]:
    try:
        import torch
        from ctc_forced_aligner import (
            generate_emissions,
            get_alignments,
            get_spans,
            load_alignment_model,
            load_audio,
            postprocess_results,
            preprocess_text,
        )
    except ImportError as import_error:
        raise ImportError(
            "Burmese CTC alignment requires `torch` and `ctc-forced-aligner`. "
            "Install the Burmese alignment dependencies before running Burmese subtitles."
        ) from import_error

    device = "cpu"
    dtype = torch.float32

    alignment_model, alignment_tokenizer = load_alignment_model(
        device=device,
        dtype=dtype,
    )
    audio_waveform = load_audio(
        audio_file_path,
        dtype=alignment_model.dtype,
        device=alignment_model.device,
    )
    emissions, stride = generate_emissions(
        alignment_model,
        audio_waveform,
        batch_size=1,
    )
    tokens_starred, text_starred = preprocess_text(
        tokenized_script_text,
        romanize=True,
        language="mya",
        split_size="word",
        star_frequency="edges",
    )
    segments, scores, blank_token = get_alignments(
        emissions,
        tokens_starred,
        alignment_tokenizer,
    )
    spans = get_spans(tokens_starred, segments, blank_token)

    return postprocess_results(
        text_starred,
        spans,
        stride,
        scores,
        merge_threshold=0.0,
    )


def _format_burmese_alignment_data(raw_aligned_items: list[dict]) -> list[dict]:
    aligned_transcript_timestamp_data = []

    for aligned_item in raw_aligned_items:
        aligned_text = aligned_item["text"].strip()
        if not aligned_text:
            continue

        aligned_transcript_timestamp_data.append(
            {
                "word": aligned_text,
                "start": round(float(aligned_item["start"]), 3),
                "end": round(float(aligned_item["end"]), 3),
            }
        )

    return aligned_transcript_timestamp_data


def run_burmese_ctc_alignment_pipeline(
        raw_script_text_from_json: str,
        original_speed_audio_file_path: str,
        output_dir: str,
):
    """
    Generates Burmese word-level subtitle timestamps with MMS/CTC forced alignment.
    """

    print("3. 📝 Generating Burmese transcript with word and timestamps for subtitles...")
    print(f"    script: {raw_script_text_from_json[:70]}...")

    burmese_word_tokens = tokenize_burmese_script_into_words(
        raw_script_text=raw_script_text_from_json,
    )

    if not burmese_word_tokens:
        raise ValueError("No Burmese word tokens found in the script text.")

    tokenized_script_text = " ".join(burmese_word_tokens)
    print(f"  ⏳ Running Burmese CTC Alignment with {len(burmese_word_tokens)} word tokens...")

    raw_aligned_items = _generate_burmese_ctc_alignment(
        audio_file_path=original_speed_audio_file_path,
        tokenized_script_text=tokenized_script_text,
    )
    aligned_transcript_data = _format_burmese_alignment_data(
        raw_aligned_items=raw_aligned_items,
    )

    os.makedirs(output_dir, exist_ok=True)
    save_json_file(
        dict_or_json_data=aligned_transcript_data,
        json_file_name_path=os.path.join(output_dir, "burmese_ctc_aligned_transcript_1x_speed_data.json")
    )

    print(f"✅ Burmese Transcription and Timestamp Alignment Complete: {len(aligned_transcript_data)} words aligned.\n")

    return aligned_transcript_data
