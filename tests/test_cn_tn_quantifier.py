import runpy
from pathlib import Path

import pytest


cn_tn = runpy.run_path(str(Path(__file__).resolve().parents[1] / "videotrans/util/cn_tn.py"))


@pytest.mark.parametrize(
    "text, expected",
    [
        ("100和1个", "一百和一个"),
        ("拿3个", "拿三个"),
        ("拿3多个、4余个、5几个", "拿三多个、四余个、五几个"),
        ("拿3.5个", "拿三点五个"),
    ],
)
def test_quantifier_normalizes_only_the_matched_number(text, expected):
    assert cn_tn["normalize_nsw"](text) == expected


def test_quantifier_in_a_sentence():
    assert cn_tn["TextNorm"](to_banjiao=True)("总共21，拿1个。") == "总共二十一,拿一个。"
