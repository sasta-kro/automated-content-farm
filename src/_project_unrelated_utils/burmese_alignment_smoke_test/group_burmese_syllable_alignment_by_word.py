"""
Group Burmese syllable alignment output into word-level display tokens.

Purpose:
This file is a local smoke-test utility. It does not run forced alignment.
Instead, it takes an existing syllable-level alignment JSON and folds adjacent
syllable timestamps into word tokens from the original Burmese script. This
makes it possible to compare per-syllable and word-grouped subtitle previews
without spending time rerunning the alignment model.

Run example:
.venv/bin/python src/_project_unrelated_utils/burmese_alignment_smoke_test/group_burmese_syllable_alignment_by_word.py \
  tmp_trash/burmese_alignment_smoke_test/burmese_alignment_smoke_script.txt \
  tmp_trash/burmese_alignment_smoke_test/burmese_alignment_smoke_output_syllable.json \
  tmp_trash/burmese_alignment_smoke_test/burmese_alignment_smoke_output_word_grouped.json
"""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT_PATH = Path(__file__).resolve().parents[3]
os.environ.setdefault(
    "MPLCONFIGDIR",
    str(PROJECT_ROOT_PATH / "tmp_trash" / "matplotlib-cache"),
)

from burmese_text_tokenization_helpers import (
    token_contains_latin_letter,
    token_contains_myanmar_character,
    tokenize_burmese_script_into_syllables,
    tokenize_burmese_script_into_words,
)


def load_alignment_data(alignment_json_file_path: Path) -> list[dict]:
    with alignment_json_file_path.open("r", encoding="utf-8") as alignment_file:
        return json.load(alignment_file)


def find_first_mismatch(left_tokens: list[str], right_tokens: list[str]) -> str | None:
    for index, left_token in enumerate(left_tokens):
        if index >= len(right_tokens):
            return f"right side ended at token {index}; next left token is {left_token!r}"
        if left_token != right_tokens[index]:
            return (
                f"token {index}: expected {left_token!r}, "
                f"alignment has {right_tokens[index]!r}"
            )

    if len(right_tokens) > len(left_tokens):
        return f"left side ended at token {len(left_tokens)}; next right token is {right_tokens[len(left_tokens)]!r}"

    return None


def get_syllable_count_for_word_token(
        word_token: str,
        script_syllable_tokens: list[str],
        syllable_cursor: int,
) -> int:
    if not token_contains_myanmar_character(word_token):
        if token_contains_latin_letter(word_token):
            return 1
        return 0

    joined_syllable_text = ""
    for syllable_index in range(syllable_cursor, len(script_syllable_tokens)):
        joined_syllable_text += script_syllable_tokens[syllable_index]

        if joined_syllable_text == word_token:
            return syllable_index - syllable_cursor + 1

        if len(joined_syllable_text) > len(word_token) + 4:
            break

    word_syllable_tokens = tokenize_burmese_script_into_syllables(word_token)
    return len(word_syllable_tokens)


def group_syllable_alignment_data_by_word(
        raw_script_text: str,
        syllable_alignment_data: list[dict],
) -> list[dict]:
    script_syllable_tokens = tokenize_burmese_script_into_syllables(raw_script_text)
    aligned_syllable_tokens = [
        syllable_alignment_item["word"]
        for syllable_alignment_item in syllable_alignment_data
    ]

    mismatch_message = find_first_mismatch(
        left_tokens=script_syllable_tokens,
        right_tokens=aligned_syllable_tokens,
    )
    if mismatch_message:
        raise ValueError(
            "Script syllable tokens do not match alignment syllable tokens. "
            f"First mismatch: {mismatch_message}"
        )

    grouped_alignment_data = []
    syllable_cursor = 0

    for word_token in tokenize_burmese_script_into_words(raw_script_text):
        syllable_count_for_word = get_syllable_count_for_word_token(
            word_token=word_token,
            script_syllable_tokens=script_syllable_tokens,
            syllable_cursor=syllable_cursor,
        )

        if syllable_count_for_word == 0:
            continue

        next_syllable_cursor = syllable_cursor + syllable_count_for_word
        grouped_syllable_items = syllable_alignment_data[
            syllable_cursor:next_syllable_cursor
        ]

        if len(grouped_syllable_items) != syllable_count_for_word:
            raise ValueError(f"Not enough syllables left to group word token: {word_token!r}")

        grouped_alignment_data.append(
            {
                "word": word_token,
                "start": grouped_syllable_items[0]["start"],
                "end": grouped_syllable_items[-1]["end"],
            }
        )
        syllable_cursor = next_syllable_cursor

    for remaining_syllable_item in syllable_alignment_data[syllable_cursor:]:
        grouped_alignment_data.append(remaining_syllable_item)

    return grouped_alignment_data


def print_script_quality_notes(raw_script_text: str, word_grouped_alignment_data: list[dict]) -> None:
    word_tokens = [alignment_item["word"] for alignment_item in word_grouped_alignment_data]
    latin_tokens = [token for token in word_tokens if token_contains_latin_letter(token)]
    non_myanmar_tokens = [
        token
        for token in word_tokens
        if not token_contains_myanmar_character(token)
    ]

    print(f"Grouped into {len(word_grouped_alignment_data)} word-level subtitle tokens.")

    if latin_tokens:
        print(f"Latin-script tokens found in source text: {latin_tokens}")

    if non_myanmar_tokens:
        print(f"Non-Myanmar display tokens found in source text: {non_myanmar_tokens}")

    if "ชอบใจฝากกดไลก์กดติดตามไว้เลยนะมึง" in raw_script_text:
        print("Thai hardcoded outro text found in source text.")


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(
            "Usage: python group_burmese_syllable_alignment_by_word.py "
            "script.txt syllable_alignment.json output_word_grouped.json"
        )

    script_file_path = Path(sys.argv[1])
    syllable_alignment_json_file_path = Path(sys.argv[2])
    word_grouped_output_json_file_path = Path(sys.argv[3])

    raw_script_text = script_file_path.read_text(encoding="utf-8")
    syllable_alignment_data = load_alignment_data(syllable_alignment_json_file_path)
    word_grouped_alignment_data = group_syllable_alignment_data_by_word(
        raw_script_text=raw_script_text,
        syllable_alignment_data=syllable_alignment_data,
    )

    word_grouped_output_json_file_path.parent.mkdir(parents=True, exist_ok=True)
    word_grouped_output_json_file_path.write_text(
        json.dumps(word_grouped_alignment_data, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )

    print_script_quality_notes(
        raw_script_text=raw_script_text,
        word_grouped_alignment_data=word_grouped_alignment_data,
    )
    print(f"Wrote grouped alignment to {word_grouped_output_json_file_path}")
    print("First 20 grouped items:", word_grouped_alignment_data[:20])


if __name__ == "__main__":
    main()
