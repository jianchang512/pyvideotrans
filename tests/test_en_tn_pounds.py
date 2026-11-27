import pytest

from videotrans.util.en_tn import EnglishNormalizer


@pytest.mark.parametrize(
    "text, expected",
    [
        ("\u00a31", "one pound"),
        ("\u00a320", "twenty pounds"),
        ("\u00a30", "zero pounds"),
        ("\u00a30.01", "one penny"),
        ("\u00a3.01", "one penny"),
        ("\u00a30.5", "fifty pence"),
        ("\u00a35.50", "five pounds, fifty pence"),
        ("\u00a31.01", "one pound, one penny"),
        ("\u00a31,000", "one thousand pounds"),
        ("\u00a31,000,000", "one million pounds"),
        ("\u00a32.5m", "two point five million pounds"),
        ("\u00a32.5M", "two point five million pounds"),
        ("\u00a32.5 million", "two point five million pounds"),
        ("\u00a320k", "twenty thousand pounds"),
        ("\u00a33.5bn", "three point five billion pounds"),
        ("\u00a32 thousand", "two thousand pounds"),
        ("\u00a34 billion", "four billion pounds"),
        ("\u00a31.25 trillion", "one point two five trillion pounds"),
        ("\u00a31 million", "one million pounds"),
        ("\u00a35 more", "five pounds more"),
        ("\u00a31.999", "one point nine nine nine pounds"),
        ("\u00a3.5m", "zero point five million pounds"),
        ("\u00a3.999", "zero point nine nine nine pounds"),
        ("\u00a31\u00a0000", "one thousand pounds"),
        ("\u00a31\u202f000", "one thousand pounds"),
        ("\u00a35\u00a0each", "five pounds each"),
        ("\u00a35 million\u00a0each", "five million pounds each"),
        ("\u00a35m\u00a0each", "five million pounds each"),
        ("It costs \u00a320.", "it costs twenty pounds."),
        ("Pay \u00a320, then go", "pay twenty pounds, then go"),
        ("\u00a35.50 each", "five pounds, fifty pence each"),
        ("$1.50", "one dollar, fifty cents"),
        ("$0.01", "one cent"),
        ("$1,000.50", "one thousand dollars, fifty cents"),
        ("$1.,.50", "one.,.fifty dollars"),
        ("$5\u00a0each", "five dollarseach"),
        ("3.05", "three point zero five"),
        ("1\u00a0000", "one thousand"),
        ("1ST Dr. Smith", "first doctor smith"),
    ],
)
def test_pounds_are_spoken_correctly(text, expected):
    assert EnglishNormalizer()(text) == expected


def test_normalize_numbers_expands_pounds_directly():
    normalizer = EnglishNormalizer()

    assert normalizer.normalize_numbers("\u00a35.50") == "five pounds, fifty pence"
    assert normalizer.normalize_numbers("\u00a32.5m") == "two point five million pounds"
    assert normalizer.normalize_numbers("\u00a31\u202f000") == "one thousand pounds"
