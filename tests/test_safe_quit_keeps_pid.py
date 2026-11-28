from types import SimpleNamespace

from videotrans.configure import _paths, config
from videotrans.task import clean_life


def test_safe_quit_keeps_pid(monkeypatch, tmp_path):
    pid_file = tmp_path / "a.pid"
    json_file = tmp_path / "b.json"
    pid_file.write_text("status")
    json_file.write_text("{}")

    redubb_status = tmp_path / "stopredubbing.pid"
    ipc_status = tmp_path / "exit.pid"
    monkeypatch.setattr(clean_life, "TEMP_ROOT", tmp_path)
    monkeypatch.setattr(clean_life, "app_cfg", SimpleNamespace())
    monkeypatch.setattr(clean_life, "kill_processes", lambda names: None)
    monkeypatch.setattr(config, "TEMP_DIR", tmp_path / "instance")
    monkeypatch.setattr(config, "AUDIO_SERVER_CFG", None)
    monkeypatch.setattr(_paths, "REDUBB_STATUS_FILE", redubb_status)
    monkeypatch.setattr(_paths, "IPC_STATUS_FILE", ipc_status)

    clean_life.safe_quit()

    assert pid_file.read_text() == "status"
    assert not json_file.exists()
    assert redubb_status.is_file()
    assert ipc_status.is_file()
