import base64
import json
import shutil
import wave

import pytest

# not just "pydub": conftest puts a mock in its place when it isn't installed
pytest.importorskip("pydub.generators")

from pydub import AudioSegment
from pydub.generators import Sine
from pydub.silence import detect_nonsilent

from videotrans.configure.config import app_cfg
from videotrans.task._rate import SpeedRate, TtsSpeedRate
from videotrans.tts import DOUBAO2_TTS, _doubao2


class _FakeResponse:
    # the API streams json lines with base64 audio and ends with code 20000000
    def __init__(self, pcm):
        self.status_code = 200
        self.headers = {}
        self.lines = [
            json.dumps({"code": 0, "data": base64.b64encode(pcm).decode()}),
            json.dumps({"code": 20000000}),
        ]

    def raise_for_status(self):
        pass

    def iter_lines(self, decode_unicode=False):
        return iter(self.lines)


@pytest.fixture(autouse=True)
def _fake_api(monkeypatch):
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    # every line is 1 s of the 48 kHz mono 16-bit pcm that the request asks for
    pcm = Sine(440, sample_rate=48000).to_audio_segment(duration=1000).raw_data

    def post(url, **kwargs):
        return _FakeResponse(pcm)

    monkeypatch.setattr(_doubao2.requests, "post", post)


def _dub(tmp_path, slots):
    queue = [
        {
            "line": i + 1,
            "text": f"line {i + 1}",
            "start_time": start,
            "end_time": end,
            "filename": (tmp_path / f"{i}.wav").as_posix(),
        }
        for i, (start, end) in enumerate(slots)
    ]
    # wait_sec=0: no pause between lines
    _doubao2.Doubao2TTS(
        queue_tts=queue, language="zh", tts_type=DOUBAO2_TTS, wait_sec=0
    ).run()
    return queue


def test_mono_pcm_is_saved_with_its_length(tmp_path):
    # the 48 kHz mono 16-bit pcm from the API is saved as it is, in a mono wav;
    # convert_to_wav() then makes the line 48 kHz stereo
    pcm = Sine(440, sample_rate=48000).to_audio_segment(duration=1000).raw_data
    path = (tmp_path / "line.wav").as_posix()
    _doubao2.Doubao2TTS._save_pcm_to_wav(pcm, path)
    with wave.open(path, "rb") as wf:
        assert wf.getframerate() == 48000
        assert wf.getnchannels() == 1
        assert wf.getnframes() == 48000
        assert wf.readframes(wf.getnframes()) == pcm


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not found")
def test_saved_line_has_the_track_format(tmp_path):
    queue = _dub(tmp_path, [(0, 1000)])
    line = AudioSegment.from_file(queue[0]["filename"])
    assert line.frame_rate == SpeedRate.AUDIO_SAMPLE_RATE
    assert line.channels == SpeedRate.AUDIO_CHANNELS
    assert len(line) == 1000


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not found")
@pytest.mark.parametrize("cls", [SpeedRate, TtsSpeedRate])
@pytest.mark.parametrize("should_audiorate", [True, False])
@pytest.mark.parametrize("first_start", [0, 1000])
def test_lines_keep_their_length_in_the_track(
    cls, should_audiorate, first_start, tmp_path
):
    # at 0 ms the first file in the track is a dubbed line, at 1000 ms a silence
    queue = _dub(tmp_path, [(first_start, 3000), (3000, 6000), (6000, 8000)])
    rate = cls(
        queue_tts=queue,
        should_audiorate=should_audiorate,
        raw_total_time=8000,
        target_audio=(tmp_path / "target.wav").as_posix(),
        cache_folder=tmp_path.as_posix(),
    )
    rate.run()
    track = AudioSegment.from_file(rate.target_audio)
    assert len(track) == 8000
    sound = detect_nonsilent(track, min_silence_len=50, silence_thresh=-40)
    assert sound == [[first_start, first_start + 1000], [3000, 4000], [6000, 7000]]
