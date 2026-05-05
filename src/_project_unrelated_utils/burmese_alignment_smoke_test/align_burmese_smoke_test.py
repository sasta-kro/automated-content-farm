"""
Standalone Burmese subtitle alignment smoke test.

Purpose:
This file is not part of the production pipeline yet. It exists to test whether
Burmese script can be aligned to existing Burmese audio without training MFA
models. The experiment uses myword for Burmese syllable tokenization and
MahmoudAshraf97/ctc-forced-aligner for MMS/CTC forced alignment.

Expected input:
- A 16 kHz mono wav file extracted from the generated Burmese MP4.
- A UTF-8 text file containing the exact source_language.script_text from the
  generated QOL YAML file.

Current smoke-test setup:
ffmpeg -y -i src/short_form_content_pipeline/Final_output_videos/UploadReady_20260504_161458_cheatingFeetFetish.mp4 -vn -ac 1 -ar 16000 /private/tmp/burmese_alignment_smoke_audio.wav

.venv/bin/python -c "import yaml; data=yaml.safe_load(open('src/short_form_content_pipeline/Final_output_videos/full_QOL_script_data_cheatingFeetFetish.yaml', encoding='utf-8')); open('/private/tmp/burmese_alignment_smoke_script.txt','w',encoding='utf-8').write(data['source_language']['script_text'])"

Install dependencies:
.venv/bin/pip install transformers uroman myword git+https://github.com/MahmoudAshraf97/ctc-forced-aligner.git
.venv/bin/pip install matplotlib

Run:
.venv/bin/python src/_project_unrelated_utils/burmese_alignment_smoke_test/align_burmese_smoke_test.py /private/tmp/burmese_alignment_smoke_audio.wav /private/tmp/burmese_alignment_smoke_script.txt /private/tmp/burmese_alignment_smoke_output.json syllable

Notes:
Use `syllable` for the original low-level timing test. Use `word` to test
word-level Burmese display timing directly.
"""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib-cache")
os.environ.setdefault("HF_HOME", "/private/tmp/huggingface-burmese-smoke")

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
from burmese_text_tokenization_helpers import (
    tokenize_burmese_script_into_syllables,
    tokenize_burmese_script_into_words,
)


def tokenize_burmese_script_for_alignment(script_text: str, token_mode: str) -> list[str]:
    if token_mode == "syllable":
        return tokenize_burmese_script_into_syllables(script_text)
    if token_mode == "word":
        return tokenize_burmese_script_into_words(script_text)
    raise ValueError(f"Unsupported token mode: {token_mode}")


def main() -> None:
    if len(sys.argv) not in (4, 5):
        raise SystemExit(
            "Usage: python align_burmese_smoke_test.py "
            "audio.wav script.txt output.json [syllable|word]"
        )

    audio_file_path = sys.argv[1]
    script_file_path = Path(sys.argv[2])
    output_json_file_path = Path(sys.argv[3])
    token_mode = sys.argv[4] if len(sys.argv) == 5 else "syllable"

    raw_script_text = script_file_path.read_text(encoding="utf-8")
    display_tokens = tokenize_burmese_script_for_alignment(
        script_text=raw_script_text,
        token_mode=token_mode,
    )

    if not display_tokens:
        raise ValueError(f"No Burmese {token_mode} tokens found in the script text.")

    spaced_script_text = " ".join(display_tokens)
    print(f"Tokenized {len(display_tokens)} Burmese {token_mode} tokens.")
    print("First 40 tokens:", display_tokens[:40])

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
        spaced_script_text,
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
    aligned_items = postprocess_results(
        text_starred,
        spans,
        stride,
        scores,
        merge_threshold=0.0,
    )

    output_items = []
    for aligned_item in aligned_items:
        aligned_text = aligned_item["text"].strip()
        if not aligned_text:
            continue
        output_items.append(
            {
                "word": aligned_text,
                "start": round(float(aligned_item["start"]), 3),
                "end": round(float(aligned_item["end"]), 3),
            }
        )

    output_json_file_path.write_text(
        json.dumps(output_items, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )
    print(f"Wrote {len(output_items)} aligned tokens to {output_json_file_path}")
    print("First 20 aligned items:", output_items[:20])


if __name__ == "__main__":
    main()
