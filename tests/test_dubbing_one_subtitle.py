import shutil
from concurrent.futures import ThreadPoolExecutor

import pytest

# not just "pydub": conftest puts a mock in its place when it isn't installed
pytest.importorskip("pydub.generators")

from pydub import AudioSegment
from pydub.generators import Sine
from pydub.silence import detect_leading_silence

from videotrans import tts
from videotrans.configure import config
from videotrans.configure.config import app_cfg
from videotrans.task import _rate, dubbing
from videotrans.task.dubbing import DubbingSrt
from videotrans.task.taskcfg import TaskCfgTTS
from videotrans.util.help_ffmpeg import format_video
from videotrans.util.help_srt import get_subtitle_from_srt

# a single subtitle, from 5 s to 7 s
SRT = "1\n00:00:05,000 --> 00:00:07,000\nHello there.\n"
ROLE = "Ana(Female/US)"

# every case joins or converts audio with ffmpeg
pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not found"
)


def _tone():
    # a 2 s 48 kHz stereo tone, as the TTS channels leave each line
    tone = Sine(440, sample_rate=48000).to_audio_segment(duration=2000, volume=-20)
    return tone.set_channels(2)


def _tts_run(queue_tts, **kwargs):
    # stands in for the TTS channel, and for Edge-TTS dubbing line by line
    for it in queue_tts:
        _tone().export(it["filename"], format="wav")


@pytest.fixture(autouse=True)
def _app(monkeypatch, tmp_path):
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    # task_done() adds the finished task to this global set
    monkeypatch.setattr(app_cfg, "stoped_uuid_set", set())
    # Multi-Speaker keeps the voice of each line here
    monkeypatch.setattr(app_cfg, "dubbing_role", {1: ROLE})
    monkeypatch.setattr(dubbing, "HOME_DIR", (tmp_path / "home").as_posix())
    monkeypatch.setattr(config, "TEMP_DIR", (tmp_path / "tmp").as_posix())
    monkeypatch.setattr(tts, "run", _tts_run)
    # auto speed-up shortens the dubbing in worker processes, which import
    # videotrans without the stand-ins from conftest.py: use threads instead
    monkeypatch.setattr(_rate, "ProcessPoolExecutor", ThreadPoolExecutor)


def _dub(tmp_path, srt=SRT, name="talk.srt", multi_speaker=False, **options):
    """Dubs subs/<name> as the Text-to-Speech or the Multi-Speaker window
    does, with OpenAI TTS unless options say otherwise, and returns the path
    of the wav it saves"""
    imported = tmp_path / "subs" / name
    imported.parent.mkdir()
    imported.write_text(srt, encoding="utf-8")
    it = format_video(imported.as_posix(), None)
    it["target_dir"] = (tmp_path / "out").as_posix()
    cfg = {
        "voice_role": ROLE,
        "cache_folder": f"{config.TEMP_DIR}/{it['uuid']}",
        "target_language_code": "en",
        "uuid": it["uuid"],
        "tts_type": tts.OPENAI_TTS,
        "voice_autorate": False,
        "remove_silent_mid": False,
        "align_sub_audio": False,
    }
    trk = DubbingSrt(
        cfg=TaskCfgTTS(**cfg | options | it),
        is_multi_role=multi_speaker,
        # Multi-Speaker dubs the subtitles it shows in its table
        subs=get_subtitle_from_srt(imported.as_posix()) if multi_speaker else [],
    )
    # as WorkerDubb, WorkerAlign and WorkerTaskDone run it
    trk.dubbing()
    trk.align()
    trk.task_done()
    return tmp_path / "out" / f"{imported.stem}.wav"


def _length_and_start(wav):
    # how long the wav is, and where its sound starts, in ms
    audio = AudioSegment.from_file(wav.as_posix())
    return len(audio), detect_leading_silence(audio)


# Edge-TTS dubs each line by itself unless "Remove In-between Silences" is
# checked and auto speed-up isn't (both are unchecked by default), and always
# in Multi-Speaker
@pytest.mark.parametrize(
    "options, multi_speaker",
    [({}, False), ({"voice_autorate": True}, False), ({}, True)],
    ids=["text-to-speech", "auto-speed-up", "multi-speaker"],
)
def test_edge_tts_saves_one_subtitle(tmp_path, options, multi_speaker):
    wav = _dub(tmp_path, multi_speaker=multi_speaker, tts_type=tts.EDGE_TTS, **options)

    assert wav.is_file()
    assert _length_and_start(wav) == pytest.approx((7000, 5000), abs=10)


# as with several subtitles, the dubbing starts where the subtitle starts
def test_one_subtitle_keeps_its_start_time(tmp_path):
    wav = _dub(tmp_path)

    assert _length_and_start(wav) == pytest.approx((7000, 5000), abs=10)


# the 2 s dubbing is sped up to fit the 1 s of its subtitle
def test_auto_speed_up_fits_one_subtitle(tmp_path):
    srt = "1\n00:00:05,000 --> 00:00:06,000\nHello there.\n"
    wav = _dub(tmp_path, srt, voice_autorate=True)

    assert _length_and_start(wav) == pytest.approx((6000, 5000), abs=10)


# OpenAI TTS has no volume setting, so align() applies the volume with ffmpeg,
# as tests/test_dubbing_volume.py checks for two subtitles
@pytest.mark.parametrize("volume, gain_db", [("+100%", 6.0), ("-50%", -6.0)])
def test_volume_is_applied_to_one_subtitle(tmp_path, volume, gain_db):
    # from 0 s to 2 s: no silence in the wav lowers its dBFS
    srt = "1\n00:00:00,000 --> 00:00:02,000\nHello there.\n"
    wav = _dub(tmp_path, srt, volume=volume)

    out = AudioSegment.from_file(wav.as_posix())
    assert out.dBFS == pytest.approx(_tone().dBFS + gain_db, abs=0.1)


# a line of a .txt file has no time: its dubbing is saved as it is
def test_one_line_txt_is_saved_as_dubbed(tmp_path):
    wav = _dub(tmp_path, "Hello there.\n", name="talk.txt")

    assert _length_and_start(wav) == pytest.approx((2000, 0), abs=10)
