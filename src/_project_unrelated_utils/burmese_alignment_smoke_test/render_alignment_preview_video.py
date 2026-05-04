"""
Standalone subtitle alignment preview renderer.

Purpose:
This file creates a quick visual preview for an alignment JSON file that uses
the same structure as the main pipeline:

[
    {"word": "text", "start": 0.25, "end": 0.67}
]

It is intended for checking whether an experimental alignment method feels
correct in real time before integrating that method into the production
pipeline. The script does not change the main pipeline.

Run example:
.venv/bin/python src/_project_unrelated_utils/burmese_alignment_smoke_test/render_alignment_preview_video.py \
  src/short_form_content_pipeline/Final_output_videos/UploadReady_20260504_161458_cheatingFeetFetish.mp4 \
  tmp_trash/burmese_alignment_smoke_test/burmese_alignment_smoke_output_syllable.json \
  tmp_trash/burmese_alignment_smoke_test/burmese_alignment_preview_syllable.mp4 \
  media_resources/myanmar_fonts/NotoSansMyanmar-Bold.ttf

Note:
Use a font that supports the script being tested. This preview is only a timing
check.
"""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT_PATH = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT_PATH))
os.environ.setdefault(
    "MPLCONFIGDIR",
    str(PROJECT_ROOT_PATH / "tmp_trash" / "matplotlib-cache"),
)

from moviepy.editor import CompositeVideoClip, VideoFileClip

from src.short_form_content_pipeline.generate_subtitle_clip_moviepy import (
    generate_speed_adjusted_subtitle_clips_moviepy_obj,
)


def load_alignment_data(alignment_json_file_path: Path) -> list[dict]:
    with alignment_json_file_path.open("r", encoding="utf-8") as alignment_file:
        return json.load(alignment_file)


def render_alignment_preview_video(
        source_video_file_path: Path,
        alignment_json_file_path: Path,
        output_video_file_path: Path,
        font_file_path: Path,
) -> None:
    alignment_data = load_alignment_data(alignment_json_file_path)

    subtitle_clips = generate_speed_adjusted_subtitle_clips_moviepy_obj(
        word_data_for_normal_speed_dict=alignment_data,
        speed_factor=1.0,
        font_path=str(font_file_path),
        fontsize=120,
        color="yellow",
        stroke_width=5,
        stroke_color="black",
    )

    source_video_clip = VideoFileClip(str(source_video_file_path))
    preview_video_clip = CompositeVideoClip([source_video_clip] + subtitle_clips)
    preview_video_clip = preview_video_clip.set_duration(source_video_clip.duration)
    preview_video_clip = preview_video_clip.set_audio(source_video_clip.audio)

    output_video_file_path.parent.mkdir(parents=True, exist_ok=True)

    preview_video_clip.write_videofile(
        filename=str(output_video_file_path),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        logger="bar",
    )

    source_video_clip.close()
    preview_video_clip.close()


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit(
            "Usage: python render_alignment_preview_video.py "
            "source_video.mp4 alignment.json output_preview.mp4 font.ttf"
        )

    render_alignment_preview_video(
        source_video_file_path=Path(sys.argv[1]),
        alignment_json_file_path=Path(sys.argv[2]),
        output_video_file_path=Path(sys.argv[3]),
        font_file_path=Path(sys.argv[4]),
    )


if __name__ == "__main__":
    main()
