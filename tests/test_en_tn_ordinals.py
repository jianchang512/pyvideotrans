import pytest

from videotrans.util.en_tn import EnglishNormalizer


@pytest.mark.parametrize(
    "text, expected",
    [
        ("1st", "first"),
        ("2nd", "second"),
        ("3rd", "third"),
        ("4th", "fourth"),
        ("5th", "fifth"),
        ("8th", "eighth"),
        ("9th", "ninth"),
        ("11th", "eleventh"),
        ("12th", "twelfth"),
        ("13th", "thirteenth"),
        ("20th", "twentieth"),
        ("21st", "twenty-first"),
        ("42nd", "forty-second"),
        ("100th", "one hundredth"),
        ("101st", "one hundred first"),
        ("1,000th", "one thousandth"),
    ],
)
def test_ordinals_are_spoken_as_ordinal_words(text, expected):
    assert EnglishNormalizer()(text) == expected


def test_ordinal_in_a_sentence():
    assert EnglishNormalizer()("The 1st and 22nd of May.") == "the first and twenty-second of may."
