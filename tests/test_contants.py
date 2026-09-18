from videotrans.configure import constants


class TestCJKLang:
    def test_cjk_languages_list(self):
        assert "zh" in constants.CJK_LANG
        assert "ja" in constants.CJK_LANG
        assert "ko" in constants.CJK_LANG
        assert "th" in constants.CJK_LANG
        assert "km" in constants.CJK_LANG
        assert "yue" in constants.CJK_LANG
        assert "yu" in constants.CJK_LANG

    def test_non_cjk_not_in_list(self):
        assert "en" not in constants.CJK_LANG
        assert "fr" not in constants.CJK_LANG
        assert "de" not in constants.CJK_LANG
        assert "es" not in constants.CJK_LANG
        assert "ru" not in constants.CJK_LANG


class TestPuncFlags:
    def test_punc_flags_contains_common_chars(self):
        assert "," in constants.PUNC_FLAGS
        assert "." in constants.PUNC_FLAGS
        assert "?" in constants.PUNC_FLAGS
        assert "!" in constants.PUNC_FLAGS
        assert "。" in constants.PUNC_FLAGS
        assert "？" in constants.PUNC_FLAGS

    def test_half_flags_no_end_punctuation(self):
        assert "." not in constants.PUNC_FLAGS_HALF
        assert "。" not in constants.PUNC_FLAGS_HALF
        assert "!" not in constants.PUNC_FLAGS_HALF
        assert "," in constants.PUNC_FLAGS_HALF
        assert "，" in constants.PUNC_FLAGS_HALF

    def test_end_flags_are_sentence_terminators(self):
        assert "." in constants.PUNC_FLAGS_END
        assert "。" in constants.PUNC_FLAGS_END
        assert "?" in constants.PUNC_FLAGS_END
        assert "？" in constants.PUNC_FLAGS_END
        assert "!" in constants.PUNC_FLAGS_END
        assert "！" in constants.PUNC_FLAGS_END


class TestListenText:
    def test_has_common_languages(self):
        assert "zh" in constants.LISTEN_TEXT
        assert "en" in constants.LISTEN_TEXT
        assert "ja" in constants.LISTEN_TEXT
        assert "ko" in constants.LISTEN_TEXT
        assert "fr" in constants.LISTEN_TEXT
        assert "de" in constants.LISTEN_TEXT
        assert "es" in constants.LISTEN_TEXT

    def test_listen_text_is_non_empty(self):
        for lang, text in constants.LISTEN_TEXT.items():
            assert len(text) > 0, f"LISTEN_TEXT[{lang}] is empty"


class TestFasterModelsDict:
    def test_common_models_present(self):
        assert "tiny" in constants.FASTER_MODELS_DICT
        assert "base" in constants.FASTER_MODELS_DICT
        assert "small" in constants.FASTER_MODELS_DICT
        assert "medium" in constants.FASTER_MODELS_DICT
        assert "large-v3" in constants.FASTER_MODELS_DICT
        assert "large-v3-turbo" in constants.FASTER_MODELS_DICT

    def test_model_values_are_non_empty(self):
        for name, repo in constants.FASTER_MODELS_DICT.items():
            assert len(repo) > 0, f"Model {name} has empty repo"


class TestNoProxyList:
    def test_contains_expected_domains(self):
        assert "tencentcloudapi.com" in constants._no_proxy_list
        assert "hf-mirror.com" in constants._no_proxy_list

    def test_formed_into_env_string(self):
        no_proxy = constants.no_proxy
        assert isinstance(no_proxy, str)
        assert len(no_proxy) > 0


class TestNONWORD:
    def test_non_word_matches_punctuation(self):
        import re

        pattern = constants.NON_WORD
        assert re.match(pattern, "。")
        assert re.match(pattern, ",")
        assert re.match(pattern, "!")
        assert re.match(pattern, "...")
        assert re.match(pattern, ' " ')

    def test_non_word_does_not_match_text(self):
        import re

        pattern = constants.NON_WORD
        assert re.match(pattern, "Hello") is None
        assert re.match(pattern, "你好") is None
        assert re.match(pattern, "abc123") is None


class TestAudioVideoExts:
    def test_audio_exits_has_common_formats(self):
        # at least mp3, wav, m4a
        lower = [e.lower() for e in constants.AUDIO_EXITS]
        assert "mp3" in lower
        assert "wav" in lower

    def test_video_exts_has_common_formats(self):
        lower = [e.lower() for e in constants.VIDEO_EXTS]
        assert "mp4" in lower
        assert "mkv" in lower
