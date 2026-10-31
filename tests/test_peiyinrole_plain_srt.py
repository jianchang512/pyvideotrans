from unittest.mock import MagicMock

import pytest

from videotrans.ui import fn_peiyinrole
from videotrans.ui.fn_peiyinrole import Ui_fn_peiyinrole


def _import_srt(monkeypatch, tmp_path, texts):
    srt = tmp_path / "demo.srt"
    srt.write_text(
        "\n".join(
            f"{i}\n00:00:0{i - 1},000 --> 00:00:0{i},000\n{text}\n"
            for i, text in enumerate(texts, start=1)
        ),
        encoding="utf-8",
    )
    # a real QWidget, which can't be created without a QApplication
    monkeypatch.setattr(fn_peiyinrole, "SpkRowWidget", MagicMock())
    # stands in for the window: besides calling methods of its widgets,
    # parse_and_display_srt() fills these two dicts and sets .subtitles
    win = MagicMock(spk_role={}, spk_lines={})
    # as hecheng_import_fun() calls it when an .srt file is imported
    Ui_fn_peiyinrole.parse_and_display_srt(win, srt.as_posix(), None)
    return win


@pytest.mark.parametrize(
    "texts",
    [
        ["Hello there.", "How are you?"],
        ["Hello there.", "How are you?", "Fine, thanks."],
        # too few tagged lines: the file is read as one without speakers
        ["[Tom]Hello there.", "How are you?", "Fine, thanks."],
    ],
)
def test_srt_without_speaker_tags_is_imported(monkeypatch, tmp_path, texts):
    win = _import_srt(monkeypatch, tmp_path, texts)

    assert [sub["text"] for sub in win.subtitles] == texts
    assert win.spk_role == {}
    assert win.spk_lines == {}


def test_speaker_tags_are_read_and_removed(monkeypatch, tmp_path):
    texts = ["[Tom]Hello there.", "[Ann]How are you?", "[Tom]Fine, thanks."]

    win = _import_srt(monkeypatch, tmp_path, texts)

    assert [sub["text"] for sub in win.subtitles] == [
        "Hello there.",
        "How are you?",
        "Fine, thanks.",
    ]
    assert list(win.spk_role) == ["Tom", "Ann"]
    assert win.spk_lines == {"Tom": [1, 3], "Ann": [2]}
