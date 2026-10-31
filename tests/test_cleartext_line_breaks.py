import pytest

from videotrans.configure.config import app_cfg, settings
from videotrans.task.taskcfg import SrtItem
from videotrans.translator import _base, _microsoft
from videotrans.translator._microsoft import Microsoft
from videotrans.util.help_srt import cleartext

# five subtitle lines and the translation the API returns for each
TRANSLATIONS = {
    "我觉得我们应该……": "I think we should...",
    "马上离开这里。": "leave this place right now.",
    "好吧。": "Okay.",
    "你确定吗？": "Are you sure?",
    "确定。": "Sure.",
}


@pytest.mark.parametrize("ending", ["...", "......", "。。。", "？！", "?."])
def test_line_ending_in_a_punctuation_run_keeps_its_line_break(ending):
    text = f"I think we should{ending}\nleave this place right now.\nOkay."
    assert len(cleartext(text).split("\n")) == 3


def test_punctuation_run_inside_a_line_is_still_collapsed():
    assert cleartext("Wait... what?") == "Wait,what?"


class _Response:
    def __init__(self, texts):
        self.texts = texts

    def raise_for_status(self):
        pass

    def json(self):
        # like the real endpoint: one translation per line sent
        return [{"translations": [{"text": TRANSLATIONS[t]}]} for t in self.texts]


def _post(url, json, **kwargs):
    return _Response(json)


def test_each_line_keeps_its_own_translation(monkeypatch, tmp_path):
    monkeypatch.setattr(_microsoft.requests, "post", _post)
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    # keep the translation cache out of the repo's tmp folder
    monkeypatch.setattr(_base, "TEMP_ROOT", tmp_path.as_posix())
    # send all five lines in one request, as the default batch size does
    monkeypatch.setattr(settings, "trans_thread", 5)
    items = [SrtItem(text=text, line=i + 1) for i, text in enumerate(TRANSLATIONS)]

    result = Microsoft(
        text_list=items, source_code="zh-Hans", target_code="en", is_test=True
    ).run()

    # each line gets its own translation, cleaned as if it had been sent alone
    expected = [cleartext(t) for t in TRANSLATIONS.values()]
    assert [it["text"] for it in result] == expected
