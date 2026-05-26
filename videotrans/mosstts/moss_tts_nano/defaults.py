from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PROMPT_AUDIO_DIR = REPO_ROOT / "assets" / "audio"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "generated_audio"
DEFAULT_CHECKPOINT_PATH = "OpenMOSS-Team/MOSS-TTS-Nano"
DEFAULT_AUDIO_TOKENIZER_PATH = "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano"
