"""
tts_batch.py — Batch TTS mit Juval-Voice-1 (Voice Cloning)

Verwendung:
    source .venv/bin/activate
    python tts_batch.py <input_txt> [output_wav]

Beispiel:
    python tts_batch.py ~/Projects/tools/GenAI/CHATAI-579/docs/voiceover-white-belt.txt
    python tts_batch.py ~/Projects/tools/GenAI/CHATAI-579/docs/voiceover-white-belt.txt outputs/white-belt.wav
"""

import sys
import os

if sys.version_info < (3, 13):
    sys.exit(
        f"Error: Python 3.13+ required (got {sys.version_info.major}.{sys.version_info.minor}).\n"
        "Run: python3.13 -m venv .venv && source .venv/bin/activate"
    )

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
    sys.exit("Error: mlx_audio not found. Run: source .venv/bin/activate")


# --- Config ---
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
VOICES_DIR  = os.path.join(SCRIPT_DIR, "voices")
OUTPUTS_DIR = os.path.join(SCRIPT_DIR, "outputs", "Clones")

VOICE_NAME  = "Juval-Voice-1"
MODEL_REPO  = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit"
STT_MODEL   = "mlx-community/whisper-large-v3-mlx"
LANG_CODE   = "de"


def load_voice(name: str):
    wav = os.path.join(VOICES_DIR, f"{name}.wav")
    txt = os.path.join(VOICES_DIR, f"{name}.txt")
    if not os.path.exists(wav):
        sys.exit(f"Error: Voice file not found: {wav}")
    ref_text = None
    if os.path.exists(txt):
        with open(txt, encoding="utf-8") as f:
            ref_text = f.read().strip() or None
        print(f"Loaded reference transcript from {name}.txt")
    else:
        print(f"No transcript file for {name} — Whisper STT will transcribe the reference audio automatically.")
    return wav, ref_text


def read_input(path: str) -> str:
    expanded = os.path.expanduser(path)
    if not os.path.exists(expanded):
        sys.exit(f"Error: Input file not found: {expanded}")
    with open(expanded, encoding="utf-8") as f:
        return f.read().strip()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path  = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    # Determine output path
    if output_path:
        output_wav = os.path.expanduser(output_path)
        os.makedirs(os.path.dirname(os.path.abspath(output_wav)), exist_ok=True)
    else:
        os.makedirs(OUTPUTS_DIR, exist_ok=True)
        base = os.path.splitext(os.path.basename(input_path))[0]
        timestamp = time.strftime("%H-%M-%S")
        output_wav = os.path.join(OUTPUTS_DIR, f"{timestamp}_{base}.wav")

    print(f"\n=== Qwen3-TTS Batch — Voice Cloning ===")
    print(f"Voice   : {VOICE_NAME}")
    print(f"Language: {LANG_CODE}")
    print(f"Input   : {input_path}")
    print(f"Output  : {output_wav}")
    print()

    # Load text
    text = read_input(input_path)
    word_count = len(text.split())
    print(f"Text loaded: {word_count} words")

    # Load voice
    ref_audio, ref_text = load_voice(VOICE_NAME)

    # Load model
    print(f"\nLoading model ({MODEL_REPO})...")
    model = load_model(MODEL_REPO)
    print("Model loaded.\n")

    # Generate — use a temp dir, then move to output_wav
    temp_dir = f"temp_batch_{int(time.time())}"
    print("Generating audio... (this may take a few minutes)")
    try:
        generate_audio(
            model=model,
            text=text,
            ref_audio=ref_audio,
            ref_text=ref_text,          # None → auto-transcribed via STT_MODEL
            stt_model=STT_MODEL,        # mlx-community/whisper-large-v3-mlx
            lang_code=LANG_CODE,
            output_path=temp_dir,
        )
    except Exception as e:
        sys.exit(f"Generation failed: {e}")

    # Move result
    source = os.path.join(temp_dir, "audio_000.wav")
    if not os.path.exists(source):
        # try any wav in temp_dir
        wavs = [f for f in os.listdir(temp_dir) if f.endswith(".wav")]
        if wavs:
            source = os.path.join(temp_dir, wavs[0])
        else:
            sys.exit(f"Error: No audio output found in {temp_dir}")

    shutil.move(source, output_wav)
    shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"\nDone! Saved to: {output_wav}")
    print("Playing...")
    os.system(f'afplay "{output_wav}"')


if __name__ == "__main__":
    main()
