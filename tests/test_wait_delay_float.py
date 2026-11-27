import pytest

from videotrans.configure._app_settings import AppSettings


@pytest.mark.parametrize(
    "key, value", [("translation_wait", 0.1), ("dubbing_wait", 1.5)]
)
def test_wait_delay_keeps_fractional_seconds(key, value):
    # Skip initialization so this test doesn't read or write cfg.json.
    settings = object.__new__(AppSettings)
    settings[key] = value

    assert settings.get(key) == value
