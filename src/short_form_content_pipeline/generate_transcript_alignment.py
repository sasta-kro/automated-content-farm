from src.short_form_content_pipeline._CONFIG import AlignmentSettings
from src.short_form_content_pipeline.burmese_transcript_alignment_mini_pipeline import run_burmese_ctc_alignment_pipeline
from src.short_form_content_pipeline.mfa_transcript_alignment_mini_pipeline import run_mfa_pipeline


def generate_aligned_transcript_data(
        raw_script_text_from_json: str,
        original_speed_audio_file_path: str,
        output_dir: str,
        language: str,
        use_mfa_alignment: bool,
        alignment_settings: AlignmentSettings,
):
    """
    Routes transcript alignment through the language-specific implementation.

    The rest of the video pipeline only needs a list of dictionaries with word/start/end keys.
    Keeping this routing layer small makes it easier to add Burmese or simple English subtitles
    without making main.py know about tokenizers, MFA models, or fallback strategies.
    """
    if not use_mfa_alignment or alignment_settings.strategy == "disabled":
        raise NotImplementedError(
            "Non-MFA transcript timing is not implemented yet. "
            "Use alignment.strategy='mfa' for the current Thai pipeline."
        )

    if alignment_settings.strategy == "simple":
        raise NotImplementedError(
            "Simple subtitle timing is not implemented yet. "
            "This is the future path for English and other spaced languages."
        )

    if alignment_settings.strategy != "mfa":
        raise ValueError(f"Unsupported alignment strategy: {alignment_settings.strategy}")

    if alignment_settings.tokenizer == "thai":
        return run_mfa_pipeline(
            raw_script_text_from_json=raw_script_text_from_json,
            original_speed_audio_file_path=original_speed_audio_file_path,
            output_dir=output_dir,
            tokenizer=alignment_settings.tokenizer,
            mfa_dictionary=alignment_settings.mfa_dictionary,
            mfa_acoustic_model=alignment_settings.mfa_acoustic_model,
        )

    if alignment_settings.tokenizer == "burmese":
        return run_burmese_ctc_alignment_pipeline(
            raw_script_text_from_json=raw_script_text_from_json,
            original_speed_audio_file_path=original_speed_audio_file_path,
            output_dir=output_dir,
        )

    raise NotImplementedError(
        f"Alignment tokenizer '{alignment_settings.tokenizer}' is not implemented yet."
    )
