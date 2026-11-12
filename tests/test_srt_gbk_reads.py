import codecs
import dataclasses
import tempfile
from pathlib import Path
from queue import Queue
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from videotrans import translator, tts, winform
from videotrans.component import component
from videotrans.configure import config
from videotrans.configure._app_cfg import AppCfg
from videotrans.configure._app_params import AppParams
from videotrans.configure._app_settings import AppSettings
from videotrans.configure.config import app_cfg, settings
from videotrans.mainwin import _actions_base_file
from videotrans.mainwin._actions_base_file import WinActionBaseFileMixin
from videotrans.task import child_win_sign, dubbing, only_one
from videotrans.task.dubbing import DubbingSrt
from videotrans.task.taskcfg import InputFile, TaskCfgTTS
from videotrans.util import help_ffmpeg, help_misc, help_srt
from videotrans.winform import fn_fanyisrt, fn_peiyin

SRT = (
    "1\n00:00:01,000 --> 00:00:03,500\n大家好。\n\n"
    "2\n00:00:04,000 --> 00:00:06,200\n你好，最近怎么样？\n"
)
# the same lines as a .txt file, one line per subtitle
TEXT = "大家好。\n你好，最近怎么样？\n"
LINES = [(1000, 3500, "大家好。"), (4000, 6200, "你好，最近怎么样？")]
# subtitles of the other language of the video, saved by the app as UTF-8
SRT_EN = (
    "1\n00:00:01,000 --> 00:00:03,500\nHello, everyone.\n\n"
    "2\n00:00:04,000 --> 00:00:06,200\nHi, how are you?\n"
)
ROLE = "Xiaoxiao(Female/CN)"
# the stages of TransCreate, in the order that the single-video worker runs them
STAGES = [
    "prepare",
    "recogn",
    "diariz",
    "trans",
    "dubbing",
    "align",
    "recogn2pass",
    "assembling",
    "task_done",
]
# GBK is "ANSI" in Notepad on Simplified Chinese Windows. Python's utf-16 and
# utf-32 codecs write a BOM, little-endian here, as > and Out-File of Windows
# PowerShell 5.1 do for UTF-16
ENCODINGS = ["utf-8", "gbk", "utf-16", "utf-32"]
# UTF-16 and UTF-32 with a BOM, in either byte order: Windows PowerShell 5.1
# saves the other forms with Set-Content -Encoding BigEndianUnicode, UTF32 or
# BigEndianUTF32
BOMS = {
    "utf-16-le": codecs.BOM_UTF16_LE,
    "utf-16-be": codecs.BOM_UTF16_BE,
    "utf-32-le": codecs.BOM_UTF32_LE,
    "utf-32-be": codecs.BOM_UTF32_BE,
}
SRT_OR_TXT = pytest.mark.parametrize(
    "name, text", [("talk.srt", SRT), ("talk.txt", TEXT)], ids=["srt", "txt"]
)

# with PySide6 installed, the QPlainTextEdit that openwin() of Translate SRT
# creates needs a QApplication; conftest.py's stand-in for PySide6 needs none
app = QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _app(monkeypatch, tmp_path):
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    # the fields of single-video mode, among them the subtitles imported in the
    # main window, start from their defaults and get their values back afterwards
    for field in dataclasses.fields(AppCfg):
        if field.name.startswith("onlyone_"):
            monkeypatch.setattr(app_cfg, field.name, field.default)
    # DubbingSrt saves into ROOT_DIR/output when it is given no output folder
    monkeypatch.setattr(dubbing, "ROOT_DIR", (tmp_path / "root").as_posix())
    monkeypatch.setattr(config, "TEMP_DIR", (tmp_path / "tmp").as_posix())


def _save(tmp_path, name, text, encoding):
    path = tmp_path / "subs" / name
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(text.encode(encoding))
    return path.as_posix()


def _save_with_bom(tmp_path, name, text, encoding):
    """Saves the text as Windows PowerShell 5.1 does: with the BOM of the
    encoding, and with CRLF line ends"""
    path = tmp_path / "subs" / name
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(BOMS[encoding] + text.replace("\n", "\r\n").encode(encoding))
    return path.as_posix()


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "gbk"])
@SRT_OR_TXT
def test_read_srt_text_reads_utf8_and_gbk(tmp_path, name, text, encoding):
    assert help_srt.read_srt_text(_save(tmp_path, name, text, encoding)) == text


# get_subtitle_from_srt() read these files before as well, and now does so with read_srt_text()
@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "gbk"])
def test_get_subtitle_from_srt_reads_utf8_and_gbk(tmp_path, encoding):
    srt = _save(tmp_path, "talk.srt", SRT, encoding)

    subtitles = help_srt.get_subtitle_from_srt(srt)

    assert [(it["start_time"], it["end_time"], it["text"]) for it in subtitles] == LINES


# the text comes without the BOM and with "\n" line ends, as from the files above
@pytest.mark.parametrize("encoding", BOMS)
@SRT_OR_TXT
def test_read_srt_text_reads_utf16_and_utf32(tmp_path, name, text, encoding):
    file = _save_with_bom(tmp_path, name, text, encoding)

    assert help_srt.read_srt_text(file) == text


@pytest.mark.parametrize("encoding", BOMS)
def test_get_subtitle_from_srt_reads_utf16_and_utf32(tmp_path, encoding):
    srt = _save_with_bom(tmp_path, "talk.srt", SRT, encoding)

    subtitles = help_srt.get_subtitle_from_srt(srt)

    assert [(it["start_time"], it["end_time"], it["text"]) for it in subtitles] == LINES


@pytest.mark.parametrize("encoding", ENCODINGS)
@pytest.mark.parametrize("srt_type", ["spoken", "target"])
def test_main_window_shows_imported_srt(monkeypatch, tmp_path, srt_type, encoding):
    srt = _save(tmp_path, "talk.srt", SRT, encoding)
    # the file chosen in the dialog of the import button
    qt = MagicMock()
    qt.QFileDialog.getOpenFileName.return_value = (srt, "Files(*.srt *.ass)")
    monkeypatch.setattr(_actions_base_file, "QtWidgets", qt)
    # stands in for the main window
    win = MagicMock()

    WinActionBaseFileMixin.import_srtfile(win, srt_type)

    # the file is shown under the name of the button
    shown = win.main.subtitle_area.insertPlainText.call_args.args[0]
    assert shown.endswith("]\n" + SRT)


def _translate_video(monkeypatch, tmp_path):
    """Translates and dubs a video in single-video mode, with the subtitles
    imported in the main window; returns the stages that ran and the subtitles
    that the worker sent to the main window's subtitle area"""
    stages, shown = [], []

    class Task:
        """Stands in for TransCreate: recogn() and trans() save the subtitles
        they would make, and the other stages only record that they ran"""

        should_trans = True
        should_dubbing = True
        ignore_align = False
        should_recogn2 = False

        def __init__(self, cfg):
            self.cfg = cfg
            self.queue_tts = []
            self.video_info = {}

        def recogn(self):
            stages.append("recogn")
            # skipped when the spoken subtitles were imported
            if not Path(self.cfg.source_sub).exists():
                Path(self.cfg.source_sub).write_text(SRT_EN, encoding="utf-8")

        def trans(self):
            # Worker.run() calls it only when no target subtitles were imported
            stages.append("trans")
            Path(self.cfg.target_sub).write_text(SRT_EN, encoding="utf-8")

    for name in set(STAGES) - {"recogn", "trans"}:
        setattr(Task, name, lambda self, name=name: stages.append(name))

    def post(text="", type="logs"):
        # what the main window does with the worker's messages
        if type == "error":
            pytest.fail(text)
        if type == "replace_subtitle":
            shown.append(text)
        if type.startswith("edit_"):
            # a proofreading panel is saved: set_djs_timeout() ends the countdown
            app_cfg.set_countdown(-1)

    monkeypatch.setattr(only_one, "TransCreate", Task)
    monkeypatch.setattr(app_cfg, "task_countdown", 0)
    # a running task: Worker._exit() stops it otherwise
    monkeypatch.setattr(app_cfg, "current_status", "ing")
    monkeypatch.setattr(app_cfg, "exit_soft", False)
    # the proofreading panels open only with a countdown, 30 s by default
    monkeypatch.setattr(settings, "countdown_sec", 30)
    # run() deletes the files of the last re-dub
    monkeypatch.setattr(
        only_one, "REDUBB_QUEUE_FILE", (tmp_path / "queue.json").as_posix()
    )
    monkeypatch.setattr(
        only_one, "REDUBB_STATUS_FILE", (tmp_path / "status.txt").as_posix()
    )
    # conftest.py's stand-in for QThread, when PySide6 isn't installed, is a
    # plain class, which doesn't take Worker's parent
    if only_one.QThread.__init__ is object.__init__:
        monkeypatch.setattr(
            only_one.QThread, "__init__", lambda self, parent=None: None
        )
    # the paths that TransCreate adds to the cfg
    video = tmp_path / "video"
    video.mkdir()
    cfg = {
        "app_mode": "biaozhun",
        "batch": False,
        "cache_folder": video.as_posix(),
        "source_sub": (video / "source.srt").as_posix(),
        "target_sub": (video / "target.srt").as_posix(),
    }
    worker = only_one.Worker(
        file=InputFile(name=(tmp_path / "talk.mp4").as_posix(), uuid="talk"), cfg=cfg
    )
    worker._post = post

    worker.run()

    return stages, shown


@pytest.mark.parametrize("encoding", ENCODINGS)
def test_single_video_task_with_imported_spoken_srt(monkeypatch, tmp_path, encoding):
    srt = _save(tmp_path, "talk.srt", SRT, encoding)
    # as the main window's "Import spoken srt or ass" stores it
    monkeypatch.setattr(app_cfg, "onlyone_importsrtfile", srt)

    stages, shown = _translate_video(monkeypatch, tmp_path)

    assert shown == [SRT, SRT_EN]
    assert stages == STAGES


@pytest.mark.parametrize("encoding", ENCODINGS)
def test_single_video_task_with_imported_target_srt(monkeypatch, tmp_path, encoding):
    srt = _save(tmp_path, "talk.srt", SRT, encoding)
    # as the main window's "Import target srt or ass" stores it
    monkeypatch.setattr(app_cfg, "onlyone_importsrtfile_target", srt)

    stages, shown = _translate_video(monkeypatch, tmp_path)

    assert shown == [SRT_EN, SRT]
    # the imported subtitles are dubbed without translating
    assert stages == [name for name in STAGES if name != "trans"]


def _dub(monkeypatch, file, tts_type, remove_silent_mid=False):
    """Dubs the file as Text-to-Speech and cli.py's tts task do; returns the
    text that the task sends to the window, or that cli.py prints"""
    replaced = []

    def signal(self, text="", type="logs", **kwargs):
        if type == "replace":
            replaced.append(text)

    monkeypatch.setattr(DubbingSrt, "signal", signal)
    it = help_ffmpeg.format_video(file, None)
    cfg = {
        "voice_role": ROLE,
        "cache_folder": f"{config.TEMP_DIR}/{it['uuid']}",
        "target_language_code": "zh-cn",
        "uuid": it["uuid"],
        "tts_type": tts_type,
        "voice_autorate": False,
        "remove_silent_mid": remove_silent_mid,
        "align_sub_audio": False,
    }
    trk = DubbingSrt(cfg=TaskCfgTTS(**cfg | it))
    # as WorkerDubb runs it
    trk.dubbing()
    return replaced


# also with a file saved as UTF-8 with a BOM, whose BOM isn't dubbed as U+FEFF
@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "gbk", "utf-16", "utf-32"])
@SRT_OR_TXT
def test_dubbing_sends_each_line(monkeypatch, tmp_path, name, text, encoding):
    queued = []

    def run(queue_tts, **kwargs):
        # stands in for the TTS channel
        queued.extend(it["text"] for it in queue_tts)

    monkeypatch.setattr(tts, "run", run)
    file = _save(tmp_path, name, text, encoding)

    # a channel that dubs each line by itself
    replaced = _dub(monkeypatch, file, tts.G_TTS)

    assert queued == ["大家好。", "你好，最近怎么样？"]
    assert replaced == [text]


# with "Remove In-between Silences" checked and auto speed-up unchecked, Edge-TTS
# dubs an .srt file in one request; a .txt file always
@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "gbk", "utf-16", "utf-32"])
@SRT_OR_TXT
def test_edge_tts_sends_the_texts_in_one_request(
    monkeypatch, tmp_path, name, text, encoding
):
    sent = []

    async def _edgetts_single(self, target_audio, kwargs):
        # stands in for Edge-TTS dubbing the whole text in one request
        sent.append(kwargs["text"])

    monkeypatch.setattr(DubbingSrt, "_edgetts_single", _edgetts_single)
    # converts Edge-TTS's mp3 to the wav
    monkeypatch.setattr(help_ffmpeg, "runffmpeg", lambda cmd, **kw: None)
    # where _convert_to_utf8_if_needed() saves a UTF-8 copy of a GBK file
    temp = tmp_path / "temp"
    temp.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", temp.as_posix())
    file = _save(tmp_path, name, text, encoding)

    replaced = _dub(monkeypatch, file, tts.EDGE_TTS, remove_silent_mid=True)

    # only the texts, without the line numbers and times of the .srt file,
    # without U+FEFF from the BOM of a file saved as UTF-8 with a BOM, and not
    # the bytes of a UTF-16 or UTF-32 file decoded as Latin-1
    assert sent == [TEXT]
    assert replaced == [text]


@pytest.fixture
def window(monkeypatch, tmp_path):
    """Stands in for the Text-to-Speech or Translate SRT window, whose widgets
    hold what the user chose"""
    win = MagicMock()
    # the output folder shown at the bottom of the window
    win.output_data.text.return_value = (tmp_path / "out").as_posix()
    monkeypatch.setattr(winform, "get_cls", lambda name: lambda: win)
    # the drop button for the files, which openwin() of Text-to-Speech adds
    monkeypatch.setattr(component, "PeiyinDropButton", lambda *args: MagicMock())
    # params of their own: openwin() reads the last settings from them, and
    # Start keeps the chosen ones there without saving them to params.json
    params = AppParams(_json_path=(tmp_path / "params.json").as_posix())
    monkeypatch.setattr(params, "save", lambda: None)
    monkeypatch.setattr(config, "params", params)
    # Start in Translate SRT keeps "Send SRT" in settings and saves them to
    # cfg.json: the value is put back afterwards, and cfg.json isn't written
    monkeypatch.setattr(AppSettings, "save", lambda self, data=None: None)
    monkeypatch.setitem(settings, "aisendsrt", settings.get("aisendsrt"))
    # instead of a dialog, an error shown by Start fails the test
    monkeypatch.setattr(help_misc, "show_error", pytest.fail)
    # the QThread that passes the task's messages to the window
    monkeypatch.setattr(child_win_sign, "SignThread", MagicMock())
    monkeypatch.setattr(app_cfg, "dubb_queue", Queue())
    monkeypatch.setattr(app_cfg, "trans_queue", Queue())
    return win


@pytest.mark.parametrize("encoding", ENCODINGS)
@SRT_OR_TXT
def test_text_to_speech_starts(window, tmp_path, name, text, encoding):
    file = _save(tmp_path, name, text, encoding)
    fn_peiyin.openwin()
    # the imported file, and the window's defaults
    window.hecheng_importbtn.filelist = [file]
    window.hecheng_plaintext.toPlainText.return_value = ""
    window.hecheng_language.currentText.return_value = translator.LANGNAME_DICT["zh-cn"]
    window.hecheng_role.currentText.return_value = ROLE
    window.tts_type.currentIndex.return_value = tts.EDGE_TTS
    for slider in (window.hecheng_rate, window.volume_rate, window.pitch_rate):
        slider.value.return_value = 0
    for box in (
        window.voice_autorate,
        window.remove_silent_mid,
        window.save_to_srt,
        window.is_cuda,
    ):
        box.isChecked.return_value = False
    window.out_format.currentText.return_value = "wav"

    start = window.hecheng_startbtn.clicked.connect.call_args.args[0]
    start()

    assert app_cfg.dubb_queue.get_nowait().cfg.target_sub == file
    # the text box shows the file, and the window gets the task's messages
    window.hecheng_plaintext.insertPlainText.assert_called_once_with(text)
    child_win_sign.SignThread.return_value.start.assert_called_once_with()


@pytest.mark.parametrize("encoding", ENCODINGS)
def test_translate_srt_starts(window, tmp_path, encoding):
    srt = _save(tmp_path, "talk.srt", SRT, encoding)
    fn_fanyisrt.openwin()
    # in place of the source box, a QPlainTextEdit that openwin() adds
    window.fanyi_sourcetext = MagicMock()
    # the imported file, and the window's defaults
    window.files = [srt]
    window.fanyi_source.currentText.return_value = translator.LANGNAME_DICT["zh-cn"]
    window.fanyi_target.currentText.return_value = translator.LANGNAME_DICT["en"]
    window.fanyi_translate_type.currentIndex.return_value = translator.GOOGLE_INDEX
    window.fanyi_proxy.text.return_value = ""
    for box in (window.aisendsrt, window.save_source, window.is_cuda):
        box.isChecked.return_value = False
    window.out_format.currentIndex.return_value = 0

    start = window.fanyi_start.clicked.connect.call_args.args[0]
    start()

    assert app_cfg.trans_queue.get_nowait().cfg.source_sub == srt
    # the source box shows the file, and Start stays disabled until the task ends
    window.fanyi_sourcetext.setPlainText.assert_called_once_with(SRT)
    window.fanyi_start.setDisabled.assert_called_once_with(True)
