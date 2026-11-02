import dataclasses

import pytest

from videotrans.configure._app_cfg import AppCfg
from videotrans.configure.config import app_cfg, settings
from videotrans.task import only_one
from videotrans.task.taskcfg import InputFile

SRT = "1\n00:00:00,000 --> 00:00:02,000\nHello there.\n"


@pytest.fixture(autouse=True)
def _app(monkeypatch, tmp_path):
    # the fields of single-video mode start from their defaults, as in a newly
    # started app, and get their values back afterwards
    for field in dataclasses.fields(AppCfg):
        if field.name.startswith("onlyone_"):
            monkeypatch.setattr(app_cfg, field.name, field.default)
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


def _translate(monkeypatch, tmp_path, remove_silent_mid, align_sub_audio):
    """Translates a video in single-video mode, with dubbing and both speed options
    off; returns what the dubbing proofreading panel showed for "Del inline mute?"
    and "Align subtitles and audio", and what align() got"""
    seen = {}

    class Task:
        """Stands in for TransCreate: its stages do nothing, and align() records
        the two options, which it passes to SpeedRate"""

        should_trans = False
        should_dubbing = True
        ignore_align = False
        should_recogn2 = False

        def __init__(self, cfg):
            self.cfg = cfg
            self.queue_tts = []
            self.video_info = {}

        def _nothing(self):
            pass

        prepare = recogn = diariz = trans = dubbing = _nothing
        recogn2pass = assembling = task_done = _nothing

        def align(self):
            seen["align"] = (self.cfg.remove_silent_mid, self.cfg.align_sub_audio)

    def post(text="", type="logs"):
        # what the main window does with the worker's messages
        if type == "error":
            pytest.fail(text)
        if type == "edit_dubbing":
            # the panel's checkboxes start from these (onlyone_set_editdubb.py),
            # and save_and_close() stores what they show, here unchanged
            seen["panel"] = (
                app_cfg.onlyone_remove_silent_mid,
                app_cfg.onlyone_align_sub_audio,
            )
        if type.startswith("edit_"):
            # a proofreading panel is saved: set_djs_timeout() ends the countdown
            app_cfg.set_countdown(-1)

    monkeypatch.setattr(only_one, "TransCreate", Task)
    for name in ("en.srt", "zh.srt"):
        (tmp_path / name).write_text(SRT, encoding="utf-8")
    # the two options as _actions_check.py puts them in the cfg when both speed
    # options are off, and the paths that TransCreate adds
    cfg = {
        "app_mode": "biaozhun",
        "batch": False,
        "voice_autorate": False,
        "video_autorate": False,
        "remove_silent_mid": remove_silent_mid,
        "align_sub_audio": align_sub_audio,
        "cache_folder": tmp_path.as_posix(),
        "source_sub": (tmp_path / "en.srt").as_posix(),
        "target_sub": (tmp_path / "zh.srt").as_posix(),
    }
    video = InputFile(name=(tmp_path / "talk.mp4").as_posix(), uuid="talk")
    worker = only_one.Worker(file=video, cfg=cfg)
    worker._post = post
    worker.run()
    return seen


@pytest.mark.parametrize(
    ("remove_silent_mid", "align_sub_audio"),
    [(True, False), (True, True), (False, False), (False, True)],
    ids=["del-mute", "del-mute-and-align", "neither", "align"],
)
def test_dubbing_panel_keeps_main_window_choices(
    monkeypatch, tmp_path, remove_silent_mid, align_sub_audio
):
    choices = (remove_silent_mid, align_sub_audio)

    seen = _translate(monkeypatch, tmp_path, *choices)

    assert seen == {"panel": choices, "align": choices}


def test_dubbing_panel_doesnt_keep_last_videos_choices(monkeypatch, tmp_path):
    # "Del inline mute?" was ticked in the dubbing panel of the last video
    monkeypatch.setattr(app_cfg, "onlyone_remove_silent_mid", True)

    seen = _translate(monkeypatch, tmp_path, False, True)

    assert seen == {"panel": (False, True), "align": (False, True)}
