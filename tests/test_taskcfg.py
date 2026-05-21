import uuid as _uuid

from videotrans.task.taskcfg import (
    InputFile,
    SignMsg,
    SrtItem,
    TaskCfgBase,
    TaskCfgSTT,
    TaskCfgTTS,
    TaskCfgSTS,
    TaskCfgVTT,
)


class TestInputFile:
    def test_default_initialization(self):
        f = InputFile()
        assert f.name is None
        assert f.dirname is None
        assert f.basename is None
        assert f.noextname is None
        assert f.ext is None
        assert f.uuid is None
        assert f.target_dir is None

    def test_full_initialization(self):
        f = InputFile(
            name="C:/videos/test.mp4",
            dirname="C:/videos",
            basename="test.mp4",
            noextname="test",
            ext="mp4",
            uuid="abc-123",
            target_dir="C:/videos/_video_out",
        )
        assert f.name == "C:/videos/test.mp4"
        assert f.noextname == "test"
        assert f.ext == "mp4"

    def test_dict_access_getitem(self):
        f = InputFile(name="video.mp4", ext="mp4")
        assert f["name"] == "video.mp4"
        assert f["ext"] == "mp4"

    def test_dict_access_setitem(self):
        f = InputFile()
        f["name"] = "audio.wav"
        f["ext"] = "wav"
        assert f.name == "audio.wav"
        assert f.ext == "wav"

    def test_get_method(self):
        f = InputFile(name="x.mp4")
        assert f.get("name") == "x.mp4"
        assert f.get("missing", "fallback") == "fallback"

    def test_or_with_dict(self):
        f = InputFile(name="a.mp4", ext="mp4")
        merged = f | {"noextname": "a", "uuid": "u1"}
        assert merged["name"] == "a.mp4"
        assert merged["noextname"] == "a"

    def test_ror_with_dict(self):
        f = InputFile(name="a.mp4", ext="mp4")
        merged = {"noextname": "a"} | f
        assert merged["name"] == "a.mp4"
        assert merged["ext"] == "mp4"
        # asdict(self) values take priority; noextname is None by default
        assert "noextname" in merged

    def test_or_with_non_dict_raises_typeerror(self):
        f = InputFile(name="a.mp4")
        try:
            f | 123
        except TypeError:
            pass
        else:
            raise AssertionError("Expected TypeError for InputFile | int")


class TestSignMsg:
    def test_default_values(self):
        msg = SignMsg()
        assert msg.type == "logs"
        assert msg.uuid == ""
        assert msg.text == ""

    def test_custom_values(self):
        msg = SignMsg(type="error", uuid="u1", text="something failed")
        assert msg.type == "error"
        assert msg.uuid == "u1"

    def test_dict_access(self):
        msg = SignMsg(text="hello")
        assert msg["text"] == "hello"
        msg["text"] = "world"
        assert msg["text"] == "world"

    def test_is_stop(self):
        for t in ("end", "stop", "succeed", "error"):
            assert SignMsg(type=t).is_stop() is True
        for t in ("logs", "subtitle", "replace_subtitle", "set_precent"):
            assert SignMsg(type=t).is_stop() is False

    def test_is_error(self):
        assert SignMsg(type="error").is_error() is True
        assert SignMsg(type="logs").is_error() is False
        assert SignMsg(type="succeed").is_error() is False

    def test_get_method(self):
        msg = SignMsg(type="logs", text="hi")
        assert msg.get("text") == "hi"
        assert msg.get("missing", "default") == "default"


class TestSrtItem:
    def test_default_initialization(self):
        item = SrtItem()
        assert item.text == ""
        assert item.start_time == 0
        assert item.end_time == 0
        assert item.startraw == ""
        assert item.endraw == ""
        assert item.line == 1
        assert item.time == ""
        assert item.spk == ""
        assert item.filename == ""

    def test_full_initialization(self):
        item = SrtItem(
            text="Hello world",
            start_time=1000,
            end_time=3000,
            startraw="00:00:01,000",
            endraw="00:00:03,000",
            line=5,
            time="00:00:01,000 --> 00:00:03,000",
            spk="SPEAKER_00",
            filename="/tmp/dubb-5.wav",
        )
        assert item.text == "Hello world"
        assert item.start_time == 1000
        assert item.end_time == 3000
        assert item.line == 5
        assert item.spk == "SPEAKER_00"
        assert item.filename == "/tmp/dubb-5.wav"

    def test_dict_access_getitem(self):
        item = SrtItem(text="Hi", line=3)
        assert item["text"] == "Hi"
        assert item["line"] == 3

    def test_dict_access_setitem(self):
        item = SrtItem()
        item["text"] = "New text"
        item["start_time"] = 2000
        assert item.text == "New text"
        assert item.start_time == 2000

    def test_items_iterates_all_fields(self):
        item = SrtItem(text="A", line=1)
        result = dict(item.items())
        assert result["text"] == "A"
        assert result["line"] == 1
        assert "start_time" in result
        assert "end_time" in result
        assert "startraw" in result
        assert "endraw" in result

    def test_iter_yields_field_names(self):
        item = SrtItem()
        names = list(item)
        assert "text" in names
        assert "line" in names
        assert "time" in names
        assert "spk" in names
        assert "filename" in names
        # 9 fields total
        assert len(names) == 9

    def test_mixed_attribute_and_dict_access(self):
        item = SrtItem(text="test")
        # attribute access
        assert item.text == "test"
        # dict access matches
        assert item["text"] == item.text
        # modify via dict
        item["text"] = "changed"
        assert item.text == "changed"


class TestTaskCfgBase:
    def test_default_initialization(self):
        cfg = TaskCfgBase()
        assert cfg.uuid is None
        assert cfg.name is None
        assert cfg.is_cuda is False
        assert cfg.source_language is None
        assert cfg.target_language is None

    def test_partial_initialization(self):
        uid = str(_uuid.uuid4())
        cfg = TaskCfgBase(
            uuid=uid,
            name="D:/media/video.mp4",
            is_cuda=True,
            source_language_code="en",
            target_language_code="zh-cn",
        )
        assert cfg.uuid == uid
        assert cfg.name == "D:/media/video.mp4"
        assert cfg.is_cuda is True
        assert cfg.source_language_code == "en"
        assert cfg.target_language_code == "zh-cn"


class TestTaskCfgSTT:
    def test_inherits_base_fields(self):
        uid = str(_uuid.uuid4())
        cfg = TaskCfgSTT(uuid=uid, source_language_code="en")
        assert cfg.uuid == uid
        assert cfg.source_language_code == "en"
        # STT-specific defaults
        assert cfg.remove_noise is False
        assert cfg.enable_diariz is False
        assert cfg.nums_diariz == 0
        assert cfg.fix_punc is False
        assert cfg.rephrase == 2

    def test_stt_specific_fields(self):
        cfg = TaskCfgSTT(
            recogn_type=0,
            model_name="large-v3-turbo",
            detect_language="en",
            remove_noise=True,
            fix_punc=True,
            rephrase=1,
        )
        assert cfg.recogn_type == 0
        assert cfg.model_name == "large-v3-turbo"
        assert cfg.detect_language == "en"
        assert cfg.remove_noise is True
        assert cfg.fix_punc is True
        assert cfg.rephrase == 1


class TestTaskCfgTTS:
    def test_tts_defaults(self):
        cfg = TaskCfgTTS()
        assert cfg.volume == "+0%"
        assert cfg.pitch == "+0Hz"
        assert cfg.voice_rate == "+0%"
        assert cfg.voice_role is None
        assert cfg.voice_autorate is False
        assert cfg.video_autorate is False
        assert cfg.align_sub_audio is True
        assert cfg.remove_silent_mid is False

    def test_tts_custom(self):
        cfg = TaskCfgTTS(
            tts_type=0,
            voice_role="en-US-AriaNeural",
            volume="+20%",
            pitch="+5Hz",
            voice_rate="+10%",
            voice_autorate=True,
        )
        assert cfg.tts_type == 0
        assert cfg.voice_role == "en-US-AriaNeural"
        assert cfg.volume == "+20%"
        assert cfg.pitch == "+5Hz"
        assert cfg.voice_rate == "+10%"
        assert cfg.voice_autorate is True


class TestTaskCfgSTS:
    def test_trans_default(self):
        cfg = TaskCfgSTS()
        assert cfg.translate_type is None

    def test_trans_custom(self):
        cfg = TaskCfgSTS(translate_type=3)  # CHATGPT_INDEX
        assert cfg.translate_type == 3


class TestTaskCfgVTT:
    def test_inherits_all_parent_fields(self):
        cfg = TaskCfgVTT(
            uuid="vtt-001",
            name="D:/media/video.mp4",
            source_language_code="en",
            target_language_code="zh-cn",
            recogn_type=0,
            tts_type=0,
            translate_type=3,
            subtitle_type=1,
            app_mode="biaozhun",
        )
        # Base fields
        assert cfg.uuid == "vtt-001"
        assert cfg.source_language_code == "en"
        assert cfg.target_language_code == "zh-cn"
        # STT fields
        assert cfg.recogn_type == 0
        # TTS fields
        assert cfg.tts_type == 0
        # STS fields
        assert cfg.translate_type == 3
        # VTT-specific fields
        assert cfg.subtitle_type == 1
        assert cfg.app_mode == "biaozhun"

    def test_vtt_defaults(self):
        cfg = TaskCfgVTT()
        assert cfg.app_mode == "biaozhun"
        assert cfg.subtitles == ""
        assert cfg.is_separate is False
        assert cfg.embed_bgm is True
        assert cfg.clear_cache is False
        assert cfg.subtitle_type == 0
        assert cfg.only_out_mp4 is False
        assert cfg.recogn2pass is False
        assert cfg.output_srt == 0
        assert cfg.copysrt_rawvideo is False
        assert cfg.loop_backaudio == 0
        assert cfg.backaudio_volume == 0.8

    def test_isinstance_checks(self):
        cfg = TaskCfgVTT()
        assert isinstance(cfg, TaskCfgBase)
        assert isinstance(cfg, TaskCfgSTT)
        assert isinstance(cfg, TaskCfgTTS)
        assert isinstance(cfg, TaskCfgSTS)

    def test_vtt_tiqu_mode_settings(self):
        cfg = TaskCfgVTT(
            app_mode="tiqu",
            subtitle_type=3,
            output_srt=2,
            copysrt_rawvideo=True,
        )
        assert cfg.app_mode == "tiqu"
        assert cfg.subtitle_type == 3
        assert cfg.output_srt == 2
        assert cfg.copysrt_rawvideo is True


class TestTaskCfgInterop:
    """Test that TaskCfgVTT combines all three config types correctly."""

    def test_shared_fields_consistent(self):
        uid = str(_uuid.uuid4())
        cfg = TaskCfgVTT(
            uuid=uid,
            name="x.mp4",
            source_language_code="en",
            target_language_code="fr",
            cache_folder="/tmp/cache",
        )
        # These fields are in TaskCfgBase, shared by all
        assert cfg.uuid == uid
        assert cfg.source_language_code == "en"
        assert cfg.target_language_code == "fr"
        assert cfg.cache_folder == "/tmp/cache"

    def test_stt_and_tts_and_sts_together(self):
        cfg = TaskCfgVTT(
            recogn_type=0,
            model_name="tiny",
            tts_type=1,
            voice_role="clone",
            translate_type=3,
            enable_diariz=True,
            nums_diariz=2,
        )
        assert cfg.recogn_type == 0
        assert cfg.model_name == "tiny"
        assert cfg.tts_type == 1
        assert cfg.voice_role == "clone"
        assert cfg.translate_type == 3
        assert cfg.enable_diariz is True
        assert cfg.nums_diariz == 2
