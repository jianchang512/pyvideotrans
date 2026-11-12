import re
import shutil
from queue import Queue
from unittest.mock import MagicMock

import pytest

# not just "pydub": conftest puts a mock in its place when it isn't installed
pytest.importorskip("pydub.generators")

from pydub.generators import Sine

from videotrans import translator, tts, winform
from videotrans.configure import config
from videotrans.configure._app_params import AppParams
from videotrans.configure.config import app_cfg
from videotrans.task import child_win_sign
from videotrans.util import help_misc
from videotrans.util.help_srt import get_subtitle_from_srt
from videotrans.winform import fn_peiyinrole

SRT = (
    "1\n00:00:00,000 --> 00:00:02,000\nHello there.\n\n"
    "2\n00:00:02,500 --> 00:00:04,500\nHow are you?\n"
)
ONE_LINE_SRT = "1\n00:00:00,000 --> 00:00:02,000\nHello there.\n"
ROLE = "Ana(Female/US)"

needs_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not found"
)


@pytest.fixture(autouse=True)
def _app(monkeypatch, tmp_path):
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    # task_done() adds the finished task to this global set
    monkeypatch.setattr(app_cfg, "stoped_uuid_set", set())
    monkeypatch.setattr(app_cfg, "dubbing_role", {})
    monkeypatch.setattr(app_cfg, "dubb_queue", Queue())
    monkeypatch.setattr(config, "TEMP_DIR", (tmp_path / "tmp").as_posix())
    # params of its own: openwin() reads the last settings from them, and
    # Start keeps the chosen ones there without saving them to params.json
    params = AppParams(_json_path=(tmp_path / "params.json").as_posix())
    monkeypatch.setattr(params, "save", lambda: None)
    monkeypatch.setattr(config, "params", params)
    # instead of a dialog, an error shown by Start fails the test
    monkeypatch.setattr(help_misc, "show_error", pytest.fail)
    # the QThread that passes the task's messages to the window
    monkeypatch.setattr(child_win_sign, "SignThread", MagicMock())


def _start(
    monkeypatch, tmp_path, save_to_srt, out_format, srt_text=SRT, tts_type=tts.EDGE_TTS
):
    """Clicks Start in Multi-Speaker with subs/talk.srt imported, returns the task"""
    srt = tmp_path / "subs" / "talk.srt"
    srt.parent.mkdir(exist_ok=True)
    srt.write_text(srt_text, encoding="utf-8")
    subs = get_subtitle_from_srt(srt.as_posix())
    # stands in for the window, whose widgets hold what the user chose
    win = MagicMock(srt_path=srt.as_posix(), subtitles=subs)
    # the output folder shown at the bottom of the window
    win.output_data.text.return_value = (tmp_path / "out").as_posix()
    monkeypatch.setattr(winform, "get_cls", lambda name: lambda: win)
    fn_peiyinrole.openwin()
    win.hecheng_language.currentText.return_value = translator.LANGNAME_DICT["en"]
    win.hecheng_role.currentText.return_value = ROLE
    win.tts_type.currentIndex.return_value = tts_type
    for slider in (win.hecheng_rate, win.volume_rate, win.pitch_rate):
        slider.value.return_value = 0
    for box in (win.voice_autorate, win.remove_silent_mid, win.is_cuda):
        box.isChecked.return_value = False
    win.save_to_srt.isChecked.return_value = save_to_srt
    win.out_format.currentText.return_value = out_format
    # one row per line, with its voice in column 3 and its text in column 5
    win.subtitle_table.rowCount.return_value = len(subs)
    win.subtitle_table.item.side_effect = lambda row, col: MagicMock(
        **{"text.return_value": ROLE if col == 3 else subs[row]["text"]}
    )

    start = win.hecheng_startbtn.clicked.connect.call_args.args[0]
    start()
    return app_cfg.dubb_queue.get_nowait()


def _tone(duration=1000):
    # a 48 kHz stereo wav, as the TTS channels leave each line
    tone = Sine(440, sample_rate=48000).to_audio_segment(duration=duration, volume=-20)
    return tone.set_channels(2)


def _saved_audio(tmp_path):
    return sorted(
        p.relative_to(tmp_path).as_posix()
        for folder in ("out", "subs")
        for p in (tmp_path / folder).rglob("*")
        if p.suffix in (".wav", ".mp3")
    )


def _recording(tmp_path):
    # e.g. the recording that the subtitles were made from
    recording = tmp_path / "subs" / "talk.wav"
    recording.parent.mkdir()
    _tone(500).export(recording.as_posix(), format="wav")
    return recording


def _dub(trk):
    # as dubbing() leaves it: a wav per line in the cache folder
    for i, sub in enumerate(trk.subs):
        wav = f"{trk.cfg.cache_folder}/dubb-{i}.wav"
        _tone().export(wav, format="wav")
        trk.queue_tts.append(
            {
                "line": sub["line"],
                "text": sub["text"],
                "start_time": sub["start_time"],
                "end_time": sub["end_time"],
                "filename": wav,
            }
        )


@pytest.mark.parametrize(
    "save_to_srt, saved",
    [(False, "out/talk.wav"), (True, "subs/talk.wav")],
)
def test_wav_is_saved_once_in_the_chosen_folder(
    monkeypatch, tmp_path, save_to_srt, saved
):
    trk = _start(monkeypatch, tmp_path, save_to_srt, "wav")
    # as align() leaves it: the dubbed subtitles in one wav
    _tone().export(trk.cfg.target_wav, format="wav")

    trk.task_done()

    assert _saved_audio(tmp_path) == [saved]


# "Save to Original" must not overwrite a wav of the same name next to the srt
@needs_ffmpeg
@pytest.mark.parametrize(
    "srt_text, tts_type",
    [
        pytest.param(SRT, tts.EDGE_TTS, id="two-lines"),
        # with one line, align() saves the wav in a branch of its own, which
        # writes nothing for Edge-TTS
        pytest.param(ONE_LINE_SRT, tts.G_TTS, id="one-line"),
    ],
)
def test_wav_next_to_the_srt_is_kept(monkeypatch, tmp_path, srt_text, tts_type):
    recording = _recording(tmp_path)
    before = recording.read_bytes()
    trk = _start(monkeypatch, tmp_path, True, "wav", srt_text, tts_type)
    _dub(trk)

    trk.align()
    trk.task_done()

    assert recording.read_bytes() == before
    # align() adds the time to the name of the dubbed wav, as in Text-to-Speech
    dubbed, kept = _saved_audio(tmp_path)
    assert re.fullmatch(r"subs/talk-\d{8}-\d{6}\.wav", dubbed)
    assert kept == "subs/talk.wav"


# with one line and Edge-TTS align() saves no wav, so for mp3 output
# task_done() must not convert the wav next to the srt and then delete it
@needs_ffmpeg
def test_wav_next_to_a_one_line_srt_is_kept_with_mp3(monkeypatch, tmp_path):
    recording = _recording(tmp_path)
    before = recording.read_bytes()
    trk = _start(monkeypatch, tmp_path, True, "mp3", ONE_LINE_SRT)
    _dub(trk)

    trk.align()
    trk.task_done()

    assert recording.read_bytes() == before


@needs_ffmpeg
@pytest.mark.parametrize(
    "save_to_srt, saved",
    [(False, "out/talk.mp3"), (True, "subs/talk.mp3")],
)
def test_mp3_is_saved_in_the_chosen_folder(monkeypatch, tmp_path, save_to_srt, saved):
    trk = _start(monkeypatch, tmp_path, save_to_srt, "mp3")
    _tone().export(trk.cfg.target_wav, format="wav")

    trk.task_done()

    assert _saved_audio(tmp_path) == [saved]
