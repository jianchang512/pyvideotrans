import pytest

from videotrans.util.en_tn import EnglishNormalizer


@pytest.mark.parametrize(
    "text, expected",
    [
        ("0.001", "zero point zero zero one"),
        ("3.05", "three point zero five"),
        ("3.14", "three point one four"),
        ("$1.5", "one dollar, fifty cents"),
        ("$1.05", "one dollar, five cents"),
        ("$1.50", "one dollar, fifty cents"),
        ("0", "zero"),
        ("14", "fourteen"),
        ("42", "forty-two"),
        ("$2", "two dollars"),
    ],
)
def test_decimals_and_dollars_are_spoken_correctly(text, expected):
    assert EnglishNormalizer()(text) == expected
