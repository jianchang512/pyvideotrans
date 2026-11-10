import json
import shutil
from pathlib import Path

import pytest

from videotrans.configure.constants import DEFAULT_STYLE
from videotrans.util import _srt_ass

# a subtitle as _process_subtitles() writes it for "Hard Subtitles (Bilingual)"
# when the bottom language has a style of its own: the line of the bottom
# language starts with '###', and set_ass_font() gives it the Bottom style
SRT = "1\n00:00:01,000 --> 00:00:03,500\nHello there, friend.\n###你好，朋友。\n"

needs_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not found"
)


def convert(tmp_path, monkeypatch, style):
    """Saves the style to ass.json, as the style editors do, and converts the
    subtitle with set_ass_font(), which runs ffmpeg. Returns the .ass file"""
    (tmp_path / "videotrans").mkdir()
    (tmp_path / "videotrans" / "ass.json").write_text(
        json.dumps(style, indent=4), encoding="utf-8"
    )
    monkeypatch.setattr(_srt_ass, "ROOT_DIR", tmp_path.as_posix())
    srt = tmp_path / "shuang.srt"
    srt.write_text(SRT, encoding="utf-8")
    ass = _srt_ass.set_ass_font(srt.as_posix())
    return Path(ass).read_text(encoding="utf-8")


def styles(ass):
    """The fields of each style of the .ass file, by name: the font is the
    second field and the size the third"""
    found = {}
    for line in ass.splitlines():
        if line.startswith("Style:"):
            fields = line[len("Style:") :].strip().split(",")
            found[fields[0]] = fields
    return found


@needs_ffmpeg
def test_bottom_language_is_drawn_in_its_own_font(tmp_path, monkeypatch):
    style = dict(
        DEFAULT_STYLE, Fontname="Arial", Bottom_Fontname="SimHei", Bottom_Fontsize=20
    )

    ass = convert(tmp_path, monkeypatch, style)

    found = styles(ass)
    fonts = {name: fields[1] for name, fields in found.items()}
    assert fonts == {"Default": "Arial", "Bottom": "SimHei"}
    # the size of the bottom language is still its own
    assert found["Bottom"][2] == "20"
    # the second line is still drawn with the Bottom style
    dialogues = [line for line in ass.splitlines() if line.startswith("Dialogue:")]
    assert len(dialogues) == 1
    assert dialogues[0].endswith(r",Hello there, friend.\N{\rBottom}你好，朋友。{\r}")


@needs_ffmpeg
@pytest.mark.parametrize("bottom_font", [None, ""], ids=["missing", "empty"])
def test_bottom_language_without_a_font_uses_the_main_font(
    tmp_path, monkeypatch, bottom_font
):
    # an ass.json without the bottom font, or with an empty one. The main font
    # isn't Arial, the font set_ass_font() uses when ass.json has none
    style = dict(DEFAULT_STYLE, Fontname="SimHei", Bottom_Fontsize=20)
    if bottom_font is None:
        del style["Bottom_Fontname"]
    else:
        style["Bottom_Fontname"] = bottom_font

    ass = convert(tmp_path, monkeypatch, style)

    fonts = {name: fields[1] for name, fields in styles(ass).items()}
    assert fonts == {"Default": "SimHei", "Bottom": "SimHei"}
