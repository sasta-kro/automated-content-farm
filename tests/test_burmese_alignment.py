import unittest
from unittest.mock import patch

from src.short_form_content_pipeline._CONFIG import AlignmentSettings
from src.short_form_content_pipeline.generate_transcript_alignment import (
    generate_aligned_transcript_data,
)


class BurmeseAlignmentRoutingTests(unittest.TestCase):
    def test_burmese_alignment_routes_to_ctc_pipeline(self):
        alignment_settings = AlignmentSettings(
            strategy="mfa",
            tokenizer="burmese",
            mfa_dictionary="burmese_mfa",
            mfa_acoustic_model="burmese_mfa",
        )
        expected_alignment_data = [
            {"word": "ဟဲ့", "start": 0.1, "end": 0.4},
        ]

        with patch(
                "src.short_form_content_pipeline.generate_transcript_alignment.run_burmese_ctc_alignment_pipeline",
                return_value=expected_alignment_data,
                create=True,
        ) as run_burmese_alignment:
            alignment_data = generate_aligned_transcript_data(
                raw_script_text_from_json="ဟဲ့ နင်သိလား",
                original_speed_audio_file_path="voice.wav",
                output_dir="tmp-output",
                language="Burmese",
                use_mfa_alignment=True,
                alignment_settings=alignment_settings,
            )

        self.assertEqual(alignment_data, expected_alignment_data)
        run_burmese_alignment.assert_called_once_with(
            raw_script_text_from_json="ဟဲ့ နင်သိလား",
            original_speed_audio_file_path="voice.wav",
            output_dir="tmp-output",
        )


class BurmeseAlignmentValidationTests(unittest.TestCase):
    def test_burmese_alignment_rejects_latin_script_leakage(self):
        from src.short_form_content_pipeline.burmese_transcript_alignment_mini_pipeline import (
            validate_burmese_script_text,
        )

        with self.assertRaisesRegex(ValueError, "Latin-script"):
            validate_burmese_script_text("ဟဲ့ Shopping Mall သွားတာ")


if __name__ == "__main__":
    unittest.main()
