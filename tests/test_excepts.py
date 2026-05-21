from videotrans.configure.excepts import (
    VideoTransError,
    TranslateSrtError,
    DubbingSrtError,
    SpeechToTextError,
    LLMSegmentError,
    FFmpegError,
    StopTask,
    StopRetry,
    NO_RETRY_EXCEPT,
    get_msg_from_except,
)


class TestExceptionHierarchy:
    def test_videotrans_error_is_exception(self):
        assert issubclass(VideoTransError, Exception)

    def test_translate_srt_error_inherits(self):
        assert issubclass(TranslateSrtError, VideoTransError)

    def test_dubbing_srt_error_inherits(self):
        assert issubclass(DubbingSrtError, VideoTransError)

    def test_speech_to_text_error_inherits(self):
        assert issubclass(SpeechToTextError, VideoTransError)

    def test_llm_segment_error_inherits(self):
        assert issubclass(LLMSegmentError, VideoTransError)

    def test_ffmpeg_error_inherits(self):
        assert issubclass(FFmpegError, VideoTransError)

    def test_stop_task_inherits(self):
        assert issubclass(StopTask, VideoTransError)

    def test_stop_retry_inherits(self):
        assert issubclass(StopRetry, VideoTransError)


class TestVideoTransError:
    def test_raises_and_catches(self):
        try:
            raise VideoTransError("test message")
        except VideoTransError as e:
            assert str(e) == "test message"
            assert e.message == "test message"

    def test_translate_srt_error_message(self):
        e = TranslateSrtError("翻译失败")
        assert str(e) == "翻译失败"
        assert isinstance(e, VideoTransError)

    def test_dubbing_error_message(self):
        e = DubbingSrtError("配音出错")
        assert str(e) == "配音出错"
        assert isinstance(e, VideoTransError)

    def test_speech_text_error_message(self):
        e = SpeechToTextError("识别为空")
        assert str(e) == "识别为空"

    def test_ffmpeg_error_message(self):
        e = FFmpegError("ffmpeg crash")
        assert str(e) == "ffmpeg crash"

    def test_stop_task_caught_as_base(self):
        try:
            raise StopTask("stop now")
        except VideoTransError:
            pass
        else:
            raise AssertionError("StopTask should be caught as VideoTransError")

    def test_stop_retry_caught_as_base(self):
        try:
            raise StopRetry("no retry")
        except VideoTransError:
            pass
        else:
            raise AssertionError("StopRetry should be caught as VideoTransError")


class TestNoRetryExcept:
    def test_is_a_tuple(self):
        assert isinstance(NO_RETRY_EXCEPT, (tuple, list))

    def test_contains_connection_error(self):
        assert ConnectionError in NO_RETRY_EXCEPT or any(
            issubclass(cls, ConnectionError) if isinstance(cls, type) else False
            for cls in NO_RETRY_EXCEPT
        )


class TestGetMsgFromExcept:
    def test_returns_string(self):
        """get_msg_from_except handles standard ValueError."""
        try:
            raise ValueError("something wrong")
        except Exception as e:
            msg = get_msg_from_except(e)
            assert isinstance(msg, str)

    def test_handles_videotrans_error(self):
        e = VideoTransError("custom message")
        msg = get_msg_from_except(e)
        assert "custom message" in msg
