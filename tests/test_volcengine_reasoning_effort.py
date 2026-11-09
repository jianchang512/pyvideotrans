from types import SimpleNamespace

import pytest

from videotrans import translator
from videotrans.configure.config import app_cfg, params
from videotrans.task.taskcfg import SrtItem
from videotrans.translator import _base, _openaicompat
from videotrans.translator._huoshan import HuoShan


@pytest.fixture
def send(monkeypatch, tmp_path):
    """Translates one line with the VolcEngine LLM channel, with the Reasoning
    Effort chosen in the ByteDance Ark window; returns the keyword arguments
    of the chat completion request"""
    sent = []

    def create(**kwargs):
        sent.append(kwargs)
        message = SimpleNamespace(content="<TRANSLATE_TEXT>Hello</TRANSLATE_TEXT>")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    # the OpenAI client that _create_completion() sends the request with
    monkeypatch.setattr(
        _openaicompat,
        "OpenAI",
        lambda **kw: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        ),
    )
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    # BaseTrans creates the translation cache folder there
    monkeypatch.setattr(_base, "TEMP_ROOT", tmp_path.as_posix())
    monkeypatch.setattr(params, "zijiehuoshan_key", "test-key")
    monkeypatch.setattr(params, "zijiehuoshan_model", "doubao-seed-2-0-pro-260215")
    # the key of the window's former Thinking checkbox, which a params.json
    # saved by v4.12 to v4.16 still has
    monkeypatch.delattr(params, "zijiehuoshan_thinking", raising=False)

    def run(effort):
        monkeypatch.setattr(params, "zijiehuoshan_reasoning_effort", effort)
        item = SrtItem(text="你好", line=1, time="00:00:01,000 --> 00:00:02,000")
        trans = HuoShan(
            text_list=[item],
            translate_type=translator.ZIJIE_INDEX,
            source_code="zh-cn",
            target_code="English",
            is_test=True,
        )
        assert trans._item_task("你好") == "Hello"
        return sent[-1]

    return run


def _thinking(effort):
    # none turns thinking off, the other values turn it on
    return {"thinking": {"type": "disabled" if effort == "none" else "enabled"}}


@pytest.mark.parametrize("effort", ["none", "low", "medium", "high", "max"])
def test_sends_the_chosen_reasoning_effort(send, effort):
    kwargs = send(effort)
    assert (kwargs.get("reasoning_effort"), kwargs["extra_body"]) == (
        effort,
        _thinking(effort),
    )


def test_default_sends_no_reasoning_parameters(send):
    # the model's own defaults apply
    kwargs = send("default")
    assert "reasoning_effort" not in kwargs
    assert kwargs["extra_body"] is None


@pytest.mark.parametrize("effort", ["none", "high"])
@pytest.mark.parametrize("old_thinking", [True, False], ids=["checked", "unchecked"])
def test_old_thinking_checkbox_key_is_ignored(send, monkeypatch, effort, old_thinking):
    monkeypatch.setattr(params, "zijiehuoshan_thinking", old_thinking, raising=False)
    kwargs = send(effort)
    assert (kwargs.get("reasoning_effort"), kwargs["extra_body"]) == (
        effort,
        _thinking(effort),
    )
