import shutil

import pytest

# not just "pydub": conftest puts a mock in its place when it isn't installed
pytest.importorskip("pydub.generators")

from pydub import AudioSegment
from pydub.generators import Sine
from pydub.silence import detect_nonsilent

from videotrans.configure.config import app_cfg
from videotrans.task._rate import SpeedRate, TtsSpeedRate


@pytest.fixture(autouse=True)
def _cli_mode(monkeypatch):
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")


def _make_rate(cls, tmp_path):
    # lines 1 and 3 are 1 s 48 kHz stereo tones, line 2 failed to dub so it has no wav
    tone = Sine(440, sample_rate=48000).to_audio_segment(duration=1000).set_channels(2)
    queue = []
    for i, (start, end) in enumerate([(0, 1000), (1000, 4000), (4000, 5000)]):
        wav = (tmp_path / f"{i}.wav").as_posix()
        if i != 1:
            tone.export(wav, format="wav")
        queue.append(
            {
                "line": i + 1,
                "text": f"line {i + 1}",
                "start_time": start,
                "end_time": end,
                "filename": wav,
            }
        )
    return cls(
        queue_tts=queue,
        should_audiorate=True,
        raw_total_time=5000,
        target_audio=(tmp_path / "target.wav").as_posix(),
        cache_folder=tmp_path.as_posix(),
    )


@pytest.mark.parametrize("cls", [SpeedRate, TtsSpeedRate])
def test_placeholder_has_the_track_format(cls, tmp_path):
    rate = _make_rate(cls, tmp_path)
    rate._prepare_data()
    placeholder = AudioSegment.from_file(rate.queue_tts[1]["filename"])
    assert placeholder.frame_rate == cls.AUDIO_SAMPLE_RATE
    assert placeholder.channels == cls.AUDIO_CHANNELS
    assert len(placeholder) == 3000


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not found")
@pytest.mark.parametrize("cls", [SpeedRate, TtsSpeedRate])
def test_failed_line_does_not_shift_later_lines(cls, tmp_path):
    rate = _make_rate(cls, tmp_path)
    rate.run()
    track = AudioSegment.from_file(rate.target_audio)
    assert len(track) == 5000
    sound = detect_nonsilent(track, min_silence_len=50, silence_thresh=-40)
    assert sound == [[0, 1000], [4000, 5000]]
