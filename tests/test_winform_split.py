import pytest
from videotrans.winform import _module_map, get_win

KNOWN_MISSING = {"qwenasrlocal", "mitts"}


def test_helpers_importable():
    from videotrans.winform._helpers import make_feed_translator, make_feed_stt, make_feed_tts, make_setallmodels
    assert callable(make_feed_translator)
    assert callable(make_feed_stt)
    assert callable(make_feed_tts)
    assert callable(make_setallmodels)


def test_all_winform_modules_importable():
    failed = []
    for name in _module_map:
        if name in KNOWN_MISSING:
            continue
        try:
            mod = get_win(name)
            assert hasattr(mod, 'openwin'), f"{name} module has no openwin()"
        except Exception as e:
            failed.append((name, str(e)))
    if failed:
        msg = "\n".join(f"  {n}: {e}" for n, e in failed)
        pytest.fail(f"Failed imports:\n{msg}")


def test_each_channel_has_openwin():
    for name in _module_map:
        if name in KNOWN_MISSING:
            continue
        mod = get_win(name)
        assert callable(mod.openwin), f"{name}.openwin is not callable"


def test_registered_module_count():
    assert len(_module_map) >= 60


def test_helpers_factory_returns_callable():
    from videotrans.winform._helpers import make_setallmodels
    mock_form = type('MockForm', (), {
        'edit_allmodels': type('W', (), {'toPlainText': lambda self: 'm1,m2'})()
    })()
    fn = make_setallmodels(mock_form, 'model_widget', 'settings_key')
    assert callable(fn)
