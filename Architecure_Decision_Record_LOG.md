# Architecture Decision Record (ADR) Log 

### 001. Modular Orchestrator Architecture
- **Status:** Accepted
- **Date:** 2023-12-07
- **Context:** The automation pipeline consists of five distinct, resource-intensive stages: Script Generation (LLM), Audio Synthesis (TTS), Phonetic Alignment (MFA), Asset Generation (Image Processing), and Video Composition (FFmpeg). Managing state and error handling across a single monolithic script proved unwieldy, making debugging specific failures (e.g., alignment crashes) difficult without re-running costly API calls.
- **Decision:** The system utilizes a **Linear Synchronous Pipeline** architecture orchestrated by a central entry point (`main.py`). Logic is encapsulated into independent "mini-pipelines" (functional modules) located in `src/short_form_content_pipeline/`. Data is passed between stages as stateless dictionaries or absolute file paths.
- **Consequences:**
    - **Positive:** Isolation of concerns allows for independent testing of modules (e.g., running `mfa_transcript_alignment_mini_pipeline.py` standalone).
    - **Positive:** Fatal errors in later stages (e.g., video rendering) do not require re-generation of earlier assets (script/audio).
    - **Negative:** Requires strict management of file system artifacts and temporary directories to ensure modules find their dependencies.
- **Rejected Alternatives:**
    - **Monolithic Procedural Script:** Rejected due to lack of maintainability and inability to isolate crashes.
    - **Class-Based Managers (OOP):** Rejected as unnecessary overhead. The pipeline is linear and stateless; instantiating persistent objects for "ScriptManager" or "AudioManager" added complexity without benefit.

### 002. Structured Output Enforcement via Pydantic (Scripting)
- **Status:** Accepted
- **Date:** 2023-12-07
- **Context:** Large Language Models (LLMs) used for script generation often return conversational filler ("Here is your script:"), Markdown formatting, or inconsistent JSON structures. Relying on Regex or string slicing to extract the Title, Script, and Gender proved fragile and prone to runtime parsing errors.
- **Decision:** Utilization of the `google-genai` SDK's native support for **Structured Output** via `pydantic`. A strict schema class (`ScriptOutputData`) is passed to the API configuration, enforcing the model to decode purely into a validated JSON object.
- **Consequences:**
    - **Positive:** Eliminates parsing errors caused by hallucinated formatting.
    - **Positive:** Guarantees type safety (e.g., `gender` is always a string, `script_text` is never null).
    - **Negative:** Dependency on specific model versions (Gemini Pro/Flash) that support structured decoding.
- **Rejected Alternatives:**
    - **Regex Parsing:** Rejected because LLM output patterns vary (sometimes using `**bold**`, sometimes code blocks), making Regex maintenance a constant burden.
    - **JSON Mode (Raw):** Rejected because while it enforces JSON syntax, it does not guarantee the *schema* (keys and value types) required by downstream modules.

### 003. Hybrid TTS Architecture & Signal Processing
- **Status:** Accepted
- **Date:** 2023-12-07
- **Context:** The content requires high expressiveness to mimic "Netizen" tones (Gossip/Drama) but maintains a strict requirement for Thai pronunciation accuracy. Additionally, modern short-form content demands rapid pacing (~1.3x speed) without pitch distortion ("Chipmunk effect").
- **Decision:** Implementation of a **Hybrid TTS Engine** with **FFmpeg Post-Processing**.
    1.  **Primary:** Google Gemini Audio (Aoede/Charon) for superior emotional prosody.
    2.  **Fallback:** EdgeTTS (`th-TH-Premwadee`) for offline reliability and pronunciation accuracy.
    3.  **Processing:** Raw audio is generated at 1.0x speed, then processed via FFmpeg's `atempo` filter to increase speed while mathematically preserving pitch.
- **Consequences:**
    - **Positive:** Achieves the "Brainrot" pacing required for retention without sacrificing audio fidelity.
    - **Positive:** Redundancy ensures the pipeline continues if one API provider fails.
    - **Negative:** Adds a dependency on `ffmpeg-python` and increased processing time for the `atempo` filter.
- **Rejected Alternatives:**
    - **Simple Sample Rate Adjustment:** Rejected as it couples speed with pitch, resulting in unusable high-pitched audio.
    - **PyTTSx3/OS Native TTS:** Rejected due to robotic, monotonic delivery unsuitable for viral entertainment content.

### 004. Montreal Forced Aligner (MFA) for Thai Synchronization
- **Status:** Accepted
- **Date:** 2023-12-07
- **Context:** Thai is a *scriptio continua* language (no spaces between words). Standard subtitles split by space are impossible. To achieve "Dynamic Captions" (word-by-word highlighting), the system requires precise start/end timestamps for every phoneme.
- **Decision:** Integration of the **Montreal Forced Aligner (MFA)** via a dedicated Conda environment. The system creates a `.lab` transcript and `.wav` audio pair, executes MFA via subprocess, and parses the resulting `.TextGrid` file.
- **Consequences:**
    - **Positive:** Provides millisecond-accurate timestamps for specific Thai words, enabling professional-grade synchronization.
    - **Negative:** Significant infrastructure overhead (requires Conda, acoustic models, dictionaries) and high latency (15-45s per run).
- **Rejected Alternatives:**
    - **OpenAI Whisper (Timestamped):** Rejected for this use case because Whisper often hallucinates timestamps on fast speech or merges multiple short words into one segment.
    - **Heuristic Splitting (gTTS/pydub):** Rejected as it simply estimates time based on character count, which fails completely for Thai due to variable vowel durations.

### 005. Custom Dictionary Trie for Slang Tokenization
- **Status:** Accepted
- **Date:** 2023-12-07
- **Context:** The generated scripts heavily utilize internet slang (e.g., "แกรร", "จึ้ง", "ป้ายยา"). Standard Thai tokenizers (PyThaiNLP `newmm`) often split these non-standard words into nonsense syllables (e.g., "แกรร" -> "แก" + "ร" + "ร"). This mismatch causes MFA to crash or produce `<unk>` (unknown) tokens, breaking subtitle synchronization.
- **Decision:** Injection of a **Custom Dictionary Trie** into the PyThaiNLP tokenizer prior to MFA processing. A curated list of slang terms (`MFA_THAI_SLANG_DICTIONARY` in `_CONSTANTS.py`) is forced as high-priority tokens.
- **Consequences:**
    - **Positive:** Ensures slang terms remain as single, indivisible tokens, allowing MFA to align them correctly against the audio waveform.
    - **Positive:** Drastically reduces `<unk>` token occurrences.
    - **Negative:** Requires manual maintenance of the slang dictionary as new internet terms emerge.
- **Rejected Alternatives:**
    - **Dictionary Expansion via AI:** Rejected for now due to unpredictability; manual curation ensures 100% accuracy for known high-frequency slang.
    - **ignoring `<unk>` tokens:** Rejected as it results in missing subtitles for the most important (emotional/slang) words in the video.


### 006. Pillow (PIL) + Libraqm for Subtitle Rendering
- **Status:** Accepted
- **Date:** 2023-12-07
- **Context:** Standard video libraries like MoviePy rely on ImageMagick for text rendering. ImageMagick often fails to render Thai Complex Text Layout (CTL) correctly, specifically "Vertical Stacking." Vowels and tone marks (e.g.,  ้,  ิ) frequently "float" in the wrong position, overlap with consonants, or render as tofu boxes.
- **Decision:** Bypassing MoviePy's internal text generator in favor of direct rasterization using the **Pillow (PIL)** library compiled with `libraqm` bindings. Text is drawn onto a transparent RGBA canvas using the HarfBuzz shaping engine and then converted to a MoviePy `ImageClip`.
- **Consequences:**
    - **Positive:** Ensures typographical correctness for Thai script, eliminating floating vowels and misplaced tone marks.
    - **Positive:** Allows for granular control over stroke width and color that mimics TikTok's native style.
    - **Negative:** Slower rendering performance compared to native FFmpeg text filters.
    - **Negative:** Adds a hard dependency on system-level libraries (`fribidi`, `harfbuzz`) which complicates deployment on non-macOS/Linux systems.
- **Rejected Alternatives:**
    - **MoviePy `TextClip` (ImageMagick):** Rejected due to persistent rendering artifacts with Thai diacritics.
    - **FFmpeg `drawtext` Filter:** Rejected due to complexity in handling dynamic word-level styling and positioning updates via CLI arguments.

### 007. Singleton Configuration Pattern (Pydantic + YAML)
- **Status:** Accepted
- **Date:** 2023-12-07
- **Context:** The system required managing two distinct types of configuration: static infrastructure secrets (API Keys, Directories) and dynamic content strategies (Topic, Tone, Voice, Speed). Hardcoding these or using a flat JSON file led to "God Objects" and made A/B testing different content styles difficult.
- **Decision:** Implementation of a **Singleton Configuration Object** utilizing `pydantic-settings`.
    1.  **Infrastructure:** Secrets are loaded from `.env` via Pydantic.
    2.  **Strategy:** Content "recipes" are stored in YAML profiles (`thai_funny_story.yaml`) and loaded into the Singleton via a `load_profile()` method.
- **Consequences:**
    - **Positive:** **Separation of Concerns:** Content strategy is decoupled from code logic.
    - **Positive:** **Type Safety:** Pydantic validates data types at load time (e.g., ensuring `speed_factor` is a float), preventing runtime crashes deep in the pipeline.
    - **Negative:** Slightly higher complexity during initialization compared to a simple dictionary.
- **Rejected Alternatives:**
    - **`config.json` (Flat File):** Rejected because it mixed secrets with content settings and lacked validation.
    - **Hardcoded Constants:** Rejected as it required code changes to modify video parameters.

### 008. Visual Randomization & Anti-Fingerprinting
- **Status:** Accepted
- **Date:** 2023-12-07
- **Context:** Social media platforms utilize hashing algorithms (e.g., Perceptual Hashing) to detect and suppress "Reused Content" or spam. Using the same background gameplay footage repeatedly without modification triggers these filters, leading to shadowbans.
- **Decision:** Implementation of a multi-layer randomization strategy within the video composition module:
    1.  **Weighted Selection:** Preferentially selecting longer source videos to maximize available footage.
    2.  **Stochastic Slicing:** Extracting a random time segment based on audio duration.
    3.  **Pixel Manipulation:** Randomly applying a horizontal **Mirror Flip** and dynamic cropping to the 9:16 aspect ratio.
- **Consequences:**
    - **Positive:** Fundamentally alters the pixel hash of the output video, significantly reducing the probability of automated detection.
    - **Positive:** Maximizes the utility of a limited library of background assets.
    - **Negative:** Random slicing may occasionally result in "boring" gameplay segments (e.g., a player standing still) being selected.
- **Rejected Alternatives:**
    - **Color Grading/Filters:** Rejected as excessive filtering degrades visual quality and is easily detected by modern algorithms.
    - **Static Backgrounds:** Rejected due to low viewer retention rates.

### 009. Mathematical Timestamp Compression for Pacing
- **Status:** Accepted
- **Date:** 2023-12-07
- **Context:** The pipeline generates audio at 1.0x speed for clarity, aligns it via MFA, and *then* speeds it up (e.g., 1.3x) for the final video. This creates a synchronization mismatch: MFA timestamps correspond to the slow audio, not the fast audio.
- **Decision:** **Mathematical Timestamp Adjustment.** Instead of re-running alignment on sped-up audio (which degrades MFA accuracy), the system divides the original timestamps by the speed factor (`new_time = original_time / speed_factor`) during the subtitle generation phase.
- **Consequences:**
    - **Positive:** Maintains the high accuracy of alignment performed on clear, normal-speed speech.
    - **Positive:** Eliminates the computational cost of a second alignment pass.
    - **Negative:** Relies on the assumption that FFmpeg's `atempo` filter is mathematically perfect (linear); minor drift may occur over very long videos (>5 mins), though negligible for short-form.
- **Rejected Alternatives:**
    - **Aligning Sped-Up Audio:** Rejected because MFA struggles to recognize phonemes in accelerated, compressed speech, leading to increased error rates.

### 010. Post-Rendering Metadata Injection (Stream Copy)
- **Status:** Accepted
- **Date:** 2023-12-07
- **Context:** To bypass "Bot Detection" heuristics, the output file must carry metadata signatures consistent with the uploader's physical environment (e.g., location, device model). Injecting this metadata during the complex video rendering phase added unnecessary logic to the composite pipeline.
- **Decision:** Implementation of a **Post-Processing Injection Step**.
    1.  The video is rendered cleanly by MoviePy.
    2.  A dedicated `metadata_injector.py` module generates organic flags (Apple/Android device tags, ISO 6709 coordinates).
    3.  FFmpeg is invoked with `-c copy` to inject these tags into a new container *without* re-encoding the video stream.
- **Consequences:**
    - **Positive:** **Zero Quality Loss:** The video stream is copied bit-for-bit.
    - **Positive:** **Speed:** The operation is near-instantaneous.
    - **Positive:** Decouples "Stealth" logic from "Creative" logic.
- **Rejected Alternatives:**
    - **Injection during Rendering:** Rejected to keep the MoviePy composition function clean and focused solely on visual assembly.
    - **External Metadata Tools (ExifTool):** Rejected in favor of FFmpeg to minimize external dependencies, as FFmpeg is already required for the pipeline.