import os
import shutil
import wave

import pytest

from videotrans import tts
from videotrans.configure import config
from videotrans.configure.config import app_cfg, params
from videotrans.tts import _audiocpp, _base
from videotrans.util.help_role import get_audiocpp_rolelist

# one of the reference voices in f5-tts/, which the voice lists of Audio.cpp offer
ROLE = "en_female_1.wav"
# the model saved by the last Start with Audio.cpp, in the main window or a dubbing window
SAVED = "dots_tts"


@pytest.fixture
def audiocpp(monkeypatch, tmp_path):
    """Stand-ins for what audio.cpp needs from outside: nothing is downloaded or
    played, and the audio.cpp cli writes a short wav and records its command"""
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    monkeypatch.setattr(config, "TEMP_DIR", (tmp_path / "tmp").as_posix())
    # _exec() puts the folder of the cli in front of PATH
    monkeypatch.setenv("PATH", os.environ.get("PATH", ""))
    monkeypatch.setitem(params, "audiocpp_model", SAVED)
    monkeypatch.setattr(_audiocpp, "down_audiocpp_bin", lambda **kwargs: None)
    monkeypatch.setattr(_audiocpp, "down_file_from_hf", lambda *args, **kwargs: None)
    commands = []

    def audiocpp_cli(cmd, *args, **kwargs):
        commands.append(cmd)
        with wave.open(cmd[cmd.index("--out") + 1], "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(b"\x01\x00" * 2400)

    monkeypatch.setattr(_audiocpp, "exec_audiocpp", audiocpp_cli)
    # instead of ffmpeg, which converts the output of the cli to 48 kHz stereo
    monkeypatch.setattr(
        _audiocpp.AudiocppTTS,
        "convert_to_wav",
        staticmethod(lambda src, dst, extra=None: shutil.copy(src, dst)),
    )
    played = []
    monkeypatch.setattr(
        _base, "pygameaudio", lambda filepath=None: played.append(filepath)
    )
    return commands, played


def _models(commands):
    """The model family and file that each command of the cli used"""
    return [
        (cmd[cmd.index("--family") + 1], cmd[cmd.index("--model") + 1])
        for cmd in commands
    ]


def _model(name):
    return name, f"models/{get_audiocpp_rolelist(name)['file']}"


def test_trial_dubbing_without_a_model_uses_the_saved_one(audiocpp):
    commands, played = audiocpp
    trial = f"{config.TEMP_DIR}/trial.wav"
    # "Trial dubbing" in the panel that assigns voices to the lines of a single
    # video: ListenVoice calls tts.run() without a model
    tts.run(
        queue_tts=[
            {
                "text": "Hello there.",
                "role": ROLE,
                "filename": trial,
                "tts_type": tts.AUDIOCPP_TTS,
            }
        ],
        language="en",
        play=True,
        tts_type=tts.AUDIOCPP_TTS,
        model_name=None,
    )
    assert _models(commands) == [_model(SAVED)]
    assert played == [trial]


@pytest.mark.parametrize(
    "model_name, used",
    [
        # a task whose settings have no model, as the web UI and cli.py make them
        (None, SAVED),
        # the model chosen in the main window or a dubbing window
        ("voxcpm2", "voxcpm2"),
    ],
)
def test_dubbing_uses_the_chosen_or_the_saved_model(audiocpp, model_name, used):
    commands, played = audiocpp
    lines = [f"{config.TEMP_DIR}/{i}.wav" for i in (1, 2)]
    tts.run(
        queue_tts=[
            {"text": text, "role": ROLE, "filename": name, "tts_type": tts.AUDIOCPP_TTS}
            for text, name in zip(["Hello there.", "See you."], lines)
        ],
        language="en",
        uuid="audiocpp-test",
        tts_type=tts.AUDIOCPP_TTS,
        model_name=model_name,
    )
    assert _models(commands) == [_model(used)] * 2
    assert all(os.path.getsize(name) > 0 for name in lines)
    assert played == []
