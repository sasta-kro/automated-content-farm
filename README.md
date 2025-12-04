
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

# 1. Project Overview and Objectives

## 1.1 System Purpose
The **Thai Short-Form Content Automation Pipeline** is a specialized software solution designed to autonomously generate vertical video content tailored for the Thai social media ecosystem. This project functions as an **Algorithmic Media Pipeline**, transforming raw topic inputs into fully produced, publish-ready video assets without human intervention in the creative process.

The primary objective of this system is to serve as a high-fidelity technical demonstration of **Python-based Automation**, **API Orchestration**, and **System Architecture**. It illustrates the capability to integrate disparate technologies—Large Language Models (LLMs), Text-to-Speech (TTS) synthesis, phonetic alignment engines, and programmatic video editing—into a cohesive workflow.

While the system is engineered to generate supplemental income via platform monetization programs (e.g., Creator Rewards) and affiliate marketing, its core function is to act as a portfolio piece. It demonstrates proficiency in solving complex engineering challenges, such as handling non-Latin script rendering, managing asynchronous data flows, and implementing "stealth" protocols to mimic organic user behavior. The roadmap includes future integration with an **Undetectable Browser Automation** module, which will extend the pipeline to include autonomous uploading, further solidifying the system's status as an end-to-end automated content engine rather than a simple "bot farm."

## 1.2 Design Philosophy

### Stealth and Anti-Fingerprinting
Major social media platforms (TikTok, Instagram, YouTube) utilize sophisticated algorithms to detect and suppress programmatically generated content. To ensure account longevity and algorithmic reach, this system adopts a "Defense-in-Depth" approach to stealth:
*   **Visual Randomization:** The system utilizes weighted random selection logic to pull from a large archive of long-form gameplay footage. It applies dynamic cropping and horizontal mirroring to alter the pixel hash of the background video, preventing "Reused Content" flags.
*   **Metadata Engineering:** The pipeline actively strips all source metadata from input files. It subsequently injects fabricated, "organic" metadata into the final MP4 container. This includes ISO 6709 geolocation tags (simulating coordinates within Bangkok or specifically Assumption University) and software encoding tags that mimic popular mobile editing applications (e.g., CapCut, InShot, VN Video Editor). This makes the output file indistinguishable from a video exported by a human user on a mobile device.

### Localization Precision
Standard text rendering libraries often fail when processing **Complex Text Layout (CTL)** languages like Thai. The Thai writing system relies on vertical stacking, where vowels and tone marks are placed above or below consonant characters. A core design philosophy of this project is strict adherence to linguistic accuracy.
*   **Technical Rendering:** The system bypasses standard CLI-based rendering tools (like ImageMagick default settings) in favor of the **Pillow (PIL)** library with **Libraqm** bindings. This ensures that diacritics are stacked correctly and do not overlap or float, maintaining professional legibility.
*   **Cultural Nuance:** The script generation module is prompted with a specific "Netizen" persona. It is instructed to reject formal language in favor of internet slang, "gossip" tones, and first-person narratives, ensuring the content resonates with local demographic consumption patterns.

### Modular Architecture
The system is constructed using the **Orchestrator Pattern**. Rather than a monolithic script, the logic is segmented into independent functional modules (Scripting, Audio, Alignment, Composition). A central controller (`main.py`) manages the data flow between these modules. This architecture allows for:
*   **Scalability:** Individual modules can be upgraded or swapped (e.g., changing the TTS engine) without breaking the entire pipeline.
*   **Debugging:** Errors can be isolated to specific stages (e.g., a failure in phonetic alignment) without needing to re-run the script generation or video rendering phases.

# 2. System Architecture and Dependency Graph

## 2.1 High-Level Structure

The application follows a linear synchronous pipeline managed by a central entry point. The file structure separates logic (`src/`) from assets (`media_resources/`) and temporary workspaces (`temp_automation_workspace/`).

### Hierarchy

1.  **Entry Point (The Orchestrator)**
    *   **File:** `main.py`
    *   **Role:** This is the execution root. It initializes the environment, defines directory paths, and calls the functional modules in a strict sequence. It manages the passing of data objects (JSON dictionaries, file paths) from one stage to the next.

2.  **Functional Modules (The Workers)**
    *   **Scripting Module:** `generate_script_th.py`
        *   Responsible for interfacing with the Google Gemini API to generate structured JSON data containing the Thai script, title, and narrator gender.
    *   **Audio Module:** `generate_audio_th_from_script.py`
        *   Handles the conversion of text to speech. It implements logic to choose between EdgeTTS (production stability) and Gemini Audio (experimental expressiveness) based on configuration flags.
    *   **Alignment Module:** `mfa_transcript_alignment_mini_pipeline.py`
        *   A wrapper for the Montreal Forced Aligner (MFA). It manages the complex process of normalizing text, preparing `.lab` and `.wav` pairs, executing the external MFA subprocess via Conda, and parsing the resulting `.TextGrid` into a Python dictionary.
    *   **Subtitle Module:** `generate_subtitle_clip.py`
        *   Responsible for converting the timestamped transcript data into visual assets. It generates individual transparent images for every word using Pillow and wraps them into MoviePy `ImageClip` objects.
    *   **Assembly Module:** `composite_final_video_mini_pipeline.py`
        *   The final stage of production. It handles background video selection, time-slicing, audio speed adjustment, and the final rendering of the composite video with metadata injection.

3.  **Utility Layer**
    *   **File:** `Util_functions.py`
    *   **Role:** Contains helper functions used across multiple modules, such as JSON serialization (`save_json_file`) and formatted console logging for debugging metadata injection.

## 2.2 External Dependency Stack

The system relies on a specific stack of external libraries and environments to function.

*   **Runtime Environment:** **Python 3.13** (running on Apple Silicon M3).
*   **Generative AI Layer:**
    *   **Google Gemini 2.5 Pro:** Accessed via `google-genai`. Used for high-temperature (creative) text generation and cultural localization.
*   **Audio Synthesis Layer:**
    *   **Edge-TTS:** Accessed via `edge-tts`. Used for generating high-quality, neural Thai speech without cost.
    *   **FFmpeg:** Accessed via `ffmpeg-python`. Used for signal processing tasks, specifically the `atempo` filter to speed up audio for "brainrot" pacing (1.3x speed) without altering pitch (chipmunk effect).
*   **Phonetic Alignment Layer:**
    *   **Montreal Forced Aligner (MFA):** A standalone tool accessed via a dedicated **Conda environment**. It uses an acoustic model and a dictionary to force-align the spoken audio with the text script.
    *   **PyThaiNLP:** Used for the initial tokenization of Thai text. It is augmented with a **Custom Dictionary Trie** to prevent the tokenizer from incorrectly splitting specific internet slang terms (e.g., "แกรร", "ป้ะ").
*   **Visual Rendering Layer:**
    *   **Pillow (PIL):** The graphics library used to rasterize text. It is compiled with `libraqm` to support Complex Text Layout.
    *   **MoviePy:** The video editing wrapper. It manages the timeline composition of audio, video, and image overlays.
    *   **FFmpeg (Backend):** The core engine driving MoviePy. It is also directly invoked to strip metadata (`-map_metadata -1`) and inject new tags during the final write process.

# 3. Data Flow Pipeline

This section details the lifecycle of data within the automation pipeline, tracing the transformation of a simple text concept into a complex, multi-stream media file. The system relies on a **Linear Synchronous Flow**, meaning each stage must successfully complete and return a specific data object before the next stage begins.

## 3.1 Data Object Lifecycle

The pipeline processes data through five distinct stages. Each stage accepts a specific input, performs a transformation, and outputs a data object or file path required by the subsequent stage.

### Stage 1: Concept to Text (Script Generation)
*   **Input:** A raw string variable defined in `main.py` (e.g., `topic = "I shat in a urinal"`).
*   **Process:** The system sends this topic to the Google Gemini API. The prompt includes "System Instructions" that strictly define the persona (Thai Netizen), tone (Gossip/Slang), and structure (Hook/Body/Twist).
*   **Transformation:** The Large Language Model (LLM) generates a response which is constrained by a **Pydantic Model**. This ensures the output is not unstructured text, but a validated JSON object.
*   **Output:** A dictionary object (`original_script_content_data_json`) containing:
    *   `title_thai`: A clickbait-style title.
    *   `script_thai`: The full spoken narrative in Thai.
    *   `gender`: The detected gender of the narrator ('M' or 'F').

### Stage 2: Text to Audio (Synthesis)
*   **Input:** The `script_thai` text and the `gender` flag from the Stage 1 JSON.
*   **Process:** The logic determines the appropriate Text-to-Speech (TTS) engine. It defaults to **Edge-TTS** for production stability, selecting `th-TH-PremwadeeNeural` (Female) or `th-TH-NiwatNeural` (Male).
*   **Transformation:** The text string is synthesized into an audio waveform.
*   **Output:**
    *   **File Artifact:** A raw audio file saved to the disk (e.g., `raw_original_audio.mp3`).
    *   **Data Object:** A string variable containing the absolute file path to this audio, which serves as the reference for all future synchronization tasks.

### Stage 3: Audio to Temporal Data (Phonetic Alignment)
*   **Input:** The raw audio file path (Stage 2) and the original `script_thai` text (Stage 1).
*   **Process:** This is the most computationally complex stage, managed by the **Montreal Forced Aligner (MFA)** wrapper.
    1.  **Normalization:** The script text is cleaned of invisible characters (zero-width spaces) and tokenized using **PyThaiNLP**. A custom dictionary is injected here to ensure slang words (e.g., "จึ้ง", "แกรร") remain as single tokens rather than being split incorrectly.
    2.  **Staging:** The wrapper creates a temporary directory and generates a `.lab` file (transcript) and a copy of the `.wav` file.
    3.  **Alignment:** A subprocess triggers the MFA engine within a Conda environment. MFA uses an acoustic model to mathematically calculate the start and end times of every phoneme and word.
    4.  **Parsing:** The resulting `.TextGrid` file is parsed by Python.
*   **Output:** A list of dictionaries (`aligned_transcript_word_and_time_data`). Each dictionary represents one word and contains:
    *   `word`: The text of the word.
    *   `start`: The start time in seconds (float).
    *   `end`: The end time in seconds (float).

### Stage 4: Temporal Data to Visual Assets (Subtitle Rendering)
*   **Input:** The list of word timestamps from Stage 3.
*   **Process:** The system iterates through the timestamp list to create visual elements.
    1.  **Rasterization:** For every word, the **Pillow (PIL)** library draws the text onto a transparent canvas using a Thai-supported font (e.g., "Prompt-Bold"). This fixes the "floating vowel" issue common in other renderers.
    2.  **Object Creation:** The resulting image is converted into a NumPy array and wrapped in a MoviePy `ImageClip` object.
    3.  **Timing:** The `ImageClip` is assigned the exact duration (`end` - `start`) calculated by MFA.
*   **Output:** A list of `ImageClip` objects (`list_of_moviepyTextClips`) stored in memory. These are ready to be overlaid onto the video timeline.

### Stage 5: Asset Composition (Assembly & Obfuscation)
*   **Input:** The raw audio file (Stage 2), the list of subtitle clips (Stage 4), and the path to the media resource library.
*   **Process:** The Orchestrator constructs the final timeline.
    1.  **Background Selection:** The system scans the media folder, identifies video files longer than the audio duration, and selects one using a weighted random algorithm (favoring longer files to maximize variance).
    2.  **Visual Manipulation:** A segment matching the audio length is sliced from the source video. It is then center-cropped to a 9:16 aspect ratio and randomly mirror-flipped to alter the visual fingerprint.
    3.  **Audio Processing:** The audio is sped up (typically by a factor of 1.3x) using FFmpeg's `atempo` filter to increase information density ("brainrot" pacing). The video duration is compressed to match this new speed.
    4.  **Rendering:** The video, sped-up audio, and subtitle overlays are merged.
    5.  **Metadata Injection:** During the write process, FFmpeg strips all original metadata and injects new, fabricated tags (e.g., "Location: Bangkok", "Software: CapCut").
*   **Output:** A fully rendered `.mp4` file (e.g., `FINAL_UPLOAD_READY_20231203_193045.mp4`) ready for manual transfer to the upload device.

## 3.2 File System Artifacts

The pipeline maintains a "clean workspace" philosophy. All intermediate files are generated within a designated temporary directory (`___0w0__temp_automation_workspace`) to avoid cluttering the source code directories.

*   **`original_script_data_th.json`**: The raw JSON output from Gemini. Useful for debugging script quality or gender detection errors.
*   **`raw_original_audio.mp3`**: The initial TTS output at normal speed.
*   **`mfa_input_data/`**: A directory containing the `source.wav` and `source.lab` pair required by the aligner.
*   **`mfa_output_data/`**: A directory containing the `source.TextGrid` file generated by MFA.
*   **`mfa_aligned_transcript_data.json`**: A JSON dump of the word-level timestamps. Essential for verifying if the alignment logic worked correctly.
*   **`spedup_audio_narration.mp3`**: The processed audio file (1.3x speed) used in the final render.
*   **`temp_render_normal_speed.mp4`**: An intermediate video file (optional/deleted in production) sometimes generated before the final speed-up pass.
*   **`FINAL_UPLOAD_READY_[Timestamp].mp4`**: The final product. This is the only file intended for distribution.

# 4. Component Analysis and Technical Decisions

This section provides a granular analysis of the five core functional modules that constitute the pipeline. For each module, we define the operational intent (the problem being solved), the implementation strategy, and the specific technical decisions made to overcome challenges inherent to Thai language processing and automated media generation.

## 4.1 Script Generation Module (`generate_script_th.py`)

### Intent
The objective of this module is to automate the creative writing process, generating narrative content that mimics the specific cadence, vocabulary, and tonal structures of viral Thai social media trends. A generic translation of English scripts is insufficient; the content must fundamentally originate from a "Thai Netizen" persona to achieve algorithmic resonance.

### Implementation Strategy
The module utilizes the **Google Gemini 2.5 Pro** model via the `google-genai` SDK. The generation process is governed by a strict prompt architecture:
*   **System Instructions:** We inject a persistent persona definition into the model context. The AI is explicitly instructed to act as a "Gossip/Storyteller" (นักเล่าเรื่อง), strictly forbidden from using formal language (ภาษาทางการ), and mandated to employ specific internet slang constructs (e.g., "แก", "คือแบบ", "พีคมาก").
*   **Structural Constraints:** The prompt enforces a three-act structure optimized for short-form retention: a 3-second Hook, a fast-paced Body, and a Plot Twist/Ending.

### Key Technical Decision: Structured Output via Pydantic
In earlier iterations of LLM integration, parsing errors were common when the model returned Markdown formatting or conversational filler alongside the JSON data.
*   **The Solution:** We leverage the **Pydantic** library to define a strict data schema (`ThaiScriptOutput`). This schema mandates three specific fields: `title_thai`, `script_thai`, and `gender`.
*   **The "Why":** By passing this schema to the Gemini API's `response_schema` configuration, we force the model to perform **constrained decoding**. The API guarantees that the output will be valid JSON adhering to our data types. This eliminates the need for fragile regular expressions or error-prone text parsing logic, creating a deterministic interface with a non-deterministic generative model.

## 4.2 Audio Synthesis Module (`generate_audio_th_from_script.py`)

### Intent
The goal is to convert the generated text into high-fidelity audio that sounds natural to native Thai speakers. The voice must match the gender identified in the script generation phase to maintain narrative consistency.

### Implementation Strategy
The module implements a **Hybrid Engine Architecture** with a toggleable fallback mechanism:
1.  **Primary Engine (Edge-TTS):** The system defaults to Microsoft Edge's online text-to-speech service (`edge-tts`). We utilize the neural voices `th-TH-PremwadeeNeural` (Female) and `th-TH-NiwatNeural` (Male). These voices are currently the industry standard for "faceless" content due to their prosodic naturalness and correct tonal pronunciation of Thai.
2.  **Experimental Engine (Gemini Audio):** The code includes bindings for Gemini's native audio generation capabilities (`Aoede` and `Charon` voices). While theoretically more expressive, this path is currently treated as experimental due to inconsistent Thai pronunciation in the current model version.

### Key Technical Decision: Signal Processing via FFmpeg
Raw TTS output is often too slow for the hyper-stimulated environment of TikTok/Reels.
*   **The Solution:** We implement a post-processing step using **FFmpeg** (via the `ffmpeg-python` wrapper).
*   **The "Why":** Simply increasing playback speed changes the pitch, resulting in a "chipmunk effect" that reduces content credibility. We utilize the `atempo` (Audio Tempo) filter, which employs a **Time-Scale Modification (TSM)** algorithm. This allows us to compress the audio duration (typically by a factor of 1.2x to 1.3x) while mathematically preserving the original pitch and formants of the voice.

## 4.3 Transcript Alignment Module (`mfa_transcript_alignment_mini_pipeline.py`)

### Intent
To achieve the "Dynamic Caption" style popular on short-form platforms, where subtitles appear word-by-word in perfect sync with the audio.

### The Challenge: Thai Text Segmentation
Thai is a scriptio continua language, meaning written sentences do not use spaces to separate words. A standard splitting method (e.g., `text.split(" ")`) is impossible. While **PyThaiNLP** can tokenize text based on a dictionary, it creates a discrepancy: the tokenizer might split a word grammatically (e.g., "swimming" -> "swim" + "ing"), but the audio might pronounce it as a single continuous sound. This causes "drift" where the subtitles desynchronize from the audio.

### Implementation Strategy: Montreal Forced Aligner (MFA)
We bypass simple text-to-time heuristics in favor of **Phonetic Alignment**. The module wraps a standalone **MFA** installation running in a Conda environment.
1.  **Staging:** The Python script creates a temporary "Lab" (`.lab`) file containing the text and a copy of the audio.
2.  **Forced Alignment:** MFA analyzes the audio waveform against a Thai acoustic model and a pronunciation dictionary. It calculates the most probable start and end times for each phoneme and aggregates them into word-level timestamps.

### Key Technical Decision: Custom Trie Injection
Standard tokenizers fail on internet slang. For example, the word "แกรร" (Girl/Friend, dragged out for emphasis) might be split by PyThaiNLP into "แก" (You) + "ร" + "ร" because "แกรร" is not in the official Thai dictionary.
*   **The Solution:** We implement a **Custom Dictionary Trie**. Before passing text to MFA, we inject a list of specific "Netizen Slang" terms (e.g., "จึ้ง", "ป้ายยา", "อาบอบนวด") into the tokenizer.
*   **The "Why":** This forces the tokenizer to treat these slang terms as single, indivisible tokens. This ensures that the generated transcript matches the "chunks" of sound in the audio file, preventing alignment crashes or massive synchronization errors.

## 4.4 Subtitle Generation Module (`generate_subtitle_clip.py`)

### Intent
To generate high-quality visual text overlays (subtitles) that can be composited onto the video timeline.

### The Challenge: Complex Text Layout (CTL)
The MoviePy library relies on **ImageMagick** for text rendering. ImageMagick often fails to correctly handle Thai **Vertical Stacking**. In Thai, vowels and tone marks (e.g.,  ้,  ิ,  ุ) are placed above or below the consonant. Without proper "Text Shaping," these marks often float in the wrong position, overlap with the consonant, or turn into square boxes (tofu).

### Implementation Strategy: Rasterization via Pillow (PIL)
We abandoned MoviePy's internal `TextClip` in favor of a custom implementation using the **Pillow** library.
1.  **Canvas Creation:** For every word, we create a transparent RGBA canvas.
2.  **Drawing:** We use `ImageDraw` to render the text onto the canvas using a Thai-compatible font (e.g., "Prompt-Bold").
3.  **Conversion:** The resulting image is converted into a NumPy array, which MoviePy can accept as a raw `ImageClip`.

### Key Technical Decision: Libraqm Binding
*   **The Solution:** The Pillow installation is compiled with **Libraqm** (a library for complex text layout). In the code, we explicitly specify `layout_engine=ImageFont.LAYOUT_RAQM`.
*   **The "Why":** Libraqm invokes the **HarfBuzz** text shaping engine. This engine understands the specific OpenType logic required for Thai. It calculates exactly how many pixels to raise a tone mark so it sits perfectly above a vowel, ensuring professional-grade typography that native speakers find legible.

## 4.5 Video Assembly and Obfuscation Module (`composite_final_video_mini_pipeline.py`)

### Intent
To assemble the final video asset while simultaneously masking its automated origins to evade "Bot" detection and "Reused Content" filters on social platforms.

### Implementation Strategy: Visual Randomization
The module scans a local library of long-form Minecraft gameplay videos (often hours long).
*   **Weighted Selection:** It employs a weighted random algorithm to select a background video, favoring longer files to maximize the pool of unused footage.
*   **Stochastic Slicing:** It selects a random start time $T$ such that the segment $T + Duration$ falls within the video bounds.
*   **Pixel Manipulation:** The clip is center-cropped to a 9:16 aspect ratio. Crucially, a random boolean check determines whether to apply a **Mirror Flip (Horizontal)**. This fundamentally alters the pixel hash of the video frames, making duplicate detection algorithms significantly less effective.

### Key Technical Decision: Metadata Engineering (Stealth)
Platforms analyze file metadata to determine the source of a video. A file output by `ffmpeg-python` defaults to tags indicating "Lavf" (Libavformat), which is a clear signature of automated software.
*   **Sanitation:** The system executes FFmpeg with the flag `-map_metadata -1`. This is a "nuclear option" that strips all existing metadata from the source gameplay and audio files, removing any potential copyright signatures or previous modification dates.
*   **Injection (The Spoof):** During the final write process, the system injects a suite of fabricated metadata:
    *   `creation_time`: Set to the current system time to simulate a fresh export.
    *   `location`: Injects **ISO 6709** coordinates randomized within a 1km radius of Assumption University or Bangkok. This signals to the platform's algorithm that the uploader is a local user in Thailand, boosting regional reach.
    *   `software` / `make` / `model`: Rotates through a predefined list of mobile identifiers (e.g., "CapCut 9.6.0 (Android)", "iPhone 14 Pro"). This attempts to fool the platform into categorizing the upload as "User Generated Content" (UGC) from a mobile device rather than "Programmatic Content" from a server.




# 5. Operational Guide

This section outlines the specific environmental prerequisites and execution procedures required to operate the pipeline. It serves as a manual for replicating the development environment and troubleshooting runtime anomalies.

## 5.1 Environment Configuration

The system is architected to run on **Apple Silicon (M3)** hardware, leveraging the `mlx` optimizations for Python 3.13. Deployment on other architectures (x86 Windows/Linux) requires significant modification to the dependency stack, particularly regarding the Montreal Forced Aligner (MFA) and Pillow compilation.

### Prerequisites
*   **Python Environment:** A dedicated virtual environment running **Python 3.13+**.
*   **Conda Environment (MFA):** The phonetic alignment module does not run in the standard Python environment. A separate **Conda** environment named `mfa` must be created. The Montreal Forced Aligner binaries must be installed within this isolated environment to prevent dependency conflicts with the main application.
*   **System Libraries:**
    *   **FFmpeg:** Must be installed at the system level and accessible via the system PATH.
    *   **Libraqm / Fribidi / Harfbuzz:** These text shaping libraries must be installed (via Homebrew) before installing Pillow. This enables the `layout_engine` support required for Thai rendering.
    *   **Thai Fonts:** The pipeline expects specific `.ttf` font files (e.g., *Prompt-Bold.ttf* or *Chonburi-Regular.ttf*) to be present in the `media_resources` directory. Missing fonts will cause the subtitle module to crash or revert to a fallback font that supports Latin characters only (rendering squares for Thai).

### Configuration Management
Sensitive credentials and configuration flags are managed via a `.env` file located in the project root.
*   **`GEMINI_API_KEY`**: The authentication token for the Google GenAI SDK.
*   **`GEMINI_MODEL_ID`**: (Optional) Configurable pointer to specific model versions (e.g., `gemini-2.5-pro`).

## 5.2 Execution and Debugging

### Standard Execution Procedure
The pipeline is triggered via the entry point script: `src/v2_thai/main.py`. Upon execution, the Orchestrator initiates the synchronous workflow. The console outputs a structured log stream indicating the current stage:
1.  **Stage 1 Log:** `1. 🇹🇭 Asking Gemini to cook up a...` – Indicates API connection and script generation.
2.  **Stage 2 Log:** `2. 🔊 Starting Audio Generation...` – Indicates TTS synthesis status.
3.  **Stage 3 Log:** `3. 📝 Generating Transcript...` – Indicates the hand-off to the MFA subprocess. This stage typically incurs the highest latency (15–45 seconds) as the alignment engine initializes.
4.  **Stage 4 Log:** `4. 🎬 Generating subtitle clips...` – Indicates the rasterization of text assets.
5.  **Stage 5 Log:** `5. 🏗️ Assembling Final Video...` – Indicates the FFmpeg render process.

### Debugging and Artifact Inspection
The system is designed with observability in mind. It does not fail silently; instead, it dumps intermediate artifacts into the `___0w0__temp_automation_workspace` directory. Developers should inspect these files to isolate failures:
*   **Alignment Issues:** If subtitles are desynchronized, inspect `mfa_aligned_transcript_data.json`. If timestamps appear as `0.0` or `<unk>`, the issue lies within the text tokenization or the MFA dictionary injection logic.
*   **Rendering Issues:** If the final video fails to render, check `debug_test_subtitle_clip.mp4` (generated by `generate_subtitle_clip.py` when run independently). This isolated clip allows verification of font rendering without waiting for the full video assembly process.
*   **Audio Issues:** If the narration sounds rushed or unnatural, inspect `raw_original_audio.mp3` before the speed-up filter is applied. This distinguishes between TTS generation errors and FFmpeg post-processing artifacts.

# 6. Future Development Roadmap

This section defines the strategic direction for the codebase, transitioning from a "High-Fidelity Prototype" to a fully autonomous production engine.

## 6.1 Optimization Targets

### Performance Refactoring
The current architecture relies on "mini-pipelines"—self-contained modules that often re-import libraries or re-initialize logic (e.g., repeatedly loading the MFA dictionary). Future work involves refactoring these into persistent Class objects to maintain state across execution cycles. Additionally, the dependency on a robust Conda environment for MFA is resource-heavy. Investigation into lighter, Python-native alignment libraries (such as Wav2Vec2 fine-tuned for Thai) could reduce the installation footprint and runtime latency.

### Error Handling Resilience
The current implementation adheres to a "Fail-Fast" philosophy. If the API returns a 500 error or MFA fails to align, the pipeline terminates. A production-grade update will implement **Exponential Backoff** strategies for API calls and **Graceful Degradation** for alignment failures (e.g., falling back to linear time interpolation if phonetic alignment fails).

## 6.2 Feature Expansion

### Audio Ducking and Sound Design
To increase viewer retention, the pipeline requires a Background Music (BGM) layer. Future modules will implement **Audio Ducking**: a dynamic volume automation process where the BGM volume automatically decreases (ducks) when the narrator speaks and swells during pauses. This requires advanced analysis of the audio waveform amplitude.

### Undetectable Browser Automation
The ultimate goal is complete autonomy. The current "Air Gap" strategy (manual upload via phone) limits throughput. The roadmap includes the development of a Selenium/Playwright module utilizing **Profile Persistence**. By hijacking an existing browser session (cookies, local storage, history), the automation can upload content via the web interface without triggering "Bot" detection flags, effectively bypassing the need for physical hardware interaction.

### Multi-Persona Library
Currently, the system is hard-coded to a single "Gossip" persona. Future iterations will introduce a configuration file defining multiple personas (e.g., "The Financial Guru," "The Horror Narrator"). The Script Generation module will dynamically load these prompt templates, and the Audio module will map them to distinct TTS voice profiles, allowing a single pipeline to service multiple niche channels.

# Summary

The **Thai Short-Form Content Automation Pipeline** represents a sophisticated intersection of Generative AI, Signal Processing, and Software Engineering. It successfully addresses specific, high-barrier technical challenges—namely, the accurate rendering of Thai Complex Text Layout and the phonetic alignment of scriptio continua languages—that often render generic automation tools unusable for the Thai market.

Beyond its functional capability to generate "Faceless" content, this project serves as a comprehensive portfolio demonstration. It exhibits mastery over **API Orchestration** (Gemini), **System Architecture** (Modular Pipelines), **Multimedia Engineering** (FFmpeg/Pillow), and **Algorithmic Stealth** (Metadata Spoofing). It stands not merely as a content generator, but as a proof-of-concept for how localized, culturally nuanced media production can be automated at scale.


