# Qwen3-TTS for Mac - Run AI Text-to-Speech Locally on Apple Silicon

Run **Qwen3-TTS** text-to-speech AI locally on your MacBook with Apple Silicon (M1, M2, M3, M4). No cloud, no API keys, completely offline.

**Keywords:** Qwen TTS Mac, Qwen3 TTS Apple Silicon, MLX text to speech, local TTS Mac, voice cloning Mac, AI voice generator MacBook

---

## Features

- **Voice Cloning** - Clone any voice from a 5-second audio sample
- **Voice Design** - Create new voices by describing them ("deep narrator", "excited child")
- **Custom Voices** - 9 built-in voices with emotion and speed control
- **Language Selection** - Choose output language (German, English, Chinese, Japanese, Korean, French, …) per session; auto-detected from speaker in Custom Voice mode
- **100% Local** - Runs entirely on your Mac, no internet required after model download
- **Optimized for M-Series** - Uses Apple's MLX framework for fast GPU inference

---

## Why MLX Models?

MLX models are specifically optimized for Apple Silicon. Compared to running standard PyTorch models:

| Metric | Standard Model | MLX Model |
|--------|----------------|-----------|
| **RAM Usage** | 10+ GB | 2-3 GB |
| **CPU Temperature** | 80-90°C | 40-50°C |

*Tested on M4 MacBook Air (fanless) with 1.7B models*

MLX runs natively on the Apple Neural Engine and GPU, meaning better performance with less heat and battery drain.

---

## Quick Start (5 Minutes)

### 1. Clone and set up

```bash
git clone https://github.com/JuvGut/qwen3-tts-apple-silicon.git
cd qwen3-tts-apple-silicon

python3.13 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
brew install ffmpeg
```

> **Note:** Python 3.13 is required. Check with `python3.13 --version`.  
> Install it via Homebrew if needed: `brew install python@3.13`

### 2. Run

Models are **downloaded automatically on first use** from HuggingFace and cached in `~/.cache/huggingface/hub/`. No manual download step is needed — just run the app and select a model.

If you want to pre-download a model before going offline (optional):

```bash
# Downloads into the HF cache — shared across all projects, no duplication
hf download mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit
```

Available models:

| Key | Model | Use Case | Cache size |
|-----|-------|----------|------------|
| 1 | Pro 1.7B — Custom Voice | Preset voices + emotion control | ~2.2 GB |
| 2 | Pro 1.7B — Voice Design | Create voices from text description | ~2.2 GB |
| 3 | Pro 1.7B — Voice Cloning | Clone from audio | ~2.2 GB |
| 4 | Lite 0.6B — Custom Voice | Preset voices + emotion control | ~0.6 GB |
| 5 | Lite 0.6B — Voice Design | Create voices from text description | ~0.6 GB |
| 6 | Lite 0.6B — Voice Cloning | Clone from audio | ~0.6 GB |

### 3. Run

```bash
source .venv/bin/activate
python main.py
```

---

## Usage

```
========================================
 Qwen3-TTS Manager
========================================

  Pro Models (1.7B - Best Quality)
  ---------------------------------
  1. Custom Voice
  2. Voice Design
  3. Voice Cloning

  Lite Models (0.6B - Faster)
  ---------------------------
  4. Custom Voice
  5. Voice Design
  6. Voice Cloning

  q. Exit

Select:
```

- **Custom Voice**: Pick from preset speakers, set emotion and speed. Language is auto-detected from the chosen speaker (e.g. Ryan → English, Ono_Anna → Japanese) and can be overridden.
- **Voice Design**: Describe a voice (e.g., "calm British narrator"). You choose the output language from a numbered menu.
- **Voice Cloning**: Provide a reference audio clip to clone. You choose the output language from a numbered menu.

**Supported languages:** English, German, Chinese, Japanese, Korean, French, Spanish, Italian, Portuguese, Russian.

---

## Tips

- Drag `.txt` files directly into the terminal for long text
- Voice cloning works best with clean 5-10 second audio clips
- Speed options: Normal (1.0x), Fast (1.3x), Slow (0.8x)
- Type `q` or `exit` anytime to go back
- For German text, select **German (de)** in the language menu — this controls pronunciation, not just the speaker accent

---

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.13+
- RAM: ~3 GB for Lite models, ~6 GB for Pro models
- [ffmpeg](https://formulae.brew.sh/formula/ffmpeg) (for voice cloning audio conversion)

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `mlx_audio not found` | Run `source .venv/bin/activate` first |
| Model download fails / hangs | Check your internet connection. On corporate networks see the SSL row below. |
| Audio won't play | Check macOS sound output settings |
| `SSL certificate verify failed` (corporate network / Zscaler) | `truststore` is installed automatically and injects the macOS native trust store. If downloads still fail, check that the Zscaler Root CA is trusted in **Keychain Access → System**. |
| `Python 3.13+ required` error | Install with `brew install python@3.13`, then recreate the venv: `python3.13 -m venv .venv` |

---

## Related Projects

- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) - Original Qwen3-TTS by Alibaba
- [MLX Audio](https://github.com/Blaizzy/mlx-audio) - MLX framework for audio models
- [MLX Community](https://huggingface.co/mlx-community) - Pre-converted MLX models

---

**If this project helped you, please give it a ⭐ star!**
