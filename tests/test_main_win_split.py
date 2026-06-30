"""Tests for the split main_win mixin modules."""
import importlib


def test_mixin_modules_importable():
    mod = importlib.import_module("videotrans.mainwin._bind_signals")
    assert hasattr(mod, "BindSignalsMixin")

    mod = importlib.import_module("videotrans.mainwin._winform")
    assert hasattr(mod, "WinformMixin")

    mod = importlib.import_module("videotrans.mainwin._lifecycle")
    assert hasattr(mod, "LifecycleMixin")


def test_main_win_importable():
    mod = importlib.import_module("videotrans.mainwin.main_win")
    assert hasattr(mod, "MainWindow")


def test_main_win_class_hierarchy():
    from videotrans.mainwin.main_win import MainWindow
    from videotrans.mainwin._bind_signals import BindSignalsMixin
    from videotrans.mainwin._winform import WinformMixin
    from videotrans.mainwin._lifecycle import LifecycleMixin

    assert issubclass(MainWindow, BindSignalsMixin)
    assert issubclass(MainWindow, WinformMixin)
    assert issubclass(MainWindow, LifecycleMixin)


def test_main_win_has_expected_methods():
    from videotrans.mainwin.main_win import MainWindow

    for method in (
        "__init__",
        "_set_default",
        "_start_workers",
        "_daemon",
        "checkbox_state_changed",
        "changeEvent",
        "_bind_signal",
        "open_winform",
        "restart_app",
        "closeEvent",
        "cleanup_and_accept",
        "kill_ffmpeg_processes",
    ):
        assert hasattr(MainWindow, method), f"MainWindow missing {method}"


def test_main_win_package_importable():
    """The mainwin package itself should be importable without errors."""
    import videotrans.mainwin
    assert videotrans.mainwin is not None
