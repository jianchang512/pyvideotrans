import json
from pathlib import Path

import pytest

from videotrans.configure.config import ROOT_DIR, app_cfg, settings
from videotrans.process import prepare_audio
from videotrans.task import _stage_recogn
from videotrans.task.taskcfg import SrtItem, TaskCfgVTT
from videotrans.task.trans_create import TransCreate
from videotrans.util import help_down
from videotrans.util.help_srt import get_subtitle_from_srt, ms_to_time_string

# (start, end, text the speech recognition returns, text with the punctuation restored)
LINES = [
    (500, 2000, "谢谢你", "谢谢你。"),
    (2500, 4000, "明天见", "明天见！"),
]


@pytest.fixture(autouse=True)
def _app(monkeypatch):
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    monkeypatch.setattr(app_cfg, "stoped_uuid_set", set())


@pytest.fixture
def calls(monkeypatch):
    """Stands in for the speech recognition, the model download and the punctuation
    model; returns the folders downloaded and the texts the model was given"""
    calls = {"download": [], "punctuation": []}

    def run_recogn(**kwargs):
        subtitles = []
        for i, (start, end, text, _) in enumerate(LINES, 1):
            startraw, endraw = ms_to_time_string(ms=start), ms_to_time_string(ms=end)
            subtitles.append(
                SrtItem(
                    line=i,
                    start_time=start,
                    end_time=end,
                    startraw=startraw,
                    endraw=endraw,
                    time=f"{startraw} --> {endraw}",
                    text=text,
                )
            )
        return subtitles

    def down_file_from_hf(local_dir, *args, **kwargs):
        calls["download"].append(local_dir)

    def new_process(self, callback=None, title="", kwargs=None):
        # the noise reduction isn't run here: as if it failed, the audio stays the same
        if callback is not prepare_audio.fix_punc:
            return False
        # like the punctuation model, writes the text of each line back with punctuation
        text_dict_file = Path(kwargs["text_dict_file"])
        texts = json.loads(text_dict_file.read_text(encoding="utf-8"))
        calls["punctuation"].append(texts)
        punctuated = {it[2]: it[3] for it in LINES}
        text_dict_file.write_text(
            json.dumps({k: punctuated[v.strip()] for k, v in texts.items()}),
            encoding="utf-8",
        )
        return True

    monkeypatch.setattr(_stage_recogn, "run_recogn", run_recogn)
    monkeypatch.setattr(help_down, "down_file_from_hf", down_file_from_hf)
    monkeypatch.setattr(TransCreate, "_new_process", new_process)
    # the default noise reduction model (zipenhancer would first download audio.cpp)
    monkeypatch.setitem(settings, "noise_model", "dpdfnet2.onnx")
    return calls


def _recogn(tmp_path, **cfg):
    """Runs the speech recognition of a video, as Start in the main window does;
    returns the text of each line, in the task and in the subtitle file it saved"""
    trk = TransCreate(
        cfg=TaskCfgVTT(
            name=(tmp_path / "video.mp4").as_posix(),
            noextname="video",
            uuid="video-uuid",
            target_dir=(tmp_path / "out").as_posix(),
            cache_folder=(tmp_path / "tmp").as_posix(),
            source_language_code="zh-cn",
            target_language_code="en",
            **cfg,
        )
    )
    Path(trk.cfg.target_dir).mkdir(parents=True)
    Path(trk.cfg.cache_folder).mkdir(parents=True)
    # the audio that prepare() extracts from the video
    Path(trk.cfg.source_wav).write_bytes(b"RIFF")
    trk.recogn()
    # translation and dubbing read the subtitle file
    saved = get_subtitle_from_srt(trk.cfg.source_sub)
    return [it["text"] for it in trk.source_srt_list], [it["text"] for it in saved]


@pytest.mark.parametrize(
    "remove_noise, is_separate",
    [
        pytest.param(False, False, id="denoise-off"),
        # with Separate Vocal/BGM checked, Denoise is skipped
        pytest.param(True, True, id="denoise-skipped-after-separation"),
        pytest.param(True, False, id="denoise-on"),
    ],
)
def test_restore_punct_adds_punctuation_to_the_recognized_lines(
    tmp_path, calls, remove_noise, is_separate
):
    punctuated = [it[3] for it in LINES]
    assert _recogn(
        tmp_path, fix_punc=1, remove_noise=remove_noise, is_separate=is_separate
    ) == (punctuated, punctuated)
    assert calls == {
        "download": [f"{ROOT_DIR}/models/puntc"],
        "punctuation": [{"1": "谢谢你", "2": "明天见"}],
    }


def test_default_punct_keeps_the_recognized_text(tmp_path, calls):
    recognized = [it[2] for it in LINES]
    assert _recogn(tmp_path, fix_punc=0) == (recognized, recognized)
    assert calls == {"download": [], "punctuation": []}
