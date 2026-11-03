import shutil
import sys
from unittest.mock import MagicMock

import pytest

from videotrans import tts
from videotrans.configure import config
from videotrans.configure.config import app_cfg, params
from videotrans.util.help_misc import vail_file

# the channels send their requests with gradio_client, which these tests replace
for _mod in ("gradio_client",):
    try:
        __import__(_mod)
    except ImportError:
        sys.modules[_mod] = MagicMock()

from videotrans.tts._gradio import GradioBase  # noqa: E402


@pytest.fixture
def sent(monkeypatch, tmp_path):
    """Stands in for the Gradio app of the channel; returns the keyword
    arguments of each Client.predict() call"""
    calls = []

    class Client:
        def predict(self, **kwargs):
            calls.append(kwargs)
            # the app returns the path of the audio it generated
            wav = tmp_path / f"generated-{len(calls)}.wav"
            wav.write_bytes(b"RIFF")
            return wav.as_posix()

    monkeypatch.setattr(GradioBase, "get_thread_client", lambda self: Client())
    # the audio is converted to 48 kHz stereo with ffmpeg: copy it instead
    monkeypatch.setattr(
        GradioBase,
        "convert_to_wav",
        staticmethod(lambda src, dst, extra=None: shutil.copyfile(src, dst)),
    )
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    monkeypatch.setattr(config, "TEMP_DIR", (tmp_path / "tmp").as_posix())
    return calls


def _dub(tts_type, tmp_path, sent):
    """Dubs one English line in a cloned voice, as the dubbing stage of a task
    does; returns the request for it"""
    ref_wav = tmp_path / "ref.wav"
    ref_wav.write_bytes(b"RIFF")
    line = {
        "line": 1,
        "text": "Hello there.",
        "role": "clone",
        "filename": (tmp_path / "line.wav").as_posix(),
        "ref_wav": ref_wav.as_posix(),
        "ref_text": "The reference text.",
    }
    tts.run(queue_tts=[line], language="en", uuid="test-uuid", tts_type=tts_type)
    assert vail_file(line["filename"])
    (kwargs,) = sent
    return kwargs


# the settings window saves V1, V2 and V2.5 as index_version 0, 1 and 2
@pytest.mark.parametrize(
    "version, inputs, lang_choice",
    [
        # Index-TTS 1.5 has no emotion control
        (0, ["prompt", "text"], None),
        (1, ["emo_control_method", "emo_ref_path", "prompt", "text"], None),
        # 2.5 takes the language of the text, ZH when it isn't sent
        (
            2,
            ["emo_control_method", "emo_ref_path", "lang_choice", "prompt", "text"],
            "EN",
        ),
    ],
    ids=["V1", "V2", "V2.5"],
)
def test_index_tts_sends_the_inputs_of_the_chosen_version(
    monkeypatch, tmp_path, sent, version, inputs, lang_choice
):
    monkeypatch.setitem(params, "index_version", version)

    kwargs = _dub(tts.INDEX_TTS, tmp_path, sent)

    assert kwargs.pop("api_name") == "/gen_single"
    assert sorted(kwargs) == inputs
    assert kwargs.get("lang_choice") == lang_choice


# v2 and v1 are the app.py of VoxCPM 2 and VoxCPM 1, hf the demo on huggingface.co
@pytest.mark.parametrize(
    "version, inputs",
    [
        (
            "v2",
            [
                "cfg_value",
                "control_instruction",
                "denoise",
                "dit_steps",
                "do_normalize",
                "prompt_text_value",
                "ref_wav",
                "text",
                "use_prompt_text",
            ],
        ),
        (
            "v1",
            [
                "cfg_value_input",
                "denoise",
                "do_normalize",
                "inference_timesteps_input",
                "prompt_text_input",
                "prompt_wav_path_input",
                "text_input",
            ],
        ),
        (
            "hf",
            [
                "cfg_value_input",
                "control_instruction",
                "denoise",
                "do_normalize",
                "prompt_text_input",
                "reference_wav_path_input",
                "text_input",
                "use_prompt_text",
            ],
        ),
    ],
    ids=["v2", "v1", "hf"],
)
def test_voxcpm_sends_the_inputs_of_the_chosen_version(
    monkeypatch, tmp_path, sent, version, inputs
):
    monkeypatch.setitem(params, "voxcpm_version", version)

    kwargs = _dub(tts.VOXCPM_TTS, tmp_path, sent)

    assert kwargs.pop("api_name") == "/generate"
    assert sorted(kwargs) == inputs
