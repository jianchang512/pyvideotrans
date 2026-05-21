"""
Tests for cli.py — validates CLI TEXT_DB structure and argument definitions
by reading the source file as text, avoiding heavy dependency imports.
"""

from pathlib import Path

_CLI_PATH = Path(__file__).parent.parent / "cli.py"
_SOURCE = _CLI_PATH.read_text(encoding="utf-8")


class TestCLITextDB:
    def test_text_db_is_defined(self):
        assert "TEXT_DB" in _SOURCE
        assert "exec_stt_task" in _SOURCE
        assert "exec_vtv_task" in _SOURCE

    def test_all_task_types_have_entries(self):
        for key in ("exec_stt_task", "exec_tts_task", "exec_sts_task", "exec_vtv_task"):
            assert key in _SOURCE, f"Missing TEXT_DB key: {key}"

    def test_error_messages_exist(self):
        for key in ("err_missing_task", "err_file_not_found",
                     "err_tts_role_required", "err_sts_target_required", "err_vtv_missing"):
            assert key in _SOURCE, f"Missing error key: {key}"

    def test_zh_and_en_present(self):
        assert '"zh":' in _SOURCE
        assert '"en":' in _SOURCE

    def test_help_keys_exist(self):
        for key in ("help_task", "help_name", "help_recogn_type",
                     "help_tts_type", "help_translate_type"):
            assert key in _SOURCE, f"Missing help key: {key}"


class TestCLIArgDefaults:
    def test_recogn_type_default_zero(self):
        assert "recogn_type', type=int, default=0" in _SOURCE

    def test_tts_type_default_zero(self):
        assert "tts_type', type=int, default=0" in _SOURCE

    def test_detect_language_default_auto(self):
        assert "detect_language', type=str, default='auto'" in _SOURCE

    def test_subtitle_type_default_one(self):
        assert "subtitle_type', type=int, default=1" in _SOURCE

    def test_clear_cache_default_true(self):
        assert "clear_cache', action='store_true', default=True" in _SOURCE

    def test_no_clear_cache_option(self):
        assert "no-clear-cache'" in _SOURCE

    def test_name_required(self):
        assert "name', type=str, required=True" in _SOURCE

    def test_task_required(self):
        assert "task', type=str, required=True" in _SOURCE


class TestCLITaskChoices:
    def test_task_choices(self):
        assert "choices=['stt', 'tts', 'sts', 'vtv']" in _SOURCE

    def test_stt_params_present(self):
        for p in ("recogn_type", "detect_language", "model_name",
                   "remove_noise", "enable_diariz", "fix_punc"):
            assert p in _SOURCE, f"STT param '{p}' not found"

    def test_tts_params_present(self):
        for p in ("tts_type", "voice_role", "voice_rate", "volume", "pitch"):
            assert p in _SOURCE, f"TTS param '{p}' not found"

    def test_trans_params_present(self):
        for p in ("translate_type", "source_language_code", "target_language_code"):
            assert p in _SOURCE, f"Trans param '{p}' not found"

    def test_vtv_params_present(self):
        for p in ("subtitle_type", "is_separate", "recogn2pass"):
            assert p in _SOURCE, f"VTV param '{p}' not found"


class TestCLIParamValidation:
    def test_vtv_missing_check_exists(self):
        assert "err_vtv_missing" in _SOURCE

    def test_tts_role_validation(self):
        assert "not args.voice_role" in _SOURCE
        assert "err_tts_role_required" in _SOURCE

    def test_sts_target_validation(self):
        assert "not args.target_language_code" in _SOURCE
        assert "err_sts_target_required" in _SOURCE

    def test_file_not_found_validation(self):
        assert "not Path(args.name).exists()" in _SOURCE

    def test_uses_format_video(self):
        assert "format_video" in _SOURCE


class TestCLITaskFunctions:
    def test_stt_fun_exists(self):
        assert "def stt_fun(" in _SOURCE

    def test_tts_fun_exists(self):
        assert "def tts_fun(" in _SOURCE

    def test_sts_fun_exists(self):
        assert "def sts_fun(" in _SOURCE

    def test_vtv_fun_exists(self):
        assert "def vtv_fun(" in _SOURCE

    def test_exec_mode_set_to_cli(self):
        assert "app_cfg.exec_mode = 'cli'" in _SOURCE
