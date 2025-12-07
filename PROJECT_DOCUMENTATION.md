# Thai Short-Form Automation Pipeline - Project Documentation

## Table of Contents

1.  **System Overview**
    *   Purpose & Strategy
    *   The "Stealth" Philosophy
2.  **System Architecture**
    *   High-Level Modular Design
    *   Directory Structure
    *   External Dependency Stack
3.  **Data Flow & Object Lifecycle**
    *   Step-by-Step Data Transformation (Text -> Audio -> Sync -> Video)
4.  **Component Deep Dive (The Engines)**
    *   Script Generation (Gemini + Pydantic)
    *   Audio Synthesis (Hybrid Engine + Speed Adjustment)
    *   Phonetic Alignment (MFA + Slang Injection)
    *   Visual Rendering (Pillow/Libraqm for Thai CTL)
    *   Assembly & Metadata Injection (The "Humanizer")
5.  **Operational Guide**
    *   Environment Setup (M3/Conda)
    *   Configuration & Secrets
    *   Execution & Debugging

---

## 1. System Overview

### Purpose & Strategy
This project is an **Algorithmic Media Engine** designed to autonomously produce viral short-form video content (TikTok/Reels/Shorts) tailored specifically for the **Thai demographic**.

The primary objective of this system is to serve as a high-fidelity technical demonstration of **Advanced Python Architecture**, **System Design** and **System Architecture**, proving the capability to integrate disparate technologies—Large Language Models, Neural TTS, and Phonetic Alignment—into a production-grade workflow. By implementing strict **Dependency Injection**, **Singleton Configuration Patterns** (via Pydantic), and sophisticated **Signal Processing**, the project showcases a mastery of solving high-barrier engineering challenges, specifically the accurate rendering of **Complex Text Layout (CTL)** for non-Latin scripts and the precise synchronization of *scriptio continua* languages. While this level of engineering rigor effectively creates a profitable engine for platform monetization and affiliate marketing, the project's core function is to act as a comprehensive portfolio piece, demonstrating the ability to architect robust, "stealth-compliant" automation systems that mimic organic user behavior down to the metadata level.

### The "Stealth" Philosophy
To survive on platforms hostile to bots, the system employs a **Defense-in-Depth** strategy:
1.  **Visual Uniqueness:** Every video uses a unique background segment, mirror-flipped and cropped stochastically to break perceptual hashes.
2.  **Metadata Spoofing:** The final MP4 file carries fabricated ISO 6709 geolocation tags and mobile device signatures (Samsung S24 / CapCut), making uploads appear to come from a real user on a phone via hotspot.

This technology is to be used in conjunction with an anti-bot-detection stealth-focused browser automation workflow (my other project)

---

## 2. System Architecture

### High-Level Modular Design
The system abandons monolithic scripts in favor of a **Linear Synchronous Pipeline**. A central Orchestrator (`main.py`) manages state, while independent "Mini-Pipelines" perform heavy lifting. This allows for isolated testing of specific components (e.g., testing just the subtitle alignment without re-generating audio).

### Directory Structure
```text
project_root/
├── .env                       # API Keys (Gemini)
├── src/
│   ├── short_form_content_pipeline/
│   │   ├── ___0w0__temp_workspace/    # Intermediate Artifacts (Deleted/Overwritten on run)
│   │   ├── _CONFIG.py         # Singleton Settings Manager (Pydantic)
│   │   ├── _CONSTANTS.py      # Hardcoded Prompts & Slang Dictionaries
│   │   ├── main.py            # Orchestrator (Entry Point)
│   │   ├── generate_script.py # Gemini Interface
│   │   ├── generate_audio.py  # EdgeTTS/Gemini + FFmpeg Speedup
│   │   ├── mfa_pipeline.py    # Montreal Forced Aligner Wrapper
│   │   ├── generate_subs.py   # Pillow/Libraqm Renderer
│   │   ├── composite_video.py # MoviePy Assembly
│   │   └── metadata_injector.py # FFmpeg Stream Copy Tool
│   └── Content_profiles/      # YAML Configs (Creative Recipes)
└── media_resources/           # Raw Assets (Background Videos, Fonts)

```

### External Dependency Stack
*   **Runtime:** Python 3.13 (optimized for Apple Silicon M3).
*   **AI:** Google Gemini 2.5 Pro (via `google-genai`).
*   **Audio:** EdgeTTS (production) & Gemini Audio (experimental).
*   **Sync:** Montreal Forced Aligner (MFA) running in a separate Conda environment.
*   **Visuals:** Pillow (with `libraqm` for Thai text shaping), MoviePy, and FFmpeg.

---

## 3. Data Flow & Object Lifecycle

The pipeline transforms a simple string topic into a complex media asset through five distinct stages.

**Stage 1: Concept to Structured Data**
*   **Input:** Topic String (e.g., "Office Drama").
*   **Process:** Gemini generates a script constrained by a **Pydantic Schema**.
*   **Output:** `original_script_data.json` (Title, Script, Gender).

**Stage 2: Text to Audio (Signal Processing)**
*   **Input:** Thai Script Text.
*   **Process:**
    1.  Generate **Raw Audio** (1.0x speed) using EdgeTTS.
    2.  Process via FFmpeg `atempo` filter to create **Sped-Up Audio** (e.g., 1.3x).
*   **Output:** `raw_audio_1x.wav` (for alignment) and `final_audio_1.3x.wav` (for video).

**Stage 3: Audio to Timestamps (The Hard Part)**
*   **Input:** `raw_audio_1x.wav` + Script Text.
*   **Process:**
    1.  Tokenize text using PyThaiNLP + **Custom Slang Injection**.
    2.  Align using **MFA** (Forced Aligner) to get precise start/end times.
*   **Output:** `aligned_transcript.json` (Timestamps at 1.0x speed).

**Stage 4: Timestamps to Visual Assets**
*   **Input:** 1.0x Timestamps.
*   **Process:**
    1.  **Mathematical Compression:** Divide all timestamps by `speed_factor` (1.3) to match the fast audio.
    2.  **Rasterization:** Render each word into a transparent image using Pillow.
*   **Output:** A list of `ImageClip` objects ready for the timeline.

**Stage 5: Final Assembly & Injection**
*   **Input:** Sped-Up Audio, ImageClips, Background Video Library.
*   **Process:**
    1.  Select random BG video, slice time, flip horizontally.
    2.  Speed up BG video to match energy.
    3.  Composite layers -> Render MP4.
    4.  **Post-Process:** Inject "Stealth" metadata via FFmpeg stream copy.
*   **Output:** `FINAL_UPLOAD_READY.mp4`.

---

## 4. Component Deep Dive (The Engines)

This section details the specific engineering decisions behind the five core modules, focusing on how they address the unique challenges of Thai language automation.

### 4.1 Script Generation Module (`generate_script.py`)
**The Challenge:** LLMs often output unstructured chatter or inconsistent formatting, making programmatic parsing fragile.
**The Solution:**
*   **Structured Output:** The module utilizes the `google-genai` SDK with **Pydantic** schema enforcement. A `ThaiScriptOutput` class defines strict types (string, string, enum), forcing the model to return valid JSON. This eliminates the need for regex parsing.
*   **Persona Injection:** System Instructions explicitly define a "Thai Netizen" persona. The model is strictly forbidden from using formal language (ภาษาทางการ) and is mandated to use internet slang, dramatic gossip tones, and first-person narratives.

### 4.2 Audio Synthesis Module (`generate_audio_th_from_script.py`)
**The Challenge:** Generating high-speed "TikTok-style" narration without pitch distortion or robotic artifacts.
**The Solution:**
*   **Hybrid Engine:** The system defaults to **EdgeTTS** (`th-TH-PremwadeeNeural`) for production reliability but supports **Gemini Audio** for experimental expressiveness.
*   **Signal Processing:** To achieve the target "Brainrot" pacing (approx. 1.3x speed), the system does not simply increase the playback rate, which would raise the pitch. Instead, it employs the FFmpeg `atempo` filter. This performs Time-Scale Modification (TSM), compressing duration while mathematically preserving the original vocal formants.

### 4.3 Phonetic Alignment Module (`mfa_pipeline.py`)
**The Challenge:** Thai is a *scriptio continua* language (no spaces between words). Standard splitters fail to determine where one word ends and another begins, causing subtitle desynchronization.
**The Solution:**
*   **Forced Alignment:** The system wraps the **Montreal Forced Aligner (MFA)**. It compares the audio waveform against a Thai acoustic model to calculate millisecond-accurate timestamps for every phoneme.
*   **Slang Injection:** Standard tokenizers (PyThaiNLP) split internet slang incorrectly (e.g., "แกรร" -> "แก" + "ร" + "ร"). The module injects a **Custom Dictionary Trie** containing high-frequency slang terms. This forces the tokenizer to treat these terms as indivisible units, preventing MFA crashes and `<unk>` tokens.

### 4.4 Visual Rendering Module (`generate_subtitle_clip.py`)
**The Challenge:** Standard video libraries (MoviePy/ImageMagick) fail to render Thai **Complex Text Layout (CTL)**. Vowels and tone marks often "float" in the wrong positions or overlap with consonants.
**The Solution:**
*   **Rasterization via Pillow:** The system bypasses MoviePy's text renderer. It uses the **Pillow (PIL)** library compiled with **Libraqm** bindings.
*   **Text Shaping:** Libraqm invokes the **HarfBuzz** engine to calculate precise glyph positioning (OpenType shaping). This ensures tone marks stack vertically correctly. The text is rendered onto transparent images and then converted into video clips.

### 4.5 Assembly & Metadata Injection (`composite_video.py` & `metadata_injector.py`)
**The Challenge:** Evading "Reused Content" filters and "Bot Detection" heuristics on social platforms.
**The Solution:**
*   **Visual Randomization:** The compositor scans a library of long-form gameplay, selects a weighted random segment, and applies a boolean **Mirror Flip**. This fundamentally alters the video's perceptual hash.
*   **Metadata Spoofing:** A post-processing step executes FFmpeg with `-c copy`. It strips all original metadata and injects fabricated tags:
    *   **Geolocation:** Random coordinates within 1km of Assumption University, Bangkok.
    *   **Software:** Signatures mimicking mobile editing apps (e.g., "CapCut 9.6.0 (Android)", "Samsung Galaxy S24").
    *   **Creation Time:** Randomized within the last 72 hours.

---

## 5. Operational Guide

### 5.1 Environment Configuration
The pipeline is optimized for **Apple Silicon (M3)** using Python 3.13. Deployment requires a specific dual-environment setup.

**1. Python Environment (Main Logic)**
*   Requires `ffmpeg-python`, `moviepy`, `google-genai`, `pillow`, and `pydantic-settings`, other reuirements in `requirements.txt`
*   **Critical:** Pillow must be installed *after* system-level text shaping libraries (`libraqm`, `fribidi`, `harfbuzz`) are present to support Thai rendering.

**2. Conda Environment (Alignment)**
*   MFA cannot run in the main Python environment due to dependency conflicts.
*   A separate Conda environment named `mfa` is required.
*   Installation: `conda create -n mfa montreal-forced-aligner` followed by `mfa model download dictionary thai_mfa` and `mfa model download acoustic thai_mfa`. After this, configuring paths manually is not needed. The code deals with the one-time conda environment.

### 5.2 Configuration & Secrets
The system uses a **Singleton Configuration Pattern** to separate code from data.

*   **Secrets (`.env`):**
    *   `GEMINI_API_KEY`: Authentication token for GenAI.
*   **Content Strategy (`Content_profiles/*.yaml`):**
    *   Contains the "Recipe" for the video: Topic, Tone, Speed Factor, Font Styles, and Metadata signatures.
    *   Example: `thai_funny_story.yaml` defines the "Gossip" persona and Android S24 metadata.
*   **Global Settings (`_CONFIG.py`):**
    *   Loads the `.env` and the selected YAML profile into a strictly typed Pydantic object.

### 5.3 Execution & Debugging

**Running the Pipeline**
Execute the orchestrator from the project root:
```bash
python -m src.short_form_content_pipeline.main
```

**Understanding Output**
*   **Console Logs:** The system prints numbered steps (1-6). Wait for `✅ Pipeline Complete`.
*   **Artifacts:** All intermediate files (Raw Audio, MFA TextGrids, Debug Clips) are saved to `___0w0__temp_automation_workspace`.
*   **Final Output:** The upload-ready video is saved to `src/short_form_content_pipeline/Final_output_videos/`.

**Common Debugging Targets**
*   **Sync Issues:** Check `mfa_aligned_transcript_1x_speed_data.json`. If words show `<unk>` or `0.0` duration, the slang dictionary in `_CONSTANTS.py` needs updating.
*   **Font Issues:** If Thai vowels are floating, verify `libraqm` installation. Check `debug_test_subtitle_clip.mp4` in the temp folder for a visual isolation test.
*   **Audio Pitch:** If audio sounds like a chipmunk, ensure `atempo` is being used in `generate_audio_from_script.py` and not simple sample rate manipulation.