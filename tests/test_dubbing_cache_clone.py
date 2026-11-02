import shutil
from pathlib import Path

import pytest

from videotrans import tts
from videotrans.configure.config import app_cfg
from videotrans.task import _stage_dubbing
from videotrans.task.taskcfg import TaskCfgVTT
from videotrans.task.trans_create import TransCreate
from videotrans.util.help_misc import vail_file

# (time, spoken text, translation) of each line
THANKS = [("00:00:00,500 --> 00:00:03,500", "谢谢你。", "Thank you.")]


@pytest.fixture(autouse=True)
def _app(monkeypatch, tmp_path):
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    monkeypatch.setattr(app_cfg, "stoped_uuid_set", set())
    # every line is dubbed with voice_role
    monkeypatch.setattr(app_cfg, "line_roles", {})
    # the cache that _tts() shares between tasks
    cache = tmp_path / "dubbing_cache"
    cache.mkdir()
    monkeypatch.setattr(_stage_dubbing, "DUBBING_CACHE", cache.as_posix())


@pytest.fixture
def tts_calls(monkeypatch):
    """Stands in for the TTS channel and returns the lines it dubbed, per task"""
    calls = []

    def run_tts(*, queue_tts, **kwargs):
        dubbed = []
        for it in queue_tts:
            # like the channels, a line whose wav is already there is skipped
            if vail_file(it["filename"]):
                continue
            # a clone takes the voice of the reference audio
            voice = (
                Path(it["ref_wav"]).read_bytes()
                if it.get("ref_wav")
                else it["role"].encode()
            )
            Path(it["filename"]).write_bytes(voice)
            dubbed.append(it["line"])
        calls.append(dubbed)

    monkeypatch.setattr(_stage_dubbing, "run_tts", run_tts)
    return calls


def _srt(times, texts):
    return "\n".join(
        f"{i}\n{t}\n{text}\n" for i, (t, text) in enumerate(zip(times, texts), 1)
    )


def _dub(
    tmp_path,
    video,
    speakers,
    lines,
    voice_role="clone",
    tts_type=tts.F5_TTS,
    target_times=None,
    target_language_code="en",
):
    """Dubs a video in which speakers[i] says line i; returns each line's audio"""
    trk = TransCreate(
        cfg=TaskCfgVTT(
            name=(tmp_path / f"{video}.mp4").as_posix(),
            noextname=video,
            uuid=f"{video}-uuid",
            target_dir=(tmp_path / "out" / video).as_posix(),
            cache_folder=(tmp_path / "tmp" / video).as_posix(),
            source_language_code="zh-cn",
            target_language_code=target_language_code,
            voice_role=voice_role,
            tts_type=tts_type,
        )
    )
    Path(trk.cfg.target_dir).mkdir(parents=True, exist_ok=True)
    Path(trk.cfg.cache_folder).mkdir(parents=True, exist_ok=True)
    times = [it[0] for it in lines]
    source = _srt(times, [it[1] for it in lines])
    target = _srt(target_times or times, [it[2] for it in lines])
    Path(trk.cfg.source_sub).write_text(source, encoding="utf-8")
    # in a same-language task, this is the same file
    Path(trk.cfg.target_sub).write_text(target, encoding="utf-8")

    # what _create_ref_from_vocal() cuts from the video for each line
    def create_ref_from_vocal():
        for it, speaker in zip(trk.queue_tts, speakers):
            Path(it["ref_wav"]).write_bytes(speaker)

    trk._create_ref_from_vocal = create_ref_from_vocal
    trk.dubbing()
    return [Path(it["filename"]).read_bytes() for it in trk.queue_tts]


def test_clone_line_has_the_voice_of_its_own_video(tmp_path, tts_calls):
    assert _dub(tmp_path, "video1", [b"speaker 1"], THANKS) == [b"speaker 1"]
    # the same line in another video is dubbed again, with the speaker of that video
    assert _dub(tmp_path, "video2", [b"speaker 2"], THANKS) == [b"speaker 2"]
    assert tts_calls == [[1], [1]]


def test_clone_line_comes_from_the_cache_when_its_video_is_dubbed_again(
    tmp_path, tts_calls
):
    assert _dub(tmp_path, "video1", [b"speaker 1"], THANKS) == [b"speaker 1"]
    # a finished task deletes its folder, and align() has saved the length of
    # the dubbing in the target subtitles, which the next run of the video keeps
    shutil.rmtree(tmp_path / "tmp" / "video1")
    retimed = ["00:00:00,500 --> 00:00:02,400"]
    again = _dub(tmp_path, "video1", [b"speaker 1"], THANKS, target_times=retimed)
    assert again == [b"speaker 1"]
    assert tts_calls == [[1], []]


@pytest.mark.parametrize(
    "target_language_code, texts, edited",
    [
        ("en", ["Hello.", "Thank you.", "Goodbye."], "Bye."),
        # dubbing in the language of the video: one subtitle file is both the
        # source and the target subtitles
        ("zh-cn", ["你好。", "谢谢你。", "再见。"], "拜拜。"),
    ],
    ids=["translated", "same-language"],
)
def test_rerun_after_editing_the_subtitles_dubs_only_the_edited_line(
    tmp_path, tts_calls, target_language_code, texts, edited
):
    times = [
        "00:00:00,000 --> 00:00:01,000",
        "00:00:01,500 --> 00:00:02,500",
        "00:00:03,000 --> 00:00:04,000",
    ]
    spoken = ["你好。", "谢谢你。", "再见。"]
    lines = list(zip(times, spoken, texts))
    speakers = [b"speaker A", b"speaker B", b"speaker C"]
    first = _dub(
        tmp_path,
        "video1",
        speakers,
        lines,
        target_language_code=target_language_code,
    )
    assert first == speakers
    # the finished task has deleted its folder, and align() has saved the
    # lengths of the dubbing in the target subtitles; before the next run, the
    # first line is removed and the last one is changed
    shutil.rmtree(tmp_path / "tmp" / "video1")
    retimed = ["00:00:01,500 --> 00:00:02,100", "00:00:03,000 --> 00:00:03,700"]
    again = _dub(
        tmp_path,
        "video1",
        speakers[1:],
        [lines[1], (times[2], spoken[2], edited)],
        target_times=retimed,
        target_language_code=target_language_code,
    )
    assert again == speakers[1:]
    # the other line keeps its key, so only the changed one, now line 2, is sent
    assert tts_calls == [[1, 2, 3], [2]]


@pytest.mark.parametrize(
    "tts_type, role",
    [(tts.EDGE_TTS, "en-US-AriaNeural"), (tts.F5_TTS, "en_female_1.wav")],
    ids=["edge-tts", "f5-tts"],
)
def test_named_voice_is_still_shared_between_videos(
    tmp_path, tts_calls, tts_type, role
):
    voice = role.encode()
    assert _dub(tmp_path, "video1", [], THANKS, role, tts_type) == [voice]
    assert _dub(tmp_path, "video2", [], THANKS, role, tts_type) == [voice]
    assert tts_calls == [[1], []]
