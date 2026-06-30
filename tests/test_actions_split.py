import importlib
import inspect

import pytest


class TestActionsSplitImports:
    def test_actions_check_importable(self):
        mod = importlib.import_module('videotrans.mainwin._actions_check')
        assert hasattr(mod, 'WinActionCheckMixin')

    def test_actions_config_importable(self):
        mod = importlib.import_module('videotrans.mainwin._actions_config')
        assert hasattr(mod, 'WinActionConfigMixin')

    def test_actions_task_importable(self):
        mod = importlib.import_module('videotrans.mainwin._actions_task')
        assert hasattr(mod, 'WinActionTaskMixin')

    def test_actions_importable(self):
        mod = importlib.import_module('videotrans.mainwin._actions')
        assert hasattr(mod, 'WinAction')

    def test_actions_base_mode_importable(self):
        mod = importlib.import_module('videotrans.mainwin._actions_base_mode')
        assert hasattr(mod, 'WinActionBaseModeMixin')

    def test_actions_base_file_importable(self):
        mod = importlib.import_module('videotrans.mainwin._actions_base_file')
        assert hasattr(mod, 'WinActionBaseFileMixin')

    def test_actions_base_misc_importable(self):
        mod = importlib.import_module('videotrans.mainwin._actions_base_misc')
        assert hasattr(mod, 'WinActionBaseMiscMixin')

    def test_actions_base_importable(self):
        mod = importlib.import_module('videotrans.mainwin._actions_base')
        assert hasattr(mod, 'WinActionBase')


class TestActionsClassHierarchy:
    def test_winaction_inherits_winactionbase(self):
        from videotrans.mainwin._actions import WinAction
        from videotrans.mainwin._actions_base import WinActionBase
        assert issubclass(WinAction, WinActionBase)

    def test_winaction_inherits_mixins(self):
        from videotrans.mainwin._actions import WinAction
        from videotrans.mainwin._actions_check import WinActionCheckMixin
        from videotrans.mainwin._actions_config import WinActionConfigMixin
        from videotrans.mainwin._actions_task import WinActionTaskMixin
        assert issubclass(WinAction, WinActionCheckMixin)
        assert issubclass(WinAction, WinActionConfigMixin)
        assert issubclass(WinAction, WinActionTaskMixin)

    def test_winactionbase_inherits_mixins(self):
        from videotrans.mainwin._actions_base import WinActionBase
        from videotrans.mainwin._actions_base_mode import WinActionBaseModeMixin
        from videotrans.mainwin._actions_base_file import WinActionBaseFileMixin
        from videotrans.mainwin._actions_base_misc import WinActionBaseMiscMixin
        assert issubclass(WinActionBase, WinActionBaseModeMixin)
        assert issubclass(WinActionBase, WinActionBaseFileMixin)
        assert issubclass(WinActionBase, WinActionBaseMiscMixin)


class TestActionsMethods:
    EXPECTED_WINACTION_METHODS = {
        '_reset', 'set_djs_timeout', 'delete_process', 'import_sub_fun',
        'set_translate_type', 'set_subtitle_type', 'shound_translate', 'check_tts',
        'check_reccogn', 'check_output', 'check_name_length', 'check_start',
        'show_xxl_select', 'show_cpp_select', 'recogn_type_change', 'model_type_change',
        'tts_type_change', 'set_voice_role',
        'create_btns', 'retry', 'add_process_btn', 'set_process_btn_text',
        'update_status', 'update_data', '_check_all_done',
    }

    EXPECTED_WINACTIONBASE_METHODS = {
        'set_biaozhun', 'set_tiquzimu', 'toggle_adv', 'hide_show_element',
        'set_mode', '_disabled_button', 'disabled_widget',
        'get_mp4', 'get_save_dir', 'get_background', 'change_proxy',
        '_test_proxy', 'proxy_alert', 'clearcache', '_clean_dir',
        'about', 'check_cuda', 'check_voice_autorate', 'check_video_autorate',
        'check_txt', 'cuda_isok', 'listen_voice_fun', 'show_listen_btn',
        'check_name', 'lawalert', 'open_url',
    }

    def test_winaction_has_expected_methods(self):
        from videotrans.mainwin._actions import WinAction
        actual = {m for m in dir(WinAction) if not m.startswith('__')}
        missing = self.EXPECTED_WINACTION_METHODS - actual
        assert not missing, f"WinAction missing methods: {missing}"

    def test_winactionbase_has_expected_methods(self):
        from videotrans.mainwin._actions_base import WinActionBase
        actual = {m for m in dir(WinActionBase) if not m.startswith('__')}
        missing = self.EXPECTED_WINACTIONBASE_METHODS - actual
        assert not missing, f"WinActionBase missing methods: {missing}"

    def test_winaction_method_count(self):
        from videotrans.mainwin._actions import WinAction
        user_methods = [
            m for m in dir(WinAction)
            if not m.startswith('_') or m in ('_reset', '_check_all_done')
        ]
        user_methods = [
            m for m in user_methods
            if callable(getattr(WinAction, m, None))
        ]
        assert len(user_methods) >= 23, f"Expected >= 23 user methods, got {len(user_methods)}"

    def test_winactionbase_method_count(self):
        from videotrans.mainwin._actions_base import WinActionBase
        user_methods = [
            m for m in dir(WinActionBase)
            if not m.startswith('__')
            and callable(getattr(WinActionBase, m, None))
        ]
        assert len(user_methods) >= 24, f"Expected >= 24 user methods, got {len(user_methods)}"
