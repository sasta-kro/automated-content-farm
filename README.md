# Automated Short-Form Content Generation Pipeline

**Status:** Production Ready (but can use some cleanup) | **Architecture:** Modular Orchestrator

This **Short-Form Content Automation Pipeline** is a specialized software solution designed to autonomously generate vertical video content tailored for the Thai social media ecosystem. This project functions as an **Algorithmic Media Pipeline**, transforming raw topic inputs into fully produced, publish-ready video assets without human intervention in the creative process.

The primary objective of this system is to serve as a high-fidelity technical demonstration of **Python-based Automation**, **API Orchestration**, and **System Architecture**. It illustrates the capability to integrate disparate technologies—Large Language Models (LLMs), Text-to-Speech (TTS) synthesis, phonetic alignment engines, and programmatic video editing—into a cohesive workflow.
## 📋 Overview
This project explores the intersection of **Zero-Shot Localization** and **Algorithmic Automation**. The objective was to engineer a system capable of producing native-level content for a target language (Thai) without the developer possessing linguistic competency in that language.

Unlike standard automation scripts, this pipeline implements a sophisticated **Defense-in-Depth** strategy against platform heuristic analysis (Shadowbanning), utilizing metadata engineering and stochastic signal processing to mimic organic user behavior.

## ⚙️ Core Engineering Challenges & Solutions

### 1. Zero-Shot Phonetic Alignment (Scriptio Continua)
**The Constraint:** Thai is a *scriptio continua* language (no whitespace delimiters). Standard string tokenization methods fail to map written text to audio timestamps, rendering standard subtitle logic useleess.
**The Solution:** Implemented a **Forced Alignment** pipeline using the **Montreal Forced Aligner (MFA)**. The system bypasses heuristic timing entirely, utilizing a Thai acoustic model to mathematically calculate phoneme-level boundaries, achieving near 100% synchronization accuracy without semantic understanding of the language.

### 2. Complex Text Layout (CTL) Rendering
**The Constraint:** Legacy Python video libraries utilize rendering backends (ImageMagick) that lack support for Thai Vertical Stacking (3 layers). This results in "overlapping diacritics," where tone marks render on top each other (z-axis) and end up covering each other. 
**The Solution:** Engineered a custom rasterization module utilizing **Pillow (PIL)** compiled with **Libraqm** and **HarfBuzz** bindings. This enforces OpenType shaping logic at the pixel level, ensuring typography meets native legibility standards before being composited into the video stream.

### 3. Temporal Signal Processing (The "Brainrot" Factor)
**The Constraint:** Maximizing viewer retention requires hyper-accelerated pacing (1.3x speed) without introducing pitch artifacts ("Chipmunk effect").
**The Solution:** Implemented a DSP post-processing stage using **FFmpeg filters (`atempo`)**. This applies Time-Scale Modification (TSM) to compress the audio duration while preserving the original formant frequencies, seamlessly synchronizing the video timeline to this new tempo.

### 4. Heuristic Evasion & Metadata Engineering
**The Constraint:** Social media algorithms utilize file hashing and metadata analysis to identify and suppress programmatically generated content (Spam/Bot detection).
**The Solution:** Developed a **Stealth Output Layer** that sanitizes all automated signatures (FFmpeg/Lavf tags). The system injects fabricated, organic metadata—including ISO 6709 geolocation tags (simulating specific Bangkok coordinates) and mobile NLE signatures (spoofing CapCut/InShot encoding)—to effectively classify the output as User Generated Content (UGC).

## 🏗 System Architecture

The codebase adheres to a strict **Orchestrator Pattern**, decoupling logic into isolated micro-services managed by a central synchronous controller (`main.py`).

*   **Generative Service:** Handles Context Injection and Schema Validation via Google GenAI.
*   **Synthesis Service:** A Hybrid TTS engine managing fallback logic between Gemini Audio (main) and Edge-tts (fallback).
*   **Alignment Service:** Manages the Conda environment context switching required to execute the MFA subprocess.
*   **Composition Service:** Handles stochastic asset selection (weighted randoms), visual obfuscation (mirroring/cropping), and final NLE-style rendering.

## 🛠 Technology Stack

*   **Runtime:** Python 3.13 (Apple Silicon Optimization via `mlx`)
*   **Generative Model:** Gemini 2.5 Pro (JSON Mode)
*   **Signal Processing:** Montreal Forced Aligner (MFA), PyThaiNLP, FFmpeg
*   **Rendering Engine:** MoviePy, Pillow (Libraqm/HarfBuzz binding)

---