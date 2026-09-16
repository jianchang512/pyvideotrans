"""LibreTranslate target-language support check.

`get_source_target_code()` reads the LibreTranslate column (index 5) of
LANG_CODE, so `is_allow_translate()` has to read the same column when it
decides whether the channel can reach the chosen target language.
"""

import pytest

from videotrans.configure._languages_dict import LANG_CODE
from videotrans.translator import is_allow_translate, get_source_target_code
from videotrans.translator._constants import LIBRE_INDEX

LIBRE_COLUMN = 5

# Languages Google can translate into but LibreTranslate cannot.
UNSUPPORTED = sorted(
    code for code, row in LANG_CODE.items()
    if row[LIBRE_COLUMN] == 'No' and row[0] != 'No'
)


@pytest.fixture(autouse=True)
def _libre_configured(monkeypatch):
    from videotrans.configure.config import params
    monkeypatch.setitem(params, 'libre_address', 'http://127.0.0.1:5000')
    monkeypatch.setitem(params, 'libre_key', 'x')


def test_unsupported_list_is_not_empty():
    assert UNSUPPORTED, 'LANG_CODE no longer marks any language No for LibreTranslate'


@pytest.mark.parametrize('code', UNSUPPORTED)
def test_unsupported_target_is_reported(code):
    # the channel really would be asked for the literal string "No"
    _, target_code = get_source_target_code(show_target=code, translate_type=LIBRE_INDEX)
    assert target_code == 'No'
    # so the check must refuse it instead of returning True
    assert is_allow_translate(translate_type=LIBRE_INDEX, show_target=code) is not True


@pytest.mark.parametrize('code', ['en', 'zh-cn', 'fr'])
def test_supported_target_is_allowed(code):
    assert LANG_CODE[code][LIBRE_COLUMN] != 'No'
    assert is_allow_translate(translate_type=LIBRE_INDEX, show_target=code) is True
