from videotrans.util import _ffmpeg_runner


class _CancelledProcess:
    returncode = None

    def __init__(self):
        self.killed = False

    def poll(self):
        return None

    def kill(self):
        self.killed = True
        self.returncode = -9

    def communicate(self):
        return "", ""


class _CompletedProcess:
    returncode = 0

    def poll(self):
        return 0

    def communicate(self, timeout=None):
        return "", ""


def test_runffmpeg_stops_process_when_cancelled(monkeypatch):
    process = _CancelledProcess()
    monkeypatch.setattr(_ffmpeg_runner.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(_ffmpeg_runner.app_cfg, "exit_soft", False)

    result = _ffmpeg_runner.runffmpeg(
        ["-i", "input.mp4", "output.mp4"], state_dict={"stop": True}
    )

    assert result is False
    assert process.killed is True


def test_runffmpeg_uses_cancellable_process_path(monkeypatch):
    process = _CompletedProcess()
    monkeypatch.setattr(_ffmpeg_runner.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(_ffmpeg_runner.app_cfg, "exit_soft", False)

    result = _ffmpeg_runner.runffmpeg(
        ["-i", "input.mp4", "output.mp4"], state_dict={"stop": False}
    )

    assert result is True
