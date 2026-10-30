import pytest

# not just "pydub": conftest puts a mock in its place when it isn't installed
pytest.importorskip("pydub.generators")

from pydub.generators import Sine

from videotrans.configure.config import app_cfg
from videotrans.task._rate import SpeedRate

VIDEO_MS = 5000


@pytest.fixture(autouse=True)
def _cli_mode(monkeypatch):
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")


def _plan(tmp_path, last, *, video=False, audio=False, raw_total_time=VIDEO_MS):
    # two lines in a 5 s video, dubbed in 1 s and 3.5 s; last is (start, end) of line 2
    lines = [(500, 2000, 1000), (*last, 3500)]
    queue = []
    for i, (start, end, dub_ms) in enumerate(lines):
        wav = (tmp_path / f"{i}.wav").as_posix()
        tone = Sine(440, sample_rate=48000).to_audio_segment(duration=dub_ms)
        tone.set_channels(2).export(wav, format="wav")
        queue.append(
            {
                "line": i + 1,
                "text": f"line {i + 1}",
                "start_time": start,
                "end_time": end,
                "filename": wav,
            }
        )
    rate = SpeedRate(
        queue_tts=queue,
        should_videorate=video,
        should_audiorate=audio,
        raw_total_time=raw_total_time,
        target_audio=(tmp_path / "target.wav").as_posix(),
        cache_folder=tmp_path.as_posix(),
    )
    rate._prepare_data()
    rate._calculate_adjustments()
    return rate


def _last_line_targets(rate):
    # (last video clip: start, end, target length; last dub: target length)
    clip = rate.video_for_clips[-1] if rate.video_for_clips else None
    dub = rate.audio_data[-1] if rate.audio_data else None
    return (
        (clip["start"], clip["end"], clip["target_time"]) if clip else None,
        dub["target_time"] if dub else None,
    )


@pytest.mark.parametrize(
    ("audio", "expected"),
    [
        # the last 2000 ms of video are slowed down to the 3500 ms of the dub
        (False, ((3000, 5000, 3500), None)),
        # video and audio each take half of the 1500 ms difference
        (True, ((3000, 5000, 2750), None)),
    ],
    ids=["slow-down", "both"],
)
def test_last_line_past_the_video_is_cut_at_its_end(tmp_path, audio, expected):
    # the last subtitle ends 2 s after the video
    rate = _plan(tmp_path, (3000, 7000), video=True, audio=audio)
    assert _last_line_targets(rate) == expected
    assert rate.queue_tts[-1]["end_time"] == VIDEO_MS


def test_speed_up_only_keeps_the_end_past_the_video(tmp_path):
    # without video slow-down, cutting the slot would only squeeze the dub
    rate = _plan(tmp_path, (3000, 7000), audio=True)
    assert _last_line_targets(rate) == (None, 4000)
    assert rate.queue_tts[-1]["end_time"] == 7000


def test_last_line_starting_after_the_video_is_left_alone(tmp_path):
    # cutting it at the end of the video would put its end before its start
    rate = _plan(tmp_path, (5200, 6000), video=True)
    assert _last_line_targets(rate) == ((5200, 6000, 3500), None)
    assert rate.queue_tts[-1]["end_time"] == 6000


def test_last_line_before_the_video_end_is_still_extended(tmp_path):
    rate = _plan(tmp_path, (3000, 4000), video=True)
    assert rate.queue_tts[-1]["end_time"] == VIDEO_MS


def test_unknown_video_length_leaves_the_last_line_alone(tmp_path):
    rate = _plan(tmp_path, (3000, 7000), video=True, raw_total_time=0)
    assert rate.queue_tts[-1]["end_time"] == 7000
