# -*- coding: utf-8 -*-
"""Tests that the translator/__init__.py split preserves all public imports and behaviour."""


class TestTranslatorSplitImports:
    """Verify every commonly-imported name is reachable from videotrans.translator."""

    def test_run_importable(self):
        from videotrans.translator import run
        assert callable(run)

    def test_get_code_importable(self):
        from videotrans.translator import get_code
        assert callable(get_code)

    def test_get_source_target_code_importable(self):
        from videotrans.translator import get_source_target_code
        assert callable(get_source_target_code)

    def test_get_language_qwen_importable(self):
        from videotrans.translator import get_language_qwen
        assert callable(get_language_qwen)

    def test_is_allow_translate_importable(self):
        from videotrans.translator import is_allow_translate
        assert callable(is_allow_translate)

    def test_get_audio_code_importable(self):
        from videotrans.translator import get_audio_code
        assert callable(get_audio_code)

    def test_get_subtitle_code_importable(self):
        from videotrans.translator import get_subtitle_code
        assert callable(get_subtitle_code)

    def test_get_mkv_code_importable(self):
        from videotrans.translator import get_mkv_code
        assert callable(get_mkv_code)

    def test_check_google_importable(self):
        from videotrans.translator import _check_google
        assert callable(_check_google)

    def test_lang_code_importable(self):
        from videotrans.translator import LANG_CODE
        assert isinstance(LANG_CODE, dict)
        assert 'en' in LANG_CODE
        assert 'zh-cn' in LANG_CODE

    def test_langname_dict_importable(self):
        from videotrans.translator import LANGNAME_DICT
        assert isinstance(LANGNAME_DICT, dict)

    def test_langname_dict_rev_importable(self):
        from videotrans.translator import LANGNAME_DICT_REV
        assert isinstance(LANGNAME_DICT_REV, dict)

    def test_id_name_dict_importable(self):
        from videotrans.translator import _ID_NAME_DICT
        assert isinstance(_ID_NAME_DICT, dict)
        assert len(_ID_NAME_DICT) == 24

    def test_translaste_name_list_importable(self):
        from videotrans.translator import TRANSLASTE_NAME_LIST
        assert isinstance(TRANSLASTE_NAME_LIST, list)
        assert len(TRANSLASTE_NAME_LIST) == 24

    def test_ai_trans_channels_importable(self):
        from videotrans.translator import AI_TRANS_CHANNELS
        assert isinstance(AI_TRANS_CHANNELS, list)
        assert len(AI_TRANS_CHANNELS) == 14

    def test_base_trans_importable(self):
        from videotrans.translator import BaseTrans
        assert BaseTrans is not None


class TestTranslatorIndexConstants:
    """Verify all index constants exist and have correct values."""

    def test_google_index(self):
        from videotrans.translator import GOOGLE_INDEX
        assert GOOGLE_INDEX == 0

    def test_microsoft_index(self):
        from videotrans.translator import MICROSOFT_INDEX
        assert MICROSOFT_INDEX == 1

    def test_m2m100_index(self):
        from videotrans.translator import M2M100_INDEX
        assert M2M100_INDEX == 2

    def test_chatgpt_index(self):
        from videotrans.translator import CHATGPT_INDEX
        assert CHATGPT_INDEX == 3

    def test_deepseek_index(self):
        from videotrans.translator import DEEPSEEK_INDEX
        assert DEEPSEEK_INDEX == 4

    def test_gemini_index(self):
        from videotrans.translator import GEMINI_INDEX
        assert GEMINI_INDEX == 5

    def test_zhipuai_index(self):
        from videotrans.translator import ZHIPUAI_INDEX
        assert ZHIPUAI_INDEX == 6

    def test_azuregpt_index(self):
        from videotrans.translator import AZUREGPT_INDEX
        assert AZUREGPT_INDEX == 7

    def test_locallm_index(self):
        from videotrans.translator import LOCALLLM_INDEX
        assert LOCALLLM_INDEX == 8

    def test_openrouter_index(self):
        from videotrans.translator import OPENROUTER_INDEX
        assert OPENROUTER_INDEX == 9

    def test_siliconflow_index(self):
        from videotrans.translator import SILICONFLOW_INDEX
        assert SILICONFLOW_INDEX == 10

    def test_ai302_index(self):
        from videotrans.translator import AI302_INDEX
        assert AI302_INDEX == 11

    def test_qwenmt_index(self):
        from videotrans.translator import QWENMT_INDEX
        assert QWENMT_INDEX == 12

    def test_zijie_index(self):
        from videotrans.translator import ZIJIE_INDEX
        assert ZIJIE_INDEX == 13

    def test_tencent_index(self):
        from videotrans.translator import TENCENT_INDEX
        assert TENCENT_INDEX == 14

    def test_baidu_index(self):
        from videotrans.translator import BAIDU_INDEX
        assert BAIDU_INDEX == 15

    def test_deepl_index(self):
        from videotrans.translator import DEEPL_INDEX
        assert DEEPL_INDEX == 16

    def test_deeplx_index(self):
        from videotrans.translator import DEEPLX_INDEX
        assert DEEPLX_INDEX == 17

    def test_ali_index(self):
        from videotrans.translator import ALI_INDEX
        assert ALI_INDEX == 18

    def test_libre_index(self):
        from videotrans.translator import LIBRE_INDEX
        assert LIBRE_INDEX == 19

    def test_minimax_index(self):
        from videotrans.translator import MINIMAX_INDEX
        assert MINIMAX_INDEX == 20

    def test_xiaomi_index(self):
        from videotrans.translator import XIAOMI_INDEX
        assert XIAOMI_INDEX == 21

    def test_camb_index(self):
        from videotrans.translator import CAMB_INDEX
        assert CAMB_INDEX == 22

    def test_transapi_index(self):
        from videotrans.translator import TRANSAPI_INDEX
        assert TRANSAPI_INDEX == 23


class TestTranslatorGetCode:
    """Verify get_code() function works correctly."""

    def test_none_returns_none(self):
        from videotrans.translator import get_code
        assert get_code(None) is None

    def test_dash_returns_none(self):
        from videotrans.translator import get_code
        assert get_code('-') is None

    def test_no_returns_none(self):
        from videotrans.translator import get_code
        assert get_code('No') is None

    def test_empty_string_returns_none(self):
        from videotrans.translator import get_code
        assert get_code('') is None

    def test_zh_maps_to_zh_cn(self):
        from videotrans.translator import get_code
        assert get_code('zh') == 'zh-cn'

    def test_lang_code_passthrough(self):
        from videotrans.translator import get_code
        assert get_code('en') == 'en'
        assert get_code('fr') == 'fr'
        assert get_code('ja') == 'ja'

    def test_display_name_returns_code(self):
        from videotrans.translator import get_code
        from videotrans.translator import LANGNAME_DICT_REV
        for display_name, code in list(LANGNAME_DICT_REV.items())[:5]:
            result = get_code(display_name)
            assert result == code, f"get_code({display_name!r}) = {result!r}, expected {code!r}"


class TestTranslatorGetSourceTargetCode:
    """Verify get_source_target_code() function works correctly."""

    def test_no_source_no_target(self):
        from videotrans.translator import get_source_target_code
        result = get_source_target_code(show_source=None, show_target=None)
        assert result == (None, None)

    def test_google_channel(self):
        from videotrans.translator import get_source_target_code, GOOGLE_INDEX
        src, tgt = get_source_target_code(
            show_source='en', show_target='zh-cn', translate_type=GOOGLE_INDEX
        )
        assert src == 'en'
        assert tgt == 'zh-cn'

    def test_ai_channel(self):
        from videotrans.translator import get_source_target_code, CHATGPT_INDEX
        src, tgt = get_source_target_code(
            show_source='en', show_target='zh-cn', translate_type=CHATGPT_INDEX
        )
        assert src == 'English'
        assert tgt == 'Simplified Chinese'

    def test_baidu_channel(self):
        from videotrans.translator import get_source_target_code, BAIDU_INDEX
        src, tgt = get_source_target_code(
            show_source='en', show_target='zh-cn', translate_type=BAIDU_INDEX
        )
        assert src == 'en'
        assert tgt == 'zh'

    def test_unknown_language_passthrough(self):
        from videotrans.translator import get_source_target_code
        src, tgt = get_source_target_code(
            show_source='xyz', show_target='abc', translate_type=0
        )
        assert src == 'xyz'
        assert tgt == 'abc'

    def test_dash_source_skipped(self):
        from videotrans.translator import get_source_target_code, GOOGLE_INDEX
        src, tgt = get_source_target_code(
            show_source='-', show_target='zh-cn', translate_type=GOOGLE_INDEX
        )
        assert src == '-'
        assert tgt == 'zh-cn'


class TestTranslatorIsAllowTranslate:
    """Verify is_allow_translate() function works correctly."""

    def test_google_always_allowed(self):
        from videotrans.translator import is_allow_translate, GOOGLE_INDEX
        assert is_allow_translate(translate_type=GOOGLE_INDEX) is True

    def test_microsoft_always_allowed(self):
        from videotrans.translator import is_allow_translate, MICROSOFT_INDEX
        assert is_allow_translate(translate_type=MICROSOFT_INDEX) is True

    def test_only_key_true(self):
        from videotrans.translator import is_allow_translate, GOOGLE_INDEX
        assert is_allow_translate(translate_type=GOOGLE_INDEX, only_key=True) is True


class TestTranslatorAudioCode:
    """Verify get_audio_code() function works correctly."""

    def test_auto_for_none(self):
        from videotrans.translator import get_audio_code
        assert get_audio_code(show_source=None) == 'auto'

    def test_auto_for_dash(self):
        from videotrans.translator import get_audio_code
        assert get_audio_code(show_source='-') == 'auto'

    def test_auto_for_auto(self):
        from videotrans.translator import get_audio_code
        assert get_audio_code(show_source='auto') == 'auto'

    def test_english_code(self):
        from videotrans.translator import get_audio_code
        assert get_audio_code(show_source='en') == 'en'

    def test_zh_cn_code(self):
        from videotrans.translator import get_audio_code
        assert get_audio_code(show_source='zh-cn') == 'zh-cn'


class TestTranslatorSubtitleCode:
    """Verify get_subtitle_code() function works correctly."""

    def test_english(self):
        from videotrans.translator import get_subtitle_code
        assert get_subtitle_code(show_target='en') == 'eng'

    def test_zh_cn(self):
        from videotrans.translator import get_subtitle_code
        assert get_subtitle_code(show_target='zh-cn') == 'zho'

    def test_fallback_to_eng(self):
        from videotrans.translator import get_subtitle_code
        assert get_subtitle_code(show_target='nonexistent') == 'eng'


class TestTranslatorMkvCode:
    """Verify get_mkv_code() function works correctly."""

    def test_fra_to_fre(self):
        from videotrans.translator import get_mkv_code
        assert get_mkv_code('fra') == 'fre'

    def test_deu_to_ger(self):
        from videotrans.translator import get_mkv_code
        assert get_mkv_code('deu') == 'ger'

    def test_zho_to_chi(self):
        from videotrans.translator import get_mkv_code
        assert get_mkv_code('zho') == 'chi'

    def test_ces_to_cze(self):
        from videotrans.translator import get_mkv_code
        assert get_mkv_code('ces') == 'cze'

    def test_ell_to_gre(self):
        from videotrans.translator import get_mkv_code
        assert get_mkv_code('ell') == 'gre'

    def test_fas_to_per(self):
        from videotrans.translator import get_mkv_code
        assert get_mkv_code('fas') == 'per'

    def test_msa_to_may(self):
        from videotrans.translator import get_mkv_code
        assert get_mkv_code('msa') == 'may'

    def test_nld_to_dut(self):
        from videotrans.translator import get_mkv_code
        assert get_mkv_code('nld') == 'dut'

    def test_ron_to_rum(self):
        from videotrans.translator import get_mkv_code
        assert get_mkv_code('ron') == 'rum'

    def test_unknown_code_passthrough(self):
        from videotrans.translator import get_mkv_code
        assert get_mkv_code('eng') == 'eng'
        assert get_mkv_code('jpn') == 'jpn'


class TestTranslatorRunCallable:
    """Verify run() is callable and has correct signature."""

    def test_run_is_callable(self):
        from videotrans.translator import run
        import inspect
        assert callable(run)
        sig = inspect.signature(run)
        params = list(sig.parameters.keys())
        assert 'translate_type' in params
        assert 'text_list' in params
        assert 'is_test' in params
        assert 'source_code' in params
        assert 'target_code' in params
        assert 'uuid' in params
