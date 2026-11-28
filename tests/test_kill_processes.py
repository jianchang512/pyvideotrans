import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, call


def test_windows_kills_every_process(monkeypatch):
    # Avoid importing the app configuration and its startup side effects.
    config = ModuleType("videotrans.configure.config")
    config.logger = Mock()
    config.TEMP_ROOT = ""
    config.app_cfg = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "videotrans.configure.config", config)
    path = Path(__file__).resolve().parents[1] / "videotrans/task/clean_life.py"
    spec = importlib.util.spec_from_file_location("clean_life", path)
    clean_life = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(clean_life)

    monkeypatch.setattr(clean_life, "_os", "Windows")
    monkeypatch.setattr(clean_life.getpass, "getuser", lambda: "test-user")
    run = Mock(return_value=SimpleNamespace(returncode=0))
    monkeypatch.setattr(clean_life.subprocess, "run", run)

    names = ["ffmpeg", "audiocpp_cli", "audiocpp_server"]
    clean_life.kill_processes(names)

    assert run.call_args_list == [
        call(
            f'taskkill /F /FI "USERNAME eq test-user" /IM {name}.exe',
            shell=True,
            capture_output=True,
            text=True,
        )
        for name in names
    ]
