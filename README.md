
# Table of Contents

1.  **Project Overview and Objectives**
    1.  **System Purpose**
        *   Definition of the automated short-form content generation pipeline.
        *   Target audience analysis: Thai demographic consumption patterns and platform-specific behaviors (TikTok, Reels, Shorts).
    2.  **Design Philosophy**
        *   **Stealth and Anti-Fingerprinting:** Strategies employed to avoid algorithmic detection (shadowbanning) through metadata manipulation and visual randomization.
        *   **Localization Precision:** The necessity of handling Complex Text Layout (CTL) for Thai language rendering and culturally relevant slang generation.
        *   **Modular Architecture:** The use of independent functional modules orchestrated by a central controller.

2.  **System Architecture and Dependency Graph**
    1.  **High-Level Structure**
        *   Identification of the Entry Point (`main.py`) as the central orchestrator.
        *   Categorization of functional modules (Scripting, Audio, Alignment, Visuals, Assembly).
        *   Role of Utility files (`Util_functions.py`) in data serialization and logging.
    2.  **External Dependency Stack**
        *   **Core Logic:** Python 3.13 environment.
        *   **Generative AI:** Google Gemini 2.5 Pro (via `google-genai` SDK) for creative text generation.
        *   **Audio Synthesis:** Microsoft Edge TTS (`edge-tts`) and Gemini Audio capabilities.
        *   **Signal Processing:** Montreal Forced Aligner (MFA) via Conda environment for phonetic alignment.
        *   **Media Rendering:** FFmpeg (backend) and MoviePy (frontend) for video composition; Pillow (PIL) for rasterized text generation.

3.  **Data Flow Pipeline**
    1.  **Data Object Lifecycle**
        *   **Stage 1: Concept to Text.** Transformation of a raw "Topic" string into a structured JSON object containing Thai script, title, and narrator gender.
        *   **Stage 2: Text to Audio.** Conversion of the JSON script into a raw Audio Waveform file (.wav/.mp3).
        *   **Stage 3: Audio to Temporal Data.** Processing audio and text to generate a `.TextGrid` file, parsed into a JSON list of word-level timestamps.
        *   **Stage 4: Temporal Data to Visual Assets.** Conversion of timestamps into a sequence of transparent ImageClips (rasterized text).
        *   **Stage 5: Asset Composition.** Merging of Audio, ImageClips, and Background Video into a final MP4 container.
    2.  **File System Artifacts**
        *   Breakdown of temporary file generation within the workspace directory.
        *   Naming conventions for intermediate assets (audio files, alignment data, debug clips).

4.  **Component Analysis and Technical Decisions**
    1.  **Script Generation Module (`generate_script_th.py`)**
        *   **Intent:** Automating the creation of viral narratives with specific personas.
        *   **Implementation:** Usage of Gemini System Instructions to enforce a "Netizen/Gossip" tone.
        *   **Technical Choice:** Adoption of Pydantic models to enforce strict JSON schema outputs from the LLM, preventing parsing errors.
    2.  **Audio Synthesis Module (`generate_audio_th_from_script.py`)**
        *   **Intent:** Producing natural-sounding narration compatible with the generated script's gender.
        *   **Hybrid Architecture:** Implementation of a fallback mechanism prioritizing Gemini Audio (experimental/expressive) with a fail-safe switch to EdgeTTS (reliable/native Thai).
        *   **Post-Processing:** Use of FFmpeg `atempo` filters to adjust pacing without altering pitch.
    3.  **Transcript Alignment Module (`mfa_transcript_alignment_mini_pipeline.py`)**
        *   **Intent:** Achieving precise word-level synchronization for dynamic subtitles.
        *   **Challenge:** The lack of spaces in written Thai script rendering standard splitters ineffective.
        *   **Solution:** Integration of the Montreal Forced Aligner (MFA).
        *   **Text Pre-processing:** Implementation of a Custom Dictionary Trie within PyThaiNLP to prevent the tokenization of slang terms (e.g., "แกรร", "จึ้ง").
    4.  **Subtitle Generation Module (`generate_subtitle_clip.py`)**
        *   **Intent:** Rendering Thai text without graphical artifacts.
        *   **The "Floating Vowel" Problem:** Explanation of ImageMagick's inability to handle Thai vertical diacritic stacking (sara-u/sara-i).
        *   **Solution:** Bypassing MoviePy's standard text renderer in favor of the Pillow (PIL) library with `libraqm` bindings to force correct glyph positioning.
    5.  **Video Assembly and Obfuscation Module (`composite_final_video_mini_pipeline.py`)**
        *   **Intent:** Assembling the final asset while mitigating "Reused Content" detection.
        *   **Visual Randomization:** Implementation of weighted random selection, time-segment slicing, and horizontal mirroring.
        *   **Metadata Engineering:** The process of stripping source metadata and injecting fabricated ISO 6709 geolocation data (simulating coordinates near Bangkok/Assumption University) and mobile software tags (e.g., CapCut, InShot).

5.  **Operational Guide**
    1.  **Environment Configuration**
        *   Prerequisites for the Conda environment setup (specifically for MFA).
        *   Font installation requirements (Thai-supported `.ttf` files).
        *   API Key management (`.env` configuration).
    2.  **Execution and Debugging**
        *   Standard execution procedure via `main.py`.
        *   Interpretation of console logs and progress indicators.
        *   Utilization of "Debug" flags to inspect intermediate outputs (e.g., checking the `debug_subtitle_clip.mp4` for sync accuracy).

6.  **Future Development Roadmap**
    1.  **Optimization Targets**
        *   Potential migration from MFA to faster alignment models if latency becomes a bottleneck.
    2.  **Feature Expansion**
        *   Integration of background music ducking (automated volume reduction during speech).
        *   Expansion of the persona library for diverse content types.