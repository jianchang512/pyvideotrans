from types import SimpleNamespace

import pytest

from videotrans import translator
from videotrans.configure.config import app_cfg, params, settings
from videotrans.task.taskcfg import SrtItem
from videotrans.translator import _base
from videotrans.translator._localllm import LocalLLM

LINES = ["你好啊我的朋友", "明天见"]
TRANSLATION = ["Hello, my friend.", "See you tomorrow."]

# multi-line reasoning that restates the prompt's output rule, tag included,
# like the Qwen3-32B output quoted in #921
THINK_WITH_TAG = (
    "<think>\n"
    "The user wants two lines translated into English.\n"
    "I must wrap the output in <TRANSLATE_TEXT> tags and keep the line count.\n"
    "Two lines in, so two lines out.\n"
    "</think>\n\n"
)
THINK_WITHOUT_TAG = (
    "<think>\n"
    "The user wants two lines translated into English.\n"
    "Two lines in, so two lines out.\n"
    "</think>\n\n"
)
TEXT = "\n".join(TRANSLATION)
SRT = (
    "1\n00:00:01,000 --> 00:00:02,000\nHello, my friend.\n\n"
    "2\n00:00:03,000 --> 00:00:04,000\nSee you tomorrow."
)

REASONING = pytest.mark.parametrize(
    "reasoning",
    [THINK_WITH_TAG, THINK_WITHOUT_TAG, ""],
    ids=["think-with-tag", "think-without-tag", "no-think"],
)
TAGGED = pytest.mark.parametrize("tagged", [True, False], ids=["tagged", "untagged"])


def _translate(monkeypatch, tmp_path, content, send_srt):
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )
    monkeypatch.setattr(LocalLLM, "_create_completion", lambda self, kwargs: response)
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    # keep the translation cache out of the repo's tmp folder
    monkeypatch.setattr(_base, "TEMP_ROOT", tmp_path.as_posix())
    # the channel needs an API URL, though no request is sent
    monkeypatch.setattr(params, "localllm_api", "http://127.0.0.1:8000/v1")
    # the "Send SRT" setting, and both lines in one request in either mode
    monkeypatch.setattr(settings, "aisendsrt", send_srt)
    monkeypatch.setattr(settings, "trans_thread", 5)
    monkeypatch.setattr(settings, "aitrans_thread", 5)
    items = [
        SrtItem(
            text=text,
            line=i + 1,
            time=f"00:00:0{2 * i + 1},000 --> 00:00:0{2 * i + 2},000",
        )
        for i, text in enumerate(LINES)
    ]
    result = LocalLLM(
        text_list=items,
        translate_type=translator.LOCALLLM_INDEX,
        source_code="zh-cn",
        target_code="English",
        is_test=True,
    ).run()
    return [it["text"] for it in result]


@TAGGED
@REASONING
def test_text_mode_gets_only_the_translation(monkeypatch, tmp_path, reasoning, tagged):
    answer = f"<TRANSLATE_TEXT>\n{TEXT}\n</TRANSLATE_TEXT>" if tagged else TEXT
    content = reasoning + answer
    assert _translate(monkeypatch, tmp_path, content, False) == TRANSLATION


# the same responses with "Send SRT" on, where the reply is read as SRT
@TAGGED
@REASONING
def test_srt_mode_gets_only_the_translation(monkeypatch, tmp_path, reasoning, tagged):
    answer = f"<TRANSLATE_TEXT>\n{SRT}\n</TRANSLATE_TEXT>" if tagged else SRT
    content = reasoning + answer
    assert _translate(monkeypatch, tmp_path, content, True) == TRANSLATION
