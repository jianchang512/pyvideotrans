import pytest

from videotrans.util.en_tn import EnglishNormalizer


@pytest.mark.parametrize(
    "text, expected",
    [
        ("\u20ac1", "one euro"),
        ("\u20ac20", "twenty euros"),
        ("\u20ac0", "zero euros"),
        ("\u20ac0.01", "one cent"),
        ("\u20ac.01", "one cent"),
        ("\u20ac0.5", "fifty cents"),
        ("\u20ac5.50", "five euros, fifty cents"),
        ("\u20ac1.01", "one euro, one cent"),
        ("\u20ac1,000", "one thousand euros"),
        ("\u20ac1,500", "fifteen hundred euros"),
        ("\u20ac1,50", "one euro, fifty cents"),
        ("\u20ac1\u00a0000", "one thousand euros"),
        ("\u20ac1\u202f000", "one thousand euros"),
        ("\u20ac2.5m", "two point five million euros"),
        ("\u20ac20k", "twenty thousand euros"),
        ("\u20ac3.5bn", "three point five billion euros"),
        ("\u20ac2 million", "two million euros"),
        ("\u20ac1.999", "one point nine nine nine euros"),
        ("1\u20ac", "one euro"),
        ("20 \u20ac", "twenty euros"),
        ("20\u00a0\u20ac", "twenty euros"),
        ("20\u202f\u20ac", "twenty euros"),
        ("0\u20ac", "zero euros"),
        ("0.01\u20ac", "one cent"),
        (".01\u20ac", "one cent"),
        ("0.5\u20ac", "fifty cents"),
        ("5.50\u20ac", "five euros, fifty cents"),
        ("1.01\u20ac", "one euro, one cent"),
        ("1,000\u20ac", "one thousand euros"),
        ("1,500 \u20ac", "fifteen hundred euros"),
        ("12,50 \u20ac", "twelve euros, fifty cents"),
        ("1,5\u20ac", "one euro, fifty cents"),
        ("1 000 \u20ac", "one thousand euros"),
        ("10 000 \u20ac", "ten thousand euros"),
        ("1 000,50 \u20ac", "one thousand euros, fifty cents"),
        ("1 000.50 \u20ac", "one thousand euros, fifty cents"),
        ("1\u00a0000\u00a0\u20ac", "one thousand euros"),
        ("1.999\u20ac", "one point nine nine nine euros"),
        ("\u20ac5\u00a0each", "five euros each"),
        ("5\u20ac\u202feach", "five euros each"),
        ("It costs \u20ac5 a month.", "it costs five euros a month."),
        ("I paid 3 times 100 \u20ac", "i paid three times one hundred euros"),
        (
            "in 2024 100 \u20ac was a lot",
            "in two thousand, twenty-four one hundred euros was a lot",
        ),
    ],
)
def test_euros_are_spoken_correctly(text, expected):
    assert EnglishNormalizer()(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("100%", "one hundred percent"),
        ("50 %", "fifty percent"),
        ("2.5%", "two point five percent"),
        (".5%", "zero point five percent"),
        ("1,000%", "one thousand percent"),
        ("0%", "zero percent"),
        ("100%.", "one hundred percent."),
        ("50%off", "fifty percent off"),
        ("%", "%"),
    ],
)
def test_percentages_are_spoken_correctly(text, expected):
    assert EnglishNormalizer()(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("\u00a31", "one pound"),
        ("\u00a35.50", "five pounds, fifty pence"),
        ("\u00a31,50", "one hundred fifty pounds"),
        ("\u00a31,500", "fifteen hundred pounds"),
        ("$1.50", "one dollar, fifty cents"),
        ("$0.01", "one cent"),
    ],
)
def test_other_currencies_are_unchanged(text, expected):
    assert EnglishNormalizer()(text) == expected


def test_normalize_numbers_expands_euros_and_percentages_directly():
    normalizer = EnglishNormalizer()

    assert normalizer.normalize_numbers("\u20ac5.50") == "five euros, fifty cents"
    assert normalizer.normalize_numbers("\u20ac1,50") == "one euro, fifty cents"
    assert (
        normalizer.normalize_numbers("1 000,50 \u20ac")
        == "one thousand euros, fifty cents"
    )
    assert normalizer.normalize_numbers("\u20ac2.5m") == "two point five million euros"
    assert normalizer.normalize_numbers("20\u00a0\u20ac") == "twenty euros"
    assert normalizer.normalize_numbers("2.5%") == "two point five percent"
