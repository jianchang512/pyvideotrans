import re
import shutil

import pytest

# not just "pydub": conftest puts a mock in its place when it isn't installed
pytest.importorskip("pydub.generators")

from pydub.generators import Sine

from videotrans import tts
from videotrans.configure import config
from videotrans.configure.config import app_cfg
from videotrans.task import dubbing
from videotrans.task.dubbing import DubbingSrt
from videotrans.task.taskcfg import TaskCfgTTS
from videotrans.util.help_ffmpeg import format_video

SRT = (
    "1\n00:00:00,000 --> 00:00:01,000\nHello there.\n\n"
    "2\n00:00:02,000 --> 00:00:03,000\nSee you.\n"
)
ROLE = "Ana(Female/US)"
# added to the name of the dubbing when the folder has a file of that name
TIME = r"-\d{8}-\d{6}"

# every case joins or converts audio with ffmpeg
pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not found"
)


def _tone(freq, duration):
    # a 48 kHz stereo tone, as the TTS channels leave each line
    tone = Sine(freq, sample_rate=48000).to_audio_segment(duration=duration, volume=-20)
    return tone.set_channels(2)


def _tts_run(queue_tts, **kwargs):
    # stands in for the TTS channel: a 1 s tone for each line
    for it in queue_tts:
        _tone(880, 1000).export(it["filename"], format="wav")


async def _edgetts_single(self, target_audio, kwargs):
    # stands in for Edge-TTS dubbing the whole text in one request
    _tone(880, 3000).export(target_audio, format="mp3")


@pytest.fixture(autouse=True)
def _app(monkeypatch, tmp_path):
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    # task_done() adds the finished task to this global set
    monkeypatch.setattr(app_cfg, "stoped_uuid_set", set())
    monkeypatch.setattr(dubbing, "HOME_DIR", (tmp_path / "home").as_posix())
    monkeypatch.setattr(config, "TEMP_DIR", (tmp_path / "tmp").as_posix())
    monkeypatch.setattr(tts, "run", _tts_run)
    monkeypatch.setattr(DubbingSrt, "_edgetts_single", _edgetts_single)
    srt = tmp_path / "subs" / "talk.srt"
    srt.parent.mkdir()
    srt.write_text(SRT, encoding="utf-8")


def _recording(tmp_path, ext):
    # e.g. the recording that talk.srt was transcribed from: with "Save to
    # SourceDir", Speech-to-Text saves talk.srt next to it
    recording = tmp_path / "subs" / f"talk.{ext}"
    # ffmpeg writes .m4a files with its mp4 muxer
    _tone(440, 500).export(recording.as_posix(), format="mp4" if ext == "m4a" else ext)
    return recording


def _dub(tmp_path, out_ext, remove_silent_mid=False, name="talk.srt"):
    """Dubs subs/<name> with Edge-TTS as Text-to-Speech does, with "Save to
    Original" checked"""
    imported = tmp_path / "subs" / name
    it = format_video(imported.as_posix(), None)
    # "Save to Original": the output folder is the imported file's own
    it["target_dir"] = imported.parent.as_posix()
    cfg = {
        "voice_role": ROLE,
        "cache_folder": f"{config.TEMP_DIR}/{it['uuid']}",
        "target_language_code": "en",
        "uuid": it["uuid"],
        "tts_type": tts.EDGE_TTS,
        "voice_autorate": False,
        "remove_silent_mid": remove_silent_mid,
        "align_sub_audio": False,
    }
    trk = DubbingSrt(cfg=TaskCfgTTS(**cfg | it), out_ext=out_ext)
    # as WorkerDubb, WorkerAlign and WorkerTaskDone run it
    trk.dubbing()
    trk.align()
    trk.task_done()


def _saved_audio(tmp_path):
    return sorted(
        p.name
        for p in (tmp_path / "subs").iterdir()
        if p.suffix in (".wav", ".mp3", ".m4a")
    )


@pytest.mark.parametrize("out_ext", ["mp3", "m4a"])
def test_mp3_or_m4a_keeps_a_file_of_that_name(tmp_path, out_ext):
    recording = _recording(tmp_path, out_ext)
    before = recording.read_bytes()

    _dub(tmp_path, out_ext)

    assert recording.read_bytes() == before
    # the time is added to the name, as align() does for the wav
    dubbed, kept = _saved_audio(tmp_path)
    assert re.fullmatch(rf"talk{TIME}\.{out_ext}", dubbed)
    assert kept == f"talk.{out_ext}"


def test_mp3_takes_the_name_of_the_srt(tmp_path):
    _dub(tmp_path, "mp3")

    assert _saved_audio(tmp_path) == ["talk.mp3"]


# with "Remove In-between Silences" checked and auto speed-up unchecked,
# Edge-TTS dubs the whole file in one request: _tts() saves the wav, and
# align() returns at once
@pytest.mark.parametrize(
    "out_ext, saved_as",
    [("wav", rf"talk{TIME}\.wav"), ("mp3", r"talk\.mp3")],
    ids=["wav", "mp3"],
)
def test_edge_tts_in_one_request_keeps_a_wav_of_that_name(tmp_path, out_ext, saved_as):
    recording = _recording(tmp_path, "wav")
    before = recording.read_bytes()

    _dub(tmp_path, out_ext, remove_silent_mid=True)

    assert recording.read_bytes() == before
    dubbed, kept = _saved_audio(tmp_path)
    assert re.fullmatch(saved_as, dubbed)
    assert kept == "talk.wav"


# Edge-TTS dubs a .txt file in one request too, whatever is checked: with the
# window's defaults, only "Save to Original" is needed
def test_edge_tts_keeps_a_wav_next_to_a_txt_file(tmp_path):
    txt = tmp_path / "subs" / "talk.txt"
    txt.write_text("Hello there.\nSee you.\n", encoding="utf-8")
    recording = _recording(tmp_path, "wav")
    before = recording.read_bytes()

    _dub(tmp_path, "wav", name="talk.txt")

    assert recording.read_bytes() == before
    dubbed, kept = _saved_audio(tmp_path)
    assert re.fullmatch(rf"talk{TIME}\.wav", dubbed)
    assert kept == "talk.wav"
