import inspect
import pytest
from pathlib import Path


class TestHelpFfmpegImports:
    """All names from the original help_ffmpeg.py must be importable."""

    def test_runffmpeg(self):
        from videotrans.util.help_ffmpeg import runffmpeg
        assert callable(runffmpeg)

    def test_extract_concise_error(self):
        from videotrans.util.help_ffmpeg import extract_concise_error
        assert callable(extract_concise_error)

    def test_get_filepath_from_cmd(self):
        from videotrans.util.help_ffmpeg import get_filepath_from_cmd
        assert callable(get_filepath_from_cmd)

    def test_runffprobe(self):
        from videotrans.util.help_ffmpeg import runffprobe
        assert callable(runffprobe)

    def test_get_video_info(self):
        from videotrans.util.help_ffmpeg import get_video_info
        assert callable(get_video_info)

    def test_get_video_duration(self):
        from videotrans.util.help_ffmpeg import get_video_duration
        assert callable(get_video_duration)

    def test_get_audio_time(self):
        from videotrans.util.help_ffmpeg import get_audio_time
        assert callable(get_audio_time)

    def test_get_video_ms_noaudio(self):
        from videotrans.util.help_ffmpeg import get_video_ms_noaudio
        assert callable(get_video_ms_noaudio)

    def test_conver_to_16k(self):
        from videotrans.util.help_ffmpeg import conver_to_16k
        assert callable(conver_to_16k)

    def test_create_concat_txt(self):
        from videotrans.util.help_ffmpeg import create_concat_txt
        assert callable(create_concat_txt)

    def test_concat_multi_audio(self):
        from videotrans.util.help_ffmpeg import concat_multi_audio
        assert callable(concat_multi_audio)

    def test_change_speed_rubberband(self):
        from videotrans.util.help_ffmpeg import change_speed_rubberband
        assert callable(change_speed_rubberband)

    def test_precise_speed_up_audio(self):
        from videotrans.util.help_ffmpeg import precise_speed_up_audio
        assert callable(precise_speed_up_audio)

    def test_cut_from_audio(self):
        from videotrans.util.help_ffmpeg import cut_from_audio
        assert callable(cut_from_audio)

    def test_remove_silence_wav(self):
        from videotrans.util.help_ffmpeg import remove_silence_wav
        assert callable(remove_silence_wav)

    def test_check_hw_on_start(self):
        from videotrans.util.help_ffmpeg import check_hw_on_start
        assert callable(check_hw_on_start)

    def test_get_video_codec(self):
        from videotrans.util.help_ffmpeg import get_video_codec
        assert callable(get_video_codec)

    def test_send_notification(self):
        from videotrans.util.help_ffmpeg import send_notification
        assert callable(send_notification)

    def test_format_video(self):
        from videotrans.util.help_ffmpeg import format_video
        assert callable(format_video)

    def test_all_names_importable(self):
        from videotrans.util import help_ffmpeg
        expected = [
            'runffmpeg', 'extract_concise_error', 'get_filepath_from_cmd',
            'runffprobe', 'get_video_info', 'get_video_duration', 'get_audio_time',
            'get_video_ms_noaudio', 'conver_to_16k', 'create_concat_txt',
            'concat_multi_audio', 'change_speed_rubberband', 'precise_speed_up_audio',
            'cut_from_audio', 'remove_silence_wav', 'check_hw_on_start',
            'get_video_codec', 'send_notification', 'format_video',
        ]
        for name in expected:
            assert hasattr(help_ffmpeg, name), f"Missing: {name}"


class TestFunctionSignatures:
    def test_runffmpeg_sig(self):
        from videotrans.util.help_ffmpeg import runffmpeg
        sig = inspect.signature(runffmpeg)
        params = list(sig.parameters.keys())
        assert 'noextname' in params
        assert 'force_cpu' in params
        assert 'cmd_dir' in params

    def test_get_video_info_sig(self):
        from videotrans.util.help_ffmpeg import get_video_info
        sig = inspect.signature(get_video_info)
        params = list(sig.parameters.keys())
        assert 'mp4_file' in params
        assert 'video_fps' in params
        assert 'video_scale' in params
        assert 'video_time' in params

    def test_format_video_sig(self):
        from videotrans.util.help_ffmpeg import format_video
        sig = inspect.signature(format_video)
        params = list(sig.parameters.keys())
        assert 'name' in params
        assert 'target_dir' in params


class TestExtractConciseError:
    def test_empty_string(self):
        from videotrans.util.help_ffmpeg import extract_concise_error
        result = extract_concise_error("")
        assert "empty stderr" in result.lower()

    def test_none(self):
        from videotrans.util.help_ffmpeg import extract_concise_error
        result = extract_concise_error(None)
        assert "empty stderr" in result.lower()

    def test_with_error_lines(self):
        from videotrans.util.help_ffmpeg import extract_concise_error
        result = extract_concise_error("Error some specific problem\nline2\nline3")
        assert "some specific problem" in result

    def test_no_error_pattern(self):
        from videotrans.util.help_ffmpeg import extract_concise_error
        result = extract_concise_error("line1\nline2\nline3")
        assert "line1" in result


class TestGetFilepathFromCmd:
    def test_long_path(self):
        from videotrans.util.help_ffmpeg import get_filepath_from_cmd
        long_path = "a" * 260
        cmd = ["ffmpeg", "-i", long_path, "output.mp4"]
        result = get_filepath_from_cmd(cmd)
        assert result is not None

    def test_special_chars(self):
        from videotrans.util.help_ffmpeg import get_filepath_from_cmd
        cmd = ["ffmpeg", "-i", "test?.mp4", "output.mp4"]
        result = get_filepath_from_cmd(cmd)
        assert result is not None

    def test_clean_path(self):
        from videotrans.util.help_ffmpeg import get_filepath_from_cmd
        cmd = ["ffmpeg", "-i", "normal.mp4", "output.mp4"]
        result = get_filepath_from_cmd(cmd)
        assert result is None


class TestFormatVideo:
    def test_format_video_returns_input_file(self, tmp_path):
        from videotrans.util.help_ffmpeg import format_video
        test_file = tmp_path / "test.mp4"
        test_file.write_text("fake video content")
        result = format_video(str(test_file))
        assert result.basename == "test.mp4"
        assert result.ext == "mp4"
        assert result.noextname == "test"
        assert result.uuid is not None
        assert len(result.uuid) == 10

    def test_format_video_with_target_dir(self, tmp_path):
        from videotrans.util.help_ffmpeg import format_video
        test_file = tmp_path / "test.mp4"
        test_file.write_text("fake video content")
        target = str(tmp_path / "output")
        result = format_video(str(test_file), target_dir=target)
        assert "test-mp4" in result.target_dir


class TestCreateConcatTxt:
    def test_empty_list_raises(self):
        from videotrans.util.help_ffmpeg import create_concat_txt
        with pytest.raises(RuntimeError):
            create_concat_txt([], "dummy.txt")
