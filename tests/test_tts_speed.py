import shutil
import sys
import types
from unittest.mock import MagicMock

import pytest

from videotrans import tts
from videotrans.configure import config
from videotrans.configure.config import app_cfg, params
from videotrans.tts._base import BaseTTS
from videotrans.util.help_misc import vail_file

# _piper.py imports g2pw and piper-tts when it is loaded; the tests replace the voice
try:
    import g2pw.api  # noqa: F401
except ImportError:
    sys.modules["g2pw"] = MagicMock()
    sys.modules["g2pw.api"] = sys.modules["g2pw"].api
try:
    import piper  # noqa: F401
except ImportError:
    sys.modules["piper"] = MagicMock()

from videotrans.tts import _gptsovits, _piper  # noqa: E402

# speech rates of the dubbing and the speeds get_speed() makes of them
RATES = [("-20%", 0.8), ("+0%", 1.0), ("+20%", 1.2), ("+50%", 1.5)]


@pytest.fixture(autouse=True)
def _app(monkeypatch, tmp_path):
    # the audio is converted to 48 kHz stereo with ffmpeg: copy it instead
    monkeypatch.setattr(
        BaseTTS,
        "convert_to_wav",
        staticmethod(lambda src, dst, extra=None: shutil.copyfile(src, dst)),
    )
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    monkeypatch.setattr(config, "TEMP_DIR", (tmp_path / "tmp").as_posix())


def _dub(tts_type, tmp_path, role, rate):
    """Dubs one English line at the speech rate, as the dubbing stage of a task
    does"""
    line = {
        "line": 1,
        "text": "Hello there.",
        "role": role,
        "rate": rate,
        "filename": (tmp_path / "line.wav").as_posix(),
    }
    tts.run(queue_tts=[line], language="en", uuid="test-uuid", tts_type=tts_type)
    assert vail_file(line["filename"])


@pytest.fixture
def length_scales(monkeypatch):
    """Stands in for piper-tts and the voice; returns the length_scale of each
    line it synthesized"""
    scales = []

    class Voice:
        def synthesize_wav(self, text, wav_file, syn_config=None):
            scales.append(syn_config.length_scale)
            # 0.1 s of silence
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            wav_file.writeframes(bytes(2 * 2205))

    monkeypatch.setattr(
        _piper, "PiperVoice", types.SimpleNamespace(load=lambda *a, **kw: Voice())
    )
    monkeypatch.setattr(_piper, "SynthesisConfig", types.SimpleNamespace)
    # never download the G2PW model or the voice
    monkeypatch.setattr(_piper.PiperTTS, "_download", lambda self: True)
    monkeypatch.setattr(
        _piper.PiperTTS, "_get_model_from_name", lambda self, name: f"{name}.onnx"
    )
    return scales


# length_scale is the phoneme length in piper-tts: < 1 is faster, > 1 is slower
@pytest.mark.parametrize("rate, speed", RATES)
def test_piper_length_scale_is_the_inverse_of_the_speed(
    tmp_path, length_scales, rate, speed
):
    _dub(tts.PIPER_TTS, tmp_path, "en_US-lessac-medium", rate)

    assert length_scales == [pytest.approx(1 / speed)]


def test_piper_dubs_at_minus_100_percent(tmp_path, length_scales):
    # the Text-to-Speech window goes down to -100%, where get_speed() is 0:
    # the line is dubbed as slowly as at -90%, with 10 times the phoneme length
    _dub(tts.PIPER_TTS, tmp_path, "en_US-lessac-medium", "-100%")

    assert length_scales == [pytest.approx(10)]


@pytest.fixture
def requests_sent(monkeypatch):
    """Stands in for the GPT-SoVITS API; returns the URL and the JSON of each
    request"""
    sent = []

    def post(url, json=None, **kwargs):
        sent.append((url, json))
        return types.SimpleNamespace(ok=True, content=b"RIFF", text="")

    monkeypatch.setattr(_gptsovits.requests, "post", post)
    # skip the waits after each line: 1 s in _gptsovits.py, dubbing_wait in _base.py
    monkeypatch.setattr(_gptsovits.time, "sleep", lambda s: None)
    monkeypatch.setitem(params, "gptsovits_url", "http://127.0.0.1:9880")
    # a voice of the GPT-SoVITS window: reference audio#its text#its language
    monkeypatch.setitem(params, "gptsovits_role", "ref.wav#The reference text.#en")
    return sent


# api.py takes the speed as "speed", api_v2.py as "speed_factor": both are 1 at
# the normal speed, and higher is faster
GPTSOVITS_APIS = pytest.mark.parametrize(
    "isv2, url, key",
    [
        (False, "http://127.0.0.1:9880", "speed"),
        (True, "http://127.0.0.1:9880/tts", "speed_factor"),
    ],
    ids=["api.py", "api_v2.py"],
)


@pytest.mark.parametrize("rate, speed", RATES[:3])
@GPTSOVITS_APIS
def test_gptsovits_sends_the_speed_of_the_rate(
    monkeypatch, tmp_path, requests_sent, isv2, url, key, rate, speed
):
    monkeypatch.setitem(params, "gptsovits_isv2", isv2)

    _dub(tts.GPTSOVITS_TTS, tmp_path, "ref.wav", rate)

    ((sent_url, data),) = requests_sent
    assert sent_url == url
    assert data[key] == pytest.approx(speed)


@GPTSOVITS_APIS
def test_gptsovits_sends_0_1_at_minus_100_percent(
    monkeypatch, tmp_path, requests_sent, isv2, url, key
):
    # at -100% get_speed() is 0, and GPT-SoVITS divides by the speed: the line
    # is sent with the speed of -90%
    monkeypatch.setitem(params, "gptsovits_isv2", isv2)

    _dub(tts.GPTSOVITS_TTS, tmp_path, "ref.wav", "-100%")

    ((sent_url, data),) = requests_sent
    assert sent_url == url
    assert data[key] == pytest.approx(0.1)
