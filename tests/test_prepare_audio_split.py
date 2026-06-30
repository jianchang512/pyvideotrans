import inspect
import pytest
import tempfile
from pathlib import Path


class TestPrepareAudioImports:
    def test_vocal_bgm_importable(self):
        from videotrans.process.prepare_audio import vocal_bgm
        assert callable(vocal_bgm)

    def test_vocal_bgm_spleeter_importable(self):
        from videotrans.process.prepare_audio import vocal_bgm_spleeter
        assert callable(vocal_bgm_spleeter)

    def test_remove_noise_importable(self):
        from videotrans.process.prepare_audio import remove_noise
        assert callable(remove_noise)

    def test_fix_punc_importable(self):
        from videotrans.process.prepare_audio import fix_punc
        assert callable(fix_punc)

    def test_cam_speakers_importable(self):
        from videotrans.process.prepare_audio import cam_speakers
        assert callable(cam_speakers)

    def test_pyannote_speakers_importable(self):
        from videotrans.process.prepare_audio import pyannote_speakers
        assert callable(pyannote_speakers)

    def test_reverb_speakers_importable(self):
        from videotrans.process.prepare_audio import reverb_speakers
        assert callable(reverb_speakers)

    def test_built_speakers_importable(self):
        from videotrans.process.prepare_audio import built_speakers
        assert callable(built_speakers)

    def test_write_log_importable(self):
        from videotrans.process.prepare_audio import _write_log
        assert callable(_write_log)

    def test_all_9_names_importable(self):
        from videotrans.process import prepare_audio
        for name in ['vocal_bgm', 'vocal_bgm_spleeter', 'remove_noise', 'fix_punc',
                      'cam_speakers', 'pyannote_speakers', 'reverb_speakers', 'built_speakers',
                      '_write_log']:
            assert hasattr(prepare_audio, name), f"Missing: {name}"


class TestFunctionSignatures:
    def test_vocal_bgm_signature(self):
        from videotrans.process.prepare_audio import vocal_bgm
        sig = inspect.signature(vocal_bgm)
        params = list(sig.parameters.keys())
        assert 'input_file' in params
        assert 'vocal_file' in params
        assert 'instr_file' in params
        assert 'logs_file' in params
        assert 'is_cuda' in params
        assert 'uvr_models' in params

    def test_remove_noise_signature(self):
        from videotrans.process.prepare_audio import remove_noise
        sig = inspect.signature(remove_noise)
        params = list(sig.parameters.keys())
        assert 'input_file' in params
        assert 'output_file' in params
        assert 'is_cuda' in params
        assert 'logs_file' in params
        assert 'device_index' in params

    def test_fix_punc_signature(self):
        from videotrans.process.prepare_audio import fix_punc
        sig = inspect.signature(fix_punc)
        params = list(sig.parameters.keys())
        assert 'text_dict_file' in params
        assert 'is_cuda' in params
        assert 'logs_file' in params

    def test_cam_speakers_signature(self):
        from videotrans.process.prepare_audio import cam_speakers
        sig = inspect.signature(cam_speakers)
        params = list(sig.parameters.keys())
        assert 'input_file' in params
        assert 'subtitles_file' in params
        assert 'speak_file' in params
        assert 'num_speakers' in params

    def test_built_speakers_signature(self):
        from videotrans.process.prepare_audio import built_speakers
        sig = inspect.signature(built_speakers)
        params = list(sig.parameters.keys())
        assert 'input_file' in params
        assert 'language' in params
        assert 'num_speakers' in params


class TestAssignSpeakers:
    def test_assign_empty_diarizations(self):
        from videotrans.process._audio_speakers import _assign_speakers
        result = _assign_speakers([[1000, 2000]], [])
        assert result == ["spk0"]

    def test_assign_single_speaker_overlap(self):
        from videotrans.process._audio_speakers import _assign_speakers
        diarizations = [[[500, 2500], "spk0"]]
        result = _assign_speakers([[1000, 2000]], diarizations)
        assert result == ["spk0"]

    def test_assign_no_overlap(self):
        from videotrans.process._audio_speakers import _assign_speakers
        diarizations = [[[0, 500], "spk0"], [[3000, 4000], "spk1"]]
        result = _assign_speakers([[1000, 2000]], diarizations)
        assert result == ["spk0"]

    def test_assign_two_speakers_majority(self):
        from videotrans.process._audio_speakers import _assign_speakers
        diarizations = [[[0, 1500], "spk0"], [[1500, 3000], "spk1"]]
        result = _assign_speakers([[500, 2000]], diarizations)
        assert result == ["spk0"]

    def test_assign_invalid_subtitle(self):
        from videotrans.process._audio_speakers import _assign_speakers
        result = _assign_speakers([[500, 200]], [])
        assert result == ["spk0"]


class TestNormalizeDiarizations:
    def test_normalizes_and_remaps(self):
        from videotrans.process._audio_speakers import _normalize_diarizations
        raw = [
            {'start': 0.0, 'end': 1.0, 'speaker': 'spk5'},
            {'start': 2.0, 'end': 3.0, 'speaker': 'spk3'},
        ]
        result = _normalize_diarizations(raw)
        assert len(result) == 2
        assert result[0]['times'] == [0, 1000]
        assert result[1]['times'] == [2000, 3000]
        speakers = {d['speaker'] for d in result}
        assert speakers == {'spk0', 'spk1'}


class TestWriteLog:
    def test_writes_to_file(self, tmp_path):
        from videotrans.process.prepare_audio import _write_log
        log_file = str(tmp_path / "test.log")
        _write_log(log_file, "test message")
        content = Path(log_file).read_text(encoding='utf-8')
        assert "test message" in content

    def test_noop_on_none(self):
        from videotrans.process.prepare_audio import _write_log
        _write_log(None, None)
