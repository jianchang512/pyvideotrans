import pytest

from videotrans.configure.config import app_cfg, settings
from videotrans.task.taskcfg import SrtItem
from videotrans.translator import _base, _google
from videotrans.translator._google import Google


class _Response:
    status_code = 200

    def __init__(self, translation):
        # like translate.google.com/m: the translation is in the result
        # container, escaped as HTML
        self.text = (
            '<div class="input-container"></div>'
            f'<div class="result-container">{translation}</div>'
            '<div class="links-container"></div>'
        )

    def raise_for_status(self):
        pass


@pytest.mark.parametrize(
    "target_code, page_text, expected",
    [
        # as on a real result page: "Salut, je m&#39;appelle Ray"
        (
            "fr",
            "Salut, je m&#39;appelle Ray.\nJe viens du Costa Rica.",
            ["Salut, je m'appelle Ray.", "Je viens du Costa Rica."],
        ),
        ("en", "I don&#39;t know.\nWe&#39;ll go.", ["I don't know.", "We'll go."]),
        ("en", "He said &quot;hello&quot;.", ['He said "hello".']),
        ("en", "Tom &amp; Jerry &lt;3", ["Tom & Jerry <3"]),
    ],
    ids=["apostrophe", "contractions", "double-quotes", "ampersand"],
)
def test_translation_keeps_the_characters_the_page_escapes(
    monkeypatch, tmp_path, target_code, page_text, expected
):
    monkeypatch.setattr(
        _google.requests, "get", lambda url, **kwargs: _Response(page_text)
    )
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    # keep the translation cache out of the repo's tmp folder
    monkeypatch.setattr(_base, "TEMP_ROOT", tmp_path.as_posix())
    # send all lines in one request, as the default batch size does
    monkeypatch.setattr(settings, "trans_thread", 5)
    items = [SrtItem(text=f"line {i}", line=i) for i in range(1, len(expected) + 1)]

    result = Google(
        text_list=items, source_code="zh-cn", target_code=target_code, wait_sec=0
    ).run()

    assert [it["text"] for it in result] == expected
