"""
Burmese text tokenization helpers for local alignment smoke tests.

Purpose:
This module keeps the experimental Burmese tokenizer behavior in one place so
the smoke-test aligner and grouping scripts use the same token cleanup rules.
It is not part of the production pipeline yet.
"""

import unicodedata

from myword import SyllableTokenizer, WordTokenizer


MYANMAR_BLOCKS = (
    ("\u1000", "\u109F"),
    ("\uAA60", "\uAA7F"),
    ("\uA9E0", "\uA9FF"),
)


def token_contains_myanmar_character(token: str) -> bool:
    for character in token:
        for block_start, block_end in MYANMAR_BLOCKS:
            if block_start <= character <= block_end:
                return True
    return False


def token_contains_myanmar_or_alphanumeric_character(token: str) -> bool:
    for character in token:
        if character.isalnum():
            return True
        for block_start, block_end in MYANMAR_BLOCKS:
            if block_start <= character <= block_end:
                return True
    return False


def token_contains_latin_letter(token: str) -> bool:
    return any(("A" <= character <= "Z") or ("a" <= character <= "z") for character in token)


def token_is_only_punctuation_or_symbol(token: str) -> bool:
    return all(
        unicodedata.category(character).startswith(("P", "S"))
        for character in token
    )


def normalize_script_text(script_text: str) -> str:
    return unicodedata.normalize("NFC", script_text)


def token_should_be_displayed(token: str) -> bool:
    if not token:
        return False
    if token_is_only_punctuation_or_symbol(token):
        return False
    return token_contains_myanmar_or_alphanumeric_character(token)


def tokenize_burmese_script_into_syllables(script_text: str) -> list[str]:
    normalized_script_text = normalize_script_text(script_text)
    syllable_tokenizer = SyllableTokenizer()
    syllable_tokens = []

    for raw_line in normalized_script_text.splitlines():
        line_text = raw_line.strip()
        if not line_text:
            continue

        for raw_token in syllable_tokenizer.tokenize(line_text):
            token = raw_token.strip()
            if token_should_be_displayed(token):
                syllable_tokens.append(token)

    return syllable_tokens


def tokenize_burmese_script_into_words(script_text: str) -> list[str]:
    normalized_script_text = normalize_script_text(script_text)
    word_tokenizer = WordTokenizer()
    word_tokens = []

    for raw_line in normalized_script_text.splitlines():
        line_text = raw_line.strip()
        if not line_text:
            continue

        for raw_token in word_tokenizer.tokenize(line_text):
            token = raw_token.strip()
            if token_should_be_displayed(token):
                word_tokens.append(token)

    return word_tokens
