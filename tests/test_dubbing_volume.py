import shutil

import pytest

# not just "pydub": conftest puts a mock in its place when it isn't installed
pytest.importorskip("pydub.generators")

from pydub import AudioSegment
from pydub.generators import Sine

from videotrans import tts
from videotrans.configure.config import app_cfg
from videotrans.task.dubbing import DubbingSrt
from videotrans.task.taskcfg import TaskCfgTTS


@pytest.fixture(autouse=True)
def _cli_mode(monkeypatch):
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    # task_done() adds the finished task to this global set
    monkeypatch.setattr(app_cfg, "stoped_uuid_set", set())


def _dub(tmp_path, tts_type, volume):
    trk = DubbingSrt(
        cfg=TaskCfgTTS(
            name=(tmp_path / "demo.srt").as_posix(),
            noextname="demo",
            target_dir=(tmp_path / "out").as_posix(),
            cache_folder=(tmp_path / "cache").as_posix(),
            tts_type=tts_type,
            volume=volume,
        )
    )
    # as dubbing() leaves it: a 1 s 48 kHz stereo wav per line in the cache folder
    tone = Sine(440, sample_rate=48000).to_audio_segment(duration=1000, volume=-20)
    tone = tone.set_channels(2)
    for i in range(2):
        wav = f"{trk.cfg.cache_folder}/dubb-{i}.wav"
        tone.export(wav, format="wav")
        trk.queue_tts.append(
            {
                "line": i + 1,
                "text": f"line {i + 1}",
                "start_time": i * 1000,
                "end_time": i * 1000 + 1000,
                "filename": wav,
            }
        )
    trk.align()
    trk.task_done()
    return tone, AudioSegment.from_file((tmp_path / "out" / "demo.wav").as_posix())


# OpenAI TTS has no volume setting, so align() applies the volume with ffmpeg
@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not found")
@pytest.mark.parametrize("volume, gain_db", [("+100%", 6.0), ("-50%", -6.0)])
def test_volume_is_applied_to_the_exported_wav(tmp_path, volume, gain_db):
    tone, out = _dub(tmp_path, tts.OPENAI_TTS, volume)
    assert out.dBFS == pytest.approx(tone.dBFS + gain_db, abs=0.1)


# Azure TTS is in SUPPORT_VOLUME: the wav it returns already has the volume
@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not found")
def test_volume_is_not_applied_twice(tmp_path):
    tone, out = _dub(tmp_path, tts.AZURE_TTS, "+100%")
    assert out.dBFS == pytest.approx(tone.dBFS, abs=0.1)
