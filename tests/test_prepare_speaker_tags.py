import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from videotrans.configure.config import app_cfg
from videotrans.task import _stage_prepare
from videotrans.task._stage_prepare import PrepareMixin
from videotrans.util.help_srt import get_subtitle_from_srt


def _prepare(monkeypatch, tmp_path, texts):
    # the source subtitles, as the main window imports them from an .ass file:
    # ass_to_srt(..., True) puts each line's Name in front of it as [Name]
    source_sub = tmp_path / "en.srt"
    source_sub.write_text(
        "\n".join(
            f"{i}\n00:00:0{i - 1},000 --> 00:00:0{i},000\n{text}\n"
            for i, text in enumerate(texts, start=1)
        ),
        encoding="utf-8",
    )
    # a video with sound, without ffprobe and ffmpeg
    info = {
        "time": 10000,
        "streams_audio": 1,
        "video_streams": 1,
        "video_codec_name": "h264",
        "color": "yuv420p",
    }
    monkeypatch.setattr(_stage_prepare, "get_video_info", lambda name: info)
    monkeypatch.setattr(_stage_prepare, "run_in_threadpool", lambda *args: None)
    monkeypatch.setattr(app_cfg, "queue_novice", {})
    # stands in for the task: prepare() calls its methods and reads .cfg
    task = MagicMock(is_audio_trans=False, uuid="demo")
    task._exit.return_value = False
    task.cfg = SimpleNamespace(
        name=(tmp_path / "demo.mp4").as_posix(),
        app_mode="biaozhun",
        target_dir=tmp_path.as_posix(),
        cache_folder=(tmp_path / "cache").as_posix(),
        source_sub=source_sub.as_posix(),
        target_sub=(tmp_path / "zh-cn.srt").as_posix(),
        targetdir_mp4=(tmp_path / "out.mp4").as_posix(),
        source_wav=(tmp_path / "cache" / "en.wav").as_posix(),
        is_separate=False,
        vocal="",
        instrument="",
    )

    PrepareMixin.prepare(task)

    texts = [sub["text"] for sub in get_subtitle_from_srt(source_sub.as_posix())]
    speaker_json = tmp_path / "speaker.json"
    if not speaker_json.exists():
        return texts, None
    return texts, json.loads(speaker_json.read_text(encoding="utf-8"))


# names with characters that mean something in a regex, and a plain one
@pytest.mark.parametrize(
    "name", ["???", "Narrator (V.O.)", "Man?", "A+B", "Mob*", "Ann"]
)
def test_speaker_tags_are_removed(monkeypatch, tmp_path, name):
    texts, speakers = _prepare(
        monkeypatch,
        tmp_path,
        [f"[{name}]Who's there?", "[Tom]It's me.", f"[{name}]Come in."],
    )

    assert texts == ["Who's there?", "It's me.", "Come in."]
    assert speakers == [name, "Tom", name]
