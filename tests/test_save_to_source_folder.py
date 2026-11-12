import re
import shutil
from queue import Queue
from unittest.mock import MagicMock

import pytest

from videotrans import recognition, translator, tts, winform
from videotrans.component import component
from videotrans.configure import config
from videotrans.configure._app_params import AppParams
from videotrans.configure.config import app_cfg, settings, tr
from videotrans.task import child_win_sign, speech2text
from videotrans.task.dubbing import DubbingSrt
from videotrans.task.taskcfg import SrtItem
from videotrans.util import help_ffmpeg, help_misc
from videotrans.winform import fn_peiyin, fn_recogn

# the files chosen in Speech-To-Text: from two folders, two with the same name
MEDIA = ["week1/lecture.wav", "week2/lecture.wav", "week2/notes.wav"]
SRT = (
    "1\n00:00:00,000 --> 00:00:01,000\nHello there.\n\n"
    "2\n00:00:02,000 --> 00:00:03,000\nSee you.\n"
)
# Text-to-Speech names the text typed into its box after the time
TIME = r"\d{8}-\d{6}"

needs_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not found"
)


@pytest.fixture(autouse=True)
def _app(monkeypatch, tmp_path):
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    # task_done() adds the finished task to this global set
    monkeypatch.setattr(app_cfg, "stoped_uuid_set", set())
    # Start puts the tasks of Speech-To-Text and Text-to-Speech in these
    monkeypatch.setattr(app_cfg, "prepare_queue", Queue())
    monkeypatch.setattr(app_cfg, "dubb_queue", Queue())
    monkeypatch.setattr(config, "TEMP_DIR", (tmp_path / "tmp").as_posix())
    # params of their own: openwin() reads the last settings from them, and
    # Start keeps the chosen ones there without saving them to params.json
    params = AppParams(_json_path=(tmp_path / "params.json").as_posix())
    monkeypatch.setattr(params, "save", lambda: None)
    monkeypatch.setattr(config, "params", params)
    # Speech-To-Text's Start saves the settings: into a cfg.json of their own
    monkeypatch.setattr(settings, "_json_path", (tmp_path / "cfg.json").as_posix())
    # instead of a dialog, an error shown by Start fails the test
    monkeypatch.setattr(help_misc, "show_error", pytest.fail)
    # the QThread that passes the tasks' messages to the window
    monkeypatch.setattr(child_win_sign, "SignThread", MagicMock())
    # the file buttons that openwin() adds to the windows
    monkeypatch.setattr(component, "DropButton", MagicMock())
    monkeypatch.setattr(component, "PeiyinDropButton", MagicMock())


def _window(monkeypatch, tmp_path, openwin):
    """Opens a window with openwin(): a MagicMock stands in for it, whose
    widgets hold what the user chose"""
    win = MagicMock()
    monkeypatch.setattr(winform, "get_cls", lambda name: lambda: win)
    openwin()
    # the folder shown at the bottom of the window
    win.output_data.text.return_value = (tmp_path / "out").as_posix()
    return win


def _stt_start(monkeypatch, tmp_path, save_to_source):
    """Clicks Start in Speech-To-Text with the files of MEDIA, returns the tasks"""
    files = []
    for name in MEDIA:
        media = tmp_path / "media" / name
        media.parent.mkdir(parents=True, exist_ok=True)
        media.write_bytes(name.encode())
        files.append(media.as_posix())
    win = _window(monkeypatch, tmp_path, fn_recogn.openwin)
    win.shibie_dropbtn.filelist = files
    win.shibie_recogn_type.currentIndex.return_value = recognition.FASTER_WHISPER
    win.shibie_model.currentText.return_value = "tiny"
    win.shibie_language.currentText.return_value = tr("auto")
    for box in (win.is_cuda, win.rephrase, win.remove_noise, win.enable_diariz):
        box.isChecked.return_value = False
    win.spk_insert.isChecked.return_value = True
    win.fix_punc.currentIndex.return_value = 0
    win.nums_diariz.currentIndex.return_value = 0
    win.out_format.currentText.return_value = "srt"
    # "Save to SourceDir"
    win.copysrt_rawvideo.isChecked.return_value = save_to_source

    start = win.shibie_startbtn.clicked.connect.call_args.args[0]
    start()
    return [app_cfg.prepare_queue.get_nowait() for _ in MEDIA]


def _recognize(monkeypatch, tasks):
    """Runs each task as the app does, with stand-ins for the conversion to a
    16 kHz wav and for the recognition channel"""
    monkeypatch.setattr(
        help_ffmpeg, "conver_to_16k", lambda audio, target: shutil.copy(audio, target)
    )
    heard = {}

    def run(*, uuid, **kwargs):
        # one line that says which file it was
        return [SrtItem(line=1, start_time=0, end_time=1000, text=heard[uuid])]

    monkeypatch.setattr(speech2text, "run", run)
    for trk in tasks:
        heard[trk.uuid] = trk.cfg.name.split("/media/")[-1]
        trk.prepare()
        trk.recogn()
        trk.diariz()
        trk.task_done()


def test_stt_saves_each_subtitle_next_to_its_file(monkeypatch, tmp_path):
    tasks = _stt_start(monkeypatch, tmp_path, save_to_source=True)
    _recognize(monkeypatch, tasks)

    # the text of each subtitle says which file it is of
    saved = {
        p.relative_to(tmp_path).as_posix(): p.read_text(encoding="utf-8").split("\n")[2]
        for p in tmp_path.rglob("*.srt")
    }
    assert saved == {
        "media/week1/lecture.srt": "week1/lecture.wav",
        "media/week2/lecture.srt": "week2/lecture.wav",
        "media/week2/notes.srt": "week2/notes.wav",
    }


def test_stt_saves_into_the_output_folder(monkeypatch, tmp_path):
    tasks = _stt_start(monkeypatch, tmp_path, save_to_source=False)

    out = (tmp_path / "out").as_posix()
    assert [trk.cfg.target_sub for trk in tasks] == [
        f"{out}/lecture.srt",
        f"{out}/lecture.srt",
        f"{out}/notes.srt",
    ]


def _tone(duration):
    from pydub.generators import Sine

    # a 48 kHz stereo tone, as the TTS channels leave each line
    tone = Sine(880, sample_rate=48000).to_audio_segment(duration=duration, volume=-20)
    return tone.set_channels(2)


def _tts_run(queue_tts, **kwargs):
    # stands in for the TTS channel: a 1 s tone for each line
    for it in queue_tts:
        _tone(1000).export(it["filename"], format="wav")


async def _edgetts_single(self, target_audio, kwargs):
    # stands in for Edge-TTS dubbing the whole text in one request
    _tone(2000).export(target_audio, format="mp3")


def _tts_start(monkeypatch, tmp_path, save_to_original, typed, imported=()):
    """Clicks Start in Text-to-Speech with the text typed into its box and the
    .srt files imported, and dubs each task with Edge-TTS as the app does"""
    pytest.importorskip("pydub.generators")
    monkeypatch.setattr(tts, "run", _tts_run)
    monkeypatch.setattr(DubbingSrt, "_edgetts_single", _edgetts_single)
    files = []
    for name in imported:
        srt = tmp_path / "subs" / name
        srt.parent.mkdir(parents=True, exist_ok=True)
        srt.write_text(SRT, encoding="utf-8")
        files.append(srt.as_posix())
    win = _window(monkeypatch, tmp_path, fn_peiyin.openwin)
    win.hecheng_importbtn.filelist = files
    win.hecheng_plaintext.toPlainText.return_value = typed
    win.hecheng_language.currentText.return_value = translator.LANGNAME_DICT["en"]
    win.hecheng_role.currentText.return_value = "en-US-AvaNeural"
    win.tts_type.currentIndex.return_value = tts.EDGE_TTS
    for slider in (win.hecheng_rate, win.volume_rate, win.pitch_rate):
        slider.value.return_value = 0
    for box in (win.voice_autorate, win.remove_silent_mid, win.is_cuda):
        box.isChecked.return_value = False
    win.out_format.currentText.return_value = "wav"
    # "Save to Original"
    win.save_to_srt.isChecked.return_value = save_to_original

    start = win.hecheng_startbtn.clicked.connect.call_args.args[0]
    start()
    while not app_cfg.dubb_queue.empty():
        trk = app_cfg.dubb_queue.get_nowait()
        # as WorkerDubb, WorkerAlign and WorkerTaskDone run it
        trk.dubbing()
        trk.align()
        trk.task_done()


def _saved_audio(tmp_path):
    # the dubbed lines are in the tasks' cache folders, tmp/<uuid>
    return sorted(
        re.sub(TIME, "<time>", p.relative_to(tmp_path).as_posix())
        for p in tmp_path.rglob("*.wav")
        if p.parent.parent != tmp_path / "tmp"
    )


@needs_ffmpeg
@pytest.mark.parametrize("save_to_original", [True, False])
def test_tts_saves_typed_text_into_the_output_folder(
    monkeypatch, tmp_path, save_to_original
):
    _tts_start(monkeypatch, tmp_path, save_to_original, "Hello there.\nSee you.")

    # and not into the temp folder, which the app deletes when it closes
    assert _saved_audio(tmp_path) == ["out/<time>.wav"]


@needs_ffmpeg
def test_tts_saves_each_srt_dubbing_next_to_it(monkeypatch, tmp_path):
    _tts_start(
        monkeypatch,
        tmp_path,
        True,
        "Hello there.",
        imported=["week1/talk.srt", "week2/talk.srt"],
    )

    assert _saved_audio(tmp_path) == [
        "out/<time>.wav",
        "subs/week1/talk.wav",
        "subs/week2/talk.wav",
    ]
