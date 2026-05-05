import os
import sys
import shutil
import time
import wave
import gc
import re
import subprocess
import warnings
from datetime import datetime

# Suppress harmless library warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    from mlx_audio.tts.utils import load_model
    from mlx_audio.tts.generate import generate_audio
except ImportError:
    print("Error: 'mlx_audio' library not found.")
    print("Run: source .venv/bin/activate")
    sys.exit(1)

# Configuration
BASE_OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")
MODELS_DIR = os.path.join(os.getcwd(), "models")
VOICES_DIR = os.path.join(os.getcwd(), "voices")
TEMP_DIR = os.path.join(os.getcwd(), "temp")

# Settings
AUTO_PLAY = True
SAMPLE_RATE = 24000
FILENAME_MAX_LEN = 20

# Model Definitions
MODELS = {
    # Pro (1.7B)
    "1": {"name": "Custom Voice", "folder": "Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit", "mode": "custom", "output_subfolder": "CustomVoice"},
    "2": {"name": "Voice Design", "folder": "Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit", "mode": "design", "output_subfolder": "VoiceDesign"},
    "3": {"name": "Voice Cloning", "folder": "Qwen3-TTS-12Hz-1.7B-Base-8bit", "mode": "clone_manager", "output_subfolder": "Clones"},
    # Lite (0.6B)
    "4": {"name": "Custom Voice", "folder": "Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit", "mode": "custom", "output_subfolder": "CustomVoice"},
    "5": {"name": "Voice Design", "folder": "Qwen3-TTS-12Hz-0.6B-VoiceDesign-8bit", "mode": "design", "output_subfolder": "VoiceDesign"},
    "6": {"name": "Voice Cloning", "folder": "Qwen3-TTS-12Hz-0.6B-Base-8bit", "mode": "clone_manager", "output_subfolder": "Clones"},
}

# HuggingFace repo mapping (folder name -> repo ID)
# All models are from mlx-community, except 0.6B VoiceDesign which doesn't exist yet
HF_REPOS = {
    "Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit": "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit",
    "Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit": "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit",
    "Qwen3-TTS-12Hz-1.7B-Base-8bit": "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit",
    "Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit": "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit",
    "Qwen3-TTS-12Hz-0.6B-Base-8bit": "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit",
}

SPEAKER_MAP = {
    "English": ["Ryan", "Aiden", "Ethan", "Chelsie", "Serena", "Vivian"],
    "Chinese": ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric"],
    "Japanese": ["Ono_Anna"],
    "Korean": ["Sohee"]
}

EMOTION_EXAMPLES = [
    "Sad and crying, speaking slowly",
    "Excited and happy, speaking very fast",
    "Angry and shouting",
    "Whispering quietly"
]


def flush_input():
    try:
        import termios
        termios.tcflush(sys.stdin, termios.TCIOFLUSH)
    except (ImportError, OSError):
        pass


def clean_memory():
    gc.collect()


def make_temp_dir():
    return os.path.join(TEMP_DIR, f"temp_{int(time.time())}")


def download_model(folder_name):
    repo_id = HF_REPOS.get(folder_name)
    if not repo_id:
        print(f"Error: No download available for '{folder_name}'.")
        return False

    local_dir = os.path.join(MODELS_DIR, folder_name)
    print(f"\nModel '{folder_name}' not found locally.")
    print(f"Downloading from {repo_id} (this may take a while)...")

    try:
        subprocess.run(
            ["hf", "download", "--local-dir", local_dir, repo_id],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        print("Download complete.")
        return True
    except FileNotFoundError:
        print("Error: 'hf' CLI not found. Install it with: pip install huggingface_hub[cli]")
        return False
    except subprocess.CalledProcessError:
        print("Download failed. Check your internet connection and try again.")
        return False


def get_smart_path(folder_name):
    full_path = os.path.join(MODELS_DIR, folder_name)
    if not os.path.exists(full_path):
        if not download_model(folder_name):
            return None

    snapshots_dir = os.path.join(full_path, "snapshots")
    if os.path.exists(snapshots_dir):
        subfolders = [f for f in os.listdir(snapshots_dir) if not f.startswith('.')]
        if subfolders:
            return os.path.join(snapshots_dir, subfolders[0])

    return full_path


def save_audio_file(temp_folder, subfolder, text_snippet):
    save_path = os.path.join(BASE_OUTPUT_DIR, subfolder)
    os.makedirs(save_path, exist_ok=True)

    timestamp = datetime.now().strftime("%H-%M-%S")
    clean_text = re.sub(r'[^\w\s-]', '', text_snippet)[:FILENAME_MAX_LEN].strip().replace(' ', '_') or "audio"
    filename = f"{timestamp}_{clean_text}.wav"
    final_path = os.path.join(save_path, filename)

    source_file = os.path.join(temp_folder, "audio_000.wav")

    if os.path.exists(source_file):
        shutil.move(source_file, final_path)
        print(f"Saved: outputs/{subfolder}/{filename}")

        if AUTO_PLAY:
            print("Playing...")
            try:
                subprocess.run(["afplay", final_path], check=False, 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except FileNotFoundError:
                pass

    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder, ignore_errors=True)


def clean_path(user_input):
    path = user_input.strip()
    if len(path) > 1 and path[0] in ["'", '"'] and path[-1] == path[0]:
        path = path[1:-1]
    return path.replace("\\ ", " ")


def get_safe_input(prompt="\nEnter text (or drag .txt file): "):
    try:
        raw_input = input(prompt).strip()
        if raw_input.lower() in ['exit', 'quit', 'q']:
            return None

        clean_p = clean_path(raw_input)
        if os.path.exists(clean_p) and clean_p.endswith(".txt"):
            print(f"Reading from: {os.path.basename(clean_p)}")
            try:
                with open(clean_p, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except IOError as e:
                print(f"Error reading file: {e}")
                return None

        return raw_input
    except KeyboardInterrupt:
        flush_input()
        return None


def convert_audio_if_needed(input_path):
    if not os.path.exists(input_path):
        return None

    filename = os.path.basename(input_path)
    name, ext = os.path.splitext(filename)

    if ext.lower() == ".wav":
        try:
            with wave.open(input_path, 'rb') as f:
                if f.getnchannels() > 0:
                    return input_path
        except wave.Error:
            pass

    os.makedirs(TEMP_DIR, exist_ok=True)
    temp_wav = os.path.join(TEMP_DIR, f"temp_convert_{int(time.time())}.wav")
    print(f"Converting '{ext}' to WAV...")

    cmd = ["ffmpeg", "-y", "-v", "error", "-i", input_path, 
           "-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", temp_wav]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return temp_wav
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Could not convert audio. Is ffmpeg installed?")
        return None


def get_saved_voices():
    if not os.path.exists(VOICES_DIR):
        return []
    voices = [f.replace(".wav", "") for f in os.listdir(VOICES_DIR) if f.endswith(".wav")]
    return sorted(voices)


def enroll_new_voice():
    print("\n--- Enroll New Voice ---")
    flush_input()

    name = input("1. Voice name (e.g. Boss, Mom): ").strip()
    if not name:
        return

    safe_name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')

    ref_input = input("2. Drag & Drop Reference File: ").strip()
    raw_path = clean_path(ref_input)

    if len(raw_path) > 300 or "\n" in raw_path:
        print("Error: Input too long.")
        flush_input()
        return

    clean_wav_path = convert_audio_if_needed(raw_path)
    if not clean_wav_path:
        return

    print("3. Transcript (important for quality):")
    ref_text = input("   Type EXACTLY what the audio says: ").strip()

    if not os.path.exists(VOICES_DIR):
        os.makedirs(VOICES_DIR)

    target_wav = os.path.join(VOICES_DIR, f"{safe_name}.wav")
    target_txt = os.path.join(VOICES_DIR, f"{safe_name}.txt")

    shutil.copy(clean_wav_path, target_wav)
    with open(target_txt, "w", encoding='utf-8') as f:
        f.write(ref_text)

    if clean_wav_path != raw_path and os.path.exists(clean_wav_path):
        os.remove(clean_wav_path)

    print(f"Voice saved as '{safe_name}'")


def run_custom_session(model_key):
    info = MODELS[model_key]
    model_path = get_smart_path(info["folder"])
    if not model_path:
        print("Error: Model not found.")
        return

    print(f"\nLoading {info['name']}...")
    try:
        model = load_model(model_path)
    except Exception as e:
        print(f"Load failed: {e}")
        return

    print(f"\n--- {info['name']} ---")
    speaker = "Vivian"
    all_speakers = [n for names in SPEAKER_MAP.values() for n in names]
    print("Available Speakers: " + ", ".join(all_speakers))

    user_choice = input("\nSelect Speaker (Name): ").strip()
    for lang, names in SPEAKER_MAP.items():
        if user_choice in names:
            speaker = user_choice
            break
    print(f"Using: {speaker}")

    print("\nEmotion Examples:")
    for ex in EMOTION_EXAMPLES:
        print(f"  - {ex}")
    base_instruct = input("Emotion Instruction: ").strip() or "Normal tone"

    print("\nSpeed:")
    print("  1. Normal (1.0x)")
    print("  2. Fast (1.3x)")
    print("  3. Slow (0.8x)")
    sp = input("Choice (1-3): ").strip()
    speed = 1.0
    if sp == "2":
        speed = 1.3
    elif sp == "3":
        speed = 0.8

    while True:
        text = get_safe_input()
        if text is None:
            break
        print("Generating...")
        temp_dir = make_temp_dir()
        try:
            generate_audio(model=model, text=text, voice=speaker, 
                         instruct=base_instruct, speed=speed, output_path=temp_dir)
            save_audio_file(temp_dir, info["output_subfolder"], text)
        except Exception as e:
            print(f"Error: {e}")
    clean_memory()


def run_design_session(model_key):
    info = MODELS[model_key]
    model_path = get_smart_path(info["folder"])
    if not model_path:
        print("Error: Model not found.")
        return

    print(f"\nLoading {info['name']}...")
    try:
        model = load_model(model_path)
    except Exception as e:
        print(f"Load failed: {e}")
        return

    print(f"\n--- {info['name']} ---")
    instruct = input("Describe the voice: ").strip()
    if not instruct:
        return

    while True:
        text = get_safe_input()
        if text is None:
            break
        print("Generating...")
        temp_dir = make_temp_dir()
        try:
            generate_audio(model=model, text=text, instruct=instruct, output_path=temp_dir)
            save_audio_file(temp_dir, info["output_subfolder"], text)
        except Exception as e:
            print(f"Error: {e}")
    clean_memory()


def run_clone_manager(model_key):
    print("\n--- Voice Cloning Manager ---")
    print("  1. Pick from Saved Voices")
    print("  2. Enroll New Voice")
    print("  3. Quick Clone")
    print("  4. Back")

    sub_choice = input("\nChoice: ").strip()
    if sub_choice == "2":
        enroll_new_voice()
        return
    if sub_choice == "4":
        return

    info = MODELS[model_key]
    model_path = get_smart_path(info["folder"])
    if not model_path:
        print("Error: Model not found.")
        return

    print("\nLoading Base Model...")
    try:
        model = load_model(model_path)
    except Exception as e:
        print(f"Load failed: {e}")
        return

    ref_audio, ref_text = None, None

    if sub_choice == "1":
        saved = get_saved_voices()
        if not saved:
            print("No saved voices found.")
            return
        print("\nSaved Voices:")
        for i, v in enumerate(saved):
            print(f"  {i+1}. {v}")
        try:
            idx = int(input("\nPick Number: ")) - 1
            if idx < 0 or idx >= len(saved):
                print("Invalid selection.")
                return
            name = saved[idx]
            ref_audio = os.path.join(VOICES_DIR, f"{name}.wav")
            txt_path = os.path.join(VOICES_DIR, f"{name}.txt")
            if os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    ref_text = f.read().strip()
            print(f"Loaded: {name}")
        except (ValueError, IndexError):
            print("Invalid selection.")
            return

    elif sub_choice == "3":
        ref_input = input("\nDrag Reference Audio: ").strip()
        raw_path = clean_path(ref_input)
        ref_audio = convert_audio_if_needed(raw_path)
        if not ref_audio:
            return
        ref_text = input("   Transcript (Optional): ").strip() or "."

    else:
        return

    while True:
        text = get_safe_input(f"\nText for '{os.path.basename(str(ref_audio))}' (or 'exit'): ")
        if text is None:
            break
        print("Cloning...")
        temp_dir = make_temp_dir()
        try:
            generate_audio(model=model, text=text, ref_audio=ref_audio, 
                         ref_text=ref_text, output_path=temp_dir)
            save_audio_file(temp_dir, info["output_subfolder"], text)
        except Exception as e:
            print(f"Error: {e}")
    clean_memory()


def main_menu():
    print("\n" + "=" * 40)
    print(" Qwen3-TTS Manager")
    print("=" * 40)
    
    print("\n  Pro Models (1.7B - Best Quality)")
    print("  ---------------------------------")
    print("  1. Custom Voice")
    print("  2. Voice Design")
    print("  3. Voice Cloning")
    
    print("\n  Lite Models (0.6B - Faster)")
    print("  ---------------------------")
    print("  4. Custom Voice")
    print("  5. Voice Design")
    print("  6. Voice Cloning")
    
    print("\n  q. Exit")

    choice = input("\nSelect: ").strip().lower()

    if choice == "q":
        sys.exit()

    if choice not in MODELS:
        print("Invalid selection.")
        flush_input()
        return

    mode = MODELS[choice]["mode"]

    if mode == "custom":
        run_custom_session(choice)
    elif mode == "design":
        run_design_session(choice)
    elif mode == "clone_manager":
        run_clone_manager(choice)


if __name__ == "__main__":
    try:
        os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
        os.makedirs(TEMP_DIR, exist_ok=True)
        while True:
            main_menu()
    except KeyboardInterrupt:
        print("\nExiting...")
