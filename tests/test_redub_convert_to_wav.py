import shutil

import pytest

# not just "pydub": conftest puts a mock in its place when it isn't installed
pytest.importorskip("pydub.generators")

from pydub import AudioSegment
from pydub.generators import Sine

from videotrans.configure.base import BaseCon
from videotrans.configure.config import settings
from videotrans.process import _utils

# both conversions run ffmpeg
pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not found"
)

# the dubbing settings that the conversion applies, at their defaults
DEFAULTS = {
    "remove_dubb_silence": True,
    "remove_dubb_all_silence": False,
    "remove_dubb_silence_level": "default",
    "dubbing_normalize": False,
}


def _set(monkeypatch, **changed):
    for key, value in (DEFAULTS | changed).items():
        monkeypatch.setitem(settings, key, value)


def _convert(convert_to_wav, folder):
    """Converts a quiet 24 kHz mono line (two words with a 1 s pause between
    them and 0.3 s of silence at each end), saved as <line>-24k.wav like the
    built-in channels save theirs, and returns the converted line"""
    folder.mkdir()
    word = Sine(440, sample_rate=24000).to_audio_segment(duration=800, volume=-28)
    pause = AudioSegment.silent(duration=1000, frame_rate=24000)
    end = AudioSegment.silent(duration=300, frame_rate=24000)
    line = (folder / "line.wav").as_posix()
    (end + word + pause + word + end).export(f"{line}-24k.wav", format="wav")
    assert convert_to_wav(f"{line}-24k.wav", line)
    return AudioSegment.from_file(line, format="wav")


@pytest.mark.parametrize(
    "changed",
    [
        {},
        {"dubbing_normalize": True},
        {"remove_dubb_all_silence": True},
        {"remove_dubb_silence": False, "remove_dubb_all_silence": True},
        {"remove_dubb_silence_level": "max"},
    ],
    ids=[
        "defaults",
        "dubbing_normalize",
        "remove_dubb_all_silence",
        "remove_dubb_all_silence-without-trim",
        "remove_dubb_silence_level-max",
    ],
)
def test_redubbed_line_matches_the_first_dubbing(changed, monkeypatch, tmp_path):
    # the built-in F5-TTS, OmniVoice, Qwen3-TTS, Higgs-audio-v3 and Confucius4
    # channels convert a line re-dubbed in the proofreading panel in their
    # worker process with process/_utils.convert_to_wav, and the lines of the
    # first dubbing in the main process with BaseCon.convert_to_wav
    _set(monkeypatch, **changed)
    first = _convert(BaseCon.convert_to_wav, tmp_path / "first")
    redub = _convert(_utils.convert_to_wav, tmp_path / "redub")
    assert (redub.frame_rate, redub.channels) == (48000, 2)
    assert (len(redub), round(redub.max_dBFS, 1)) == (
        len(first),
        round(first.max_dBFS, 1),
    )
    assert redub.raw_data == first.raw_data


def test_redubbed_line_is_normalized(monkeypatch, tmp_path):
    _set(monkeypatch, dubbing_normalize=True)
    redub = _convert(_utils.convert_to_wav, tmp_path / "redub")
    # "Dubbing Peak Normalization" brings the peak of every line to -3 dBFS
    assert round(redub.max_dBFS, 1) == -3.0
