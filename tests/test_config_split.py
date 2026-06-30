# -*- coding: utf-8 -*-
"""Tests that the config.py split preserves all public imports and behaviour."""
from pathlib import Path


class TestConfigSplitImports:
    """Verify every commonly-imported name is reachable from config.py."""

    def test_app_cfg_importable(self):
        from videotrans.configure.config import app_cfg
        assert app_cfg is not None

    def test_settings_importable(self):
        from videotrans.configure.config import settings
        assert settings is not None

    def test_params_importable(self):
        from videotrans.configure.config import params
        assert params is not None

    def test_tr_importable(self):
        from videotrans.configure.config import tr
        assert callable(tr)

    def test_root_dir_importable(self):
        from videotrans.configure.config import ROOT_DIR
        assert isinstance(ROOT_DIR, str)
        assert ROOT_DIR  # non-empty

    def test_logger_importable(self):
        from videotrans.configure.config import logger
        import logging
        assert isinstance(logger, logging.Logger)

    def test_home_dir_importable(self):
        from videotrans.configure.config import HOME_DIR
        assert isinstance(HOME_DIR, str)
        assert HOME_DIR

    def test_temp_root_importable(self):
        from videotrans.configure.config import TEMP_ROOT
        assert isinstance(TEMP_ROOT, str)
        assert TEMP_ROOT.endswith('/tmp')

    def test_temp_dir_importable(self):
        from videotrans.configure.config import TEMP_DIR
        assert isinstance(TEMP_DIR, str)

    def test_translate_cache_importable(self):
        from videotrans.configure.config import TRANSLATE_CACHE
        assert isinstance(TRANSLATE_CACHE, str)
        assert 'translate_cache' in TRANSLATE_CACHE


class TestTrFunction:
    """Verify tr() behaves correctly."""

    def test_tr_returns_key_on_missing(self):
        from videotrans.configure.config import tr
        result = tr("totally_nonexistent_key_xyz_12345")
        assert result == "totally_nonexistent_key_xyz_12345"

    def test_tr_accepts_list(self):
        from videotrans.configure.config import tr
        result = tr(["nonexistent_a", "nonexistent_b"])
        assert isinstance(result, str)


class TestPushQueue:
    """Verify push_queue is accessible."""

    def test_push_queue_exists(self):
        from videotrans.configure.config import push_queue
        assert callable(push_queue)


class TestAppCfgClass:
    """Verify AppCfg dataclass works."""

    def test_app_cfg_has_expected_attrs(self):
        from videotrans.configure.config import app_cfg
        assert hasattr(app_cfg, 'exit_soft')
        assert hasattr(app_cfg, 'stoped_uuid_set')
        assert hasattr(app_cfg, 'current_status')
        assert hasattr(app_cfg, 'prepare_queue')

    def test_app_cfg_rm_uuid(self):
        from videotrans.configure.config import app_cfg
        app_cfg.stoped_uuid_set.add("test-uuid-123")
        app_cfg.rm_uuid("test-uuid-123")
        assert "test-uuid-123" not in app_cfg.stoped_uuid_set

    def test_app_cfg_rm_uuid_none(self):
        from videotrans.configure.config import app_cfg
        app_cfg.rm_uuid(None)  # should not raise


class TestAppSettingsClass:
    """Verify AppSettings dataclass works."""

    def test_settings_has_expected_attrs(self):
        from videotrans.configure.config import settings
        assert hasattr(settings, 'homedir')
        assert hasattr(settings, 'lang')
        assert hasattr(settings, 'proxy')

    def test_settings_to_dict(self):
        from videotrans.configure.config import settings
        d = settings.to_dict()
        assert isinstance(d, dict)
        assert 'homedir' in d


class TestAppParamsClass:
    """Verify AppParams dataclass works."""

    def test_params_has_expected_attrs(self):
        from videotrans.configure.config import params
        assert hasattr(params, 'chatgpt_api')
        assert hasattr(params, 'chatgpt_key')
        assert hasattr(params, 'deepl_authkey')

    def test_params_to_dict(self):
        from videotrans.configure.config import params
        d = params.to_dict()
        assert isinstance(d, dict)
        assert 'chatgpt_api' in d


class TestInitRun:
    """Verify init_run is callable."""

    def test_init_run_exists(self):
        from videotrans.configure.config import init_run
        assert callable(init_run)


class TestAccessibleFunctions:
    """Verify internal functions are accessible through config module."""

    def test_push_queue_accessible(self):
        from videotrans.configure.config import push_queue
        assert callable(push_queue)

    def test_update_logging_level_accessible(self):
        from videotrans.configure.config import update_logging_level
        assert callable(update_logging_level)

    def test_set_env_accessible(self):
        from videotrans.configure.config import _set_env
        assert callable(_set_env)

    def test_set_logs_accessible(self):
        from videotrans.configure.config import _set_logs
        assert callable(_set_logs)


class TestModuleLevelConstants:
    """Verify constants match expected values."""

    def test_root_dir_not_empty(self):
        from videotrans.configure.config import ROOT_DIR
        assert len(ROOT_DIR) > 0

    def test_temp_root_format(self):
        from videotrans.configure.config import ROOT_DIR, TEMP_ROOT
        assert TEMP_ROOT == f"{ROOT_DIR}/tmp"

    def test_logs_dir_format(self):
        from videotrans.configure.config import ROOT_DIR, LOGS_DIR
        assert LOGS_DIR == f"{ROOT_DIR}/logs"

    def test_is_frozen_is_bool(self):
        from videotrans.configure.config import IS_FROZEN
        assert isinstance(IS_FROZEN, bool)

    def test_sys_tmp_is_string(self):
        from videotrans.configure.config import SYS_TMP
        assert isinstance(SYS_TMP, str)

    def test_log_dir_exists(self):
        from videotrans.configure.config import LOGS_DIR
        assert Path(LOGS_DIR).exists()

    def test_models_dir_exists(self):
        from videotrans.configure.config import ROOT_DIR
        assert Path(f"{ROOT_DIR}/models").exists()
