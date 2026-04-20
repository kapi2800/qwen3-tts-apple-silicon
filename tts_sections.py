"""
tts_sections.py — TTS per section, no autoplay, scriptable

Splits input text on '---' separators and generates one .wav per section.
Whisper (STT) is loaded once upfront when no transcript file exists for the
reference voice, avoiding repeated model load/unload between sections.

Usage:
    python tts_sections.py <input.txt> <output_dir>

Example:
    python tts_sections.py docs/voiceover-white-belt.txt outputs/voiceover-white-belt
    python tts_sections.py docs/voiceover-black-belt.txt outputs/voiceover-black-belt

Output files: <output_dir>/01.wav, 02.wav, ...
Skips sections that are already present (safe to re-run).
"""

import sys
import os

if sys.version_info < (3, 13):
    sys.exit(
        f"Python 3.13+ required (got {sys.version_info.major}.{sys.version_info.minor}).\n"
        "Run: python3.13 -m venv .venv && source .venv/bin/activate"
    )

import gc
import shutil
import time
import warnings

os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    from mlx_audio.tts.utils import load_model
    from mlx_audio.tts.generate import generate_audio
except ImportError:
    sys.exit("mlx_audio not found. Run: source .venv/bin/activate")

# --- Config ---
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
VOICES_DIR   = os.path.join(SCRIPT_DIR, "voices")

VOICE_NAME   = "Juval-Voice-1"
MODEL_REPO   = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit"
LANG_CODE    = "de"
SECTION_SEP  = "---"
STT_MODEL_ID = "mlx-community/whisper-large-v3-mlx"


def load_voice(name: str) -> tuple[str, str | None]:
    """Load voice wav + optional transcript. Returns (wav_path, ref_text_or_None)."""
    wav = os.path.join(VOICES_DIR, f"{name}.wav")
    txt = os.path.join(VOICES_DIR, f"{name}.txt")
    if not os.path.exists(wav):
        sys.exit(f"Voice not found: {wav}")
    ref_text = None
    if os.path.exists(txt):
        with open(txt, encoding="utf-8") as f:
            ref_text = f.read().strip() or None
        print(f"Transcript : loaded from {name}.txt")
    else:
        print(f"Transcript : not found — will transcribe via Whisper STT")
    return wav, ref_text


def transcribe_reference(ref_audio: str) -> str:
    """Transcribe the reference audio once using Whisper. Returns transcript text."""
    print(f"STT        : loading Whisper ({STT_MODEL_ID})...")
    from mlx_audio.stt import load as load_stt
    stt = load_stt(STT_MODEL_ID)
    print(f"STT        : transcribing {os.path.basename(ref_audio)}...")
    ref_text = stt.generate(ref_audio).text.strip()
    print(f"STT        : \"{ref_text}\"")
    # Free Whisper from memory — TTS model needs the RAM
    del stt
    gc.collect()
    print(f"STT        : unloaded\n")
    return ref_text


def split_sections(path: str) -> list[str]:
    with open(os.path.expanduser(path), encoding="utf-8") as f:
        raw = f.read()
    parts = [p.strip() for p in raw.split(SECTION_SEP)]
    return [p for p in parts if p]  # drop empty


def generate_section(model, text: str, ref_audio: str, ref_text: str, out_wav: str):
    """Generate audio for one section. ref_text must be resolved before calling."""
    temp_dir = f"_tmp_{int(time.time() * 1000)}"
    try:
        generate_audio(
            model=model,
            text=text,
            ref_audio=ref_audio,
            ref_text=ref_text,   # always a string — Whisper already ran upfront
            lang_code=LANG_CODE,
            output_path=temp_dir,
        )
        src = os.path.join(temp_dir, "audio_000.wav")
        if not os.path.exists(src):
            wavs = [f for f in os.listdir(temp_dir) if f.endswith(".wav")]
            if not wavs:
                raise FileNotFoundError(f"No wav in {temp_dir}")
            src = os.path.join(temp_dir, wavs[0])
        shutil.move(src, out_wav)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2]

    sections = split_sections(input_path)
    if not sections:
        sys.exit("No sections found in input file.")

    os.makedirs(output_dir, exist_ok=True)

    print(f"Input   : {input_path}")
    print(f"Output  : {output_dir}/")
    print(f"Voice   : {VOICE_NAME}")
    print(f"Sections: {len(sections)}")
    print()

    ref_audio, ref_text = load_voice(VOICE_NAME)

    # If no transcript file exists, run Whisper once now — before loading the
    # TTS model — so both don't compete for RAM at the same time.
    if ref_text is None:
        ref_text = transcribe_reference(ref_audio)
        # Persist transcript so future runs skip this step entirely
        txt_path = os.path.join(VOICES_DIR, f"{VOICE_NAME}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(ref_text)
        print(f"STT        : transcript saved to {txt_path}\n")

    print(f"Loading TTS model ({MODEL_REPO})...")
    model = load_model(MODEL_REPO)
    print(f"TTS model ready.\n")

    for i, text in enumerate(sections, start=1):
        out_wav = os.path.join(output_dir, f"{i:02d}.wav")
        preview = text[:60].replace("\n", " ")

        if os.path.exists(out_wav):
            print(f"[{i:02d}/{len(sections)}] skip (exists): {out_wav}")
            continue

        print(f"[{i:02d}/{len(sections)}] {preview!r}...")
        try:
            generate_section(model, text, ref_audio, ref_text, out_wav)
            print(f"           -> {out_wav}")
        except Exception as e:
            print(f"           ERROR: {e}")

    print(f"\nDone. {len(sections)} sections -> {output_dir}/")


if __name__ == "__main__":
    main()
