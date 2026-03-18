# -*- coding: utf-8 -*-
"""
Unit tests for the MiniMax translator module.

These tests verify the MiniMax translator class without requiring
the full pyvideotrans application or PySide6 GUI.
"""
import importlib
import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import patch, MagicMock

# Set up mock modules for pyvideotrans imports that require PySide6
_mock_modules = {
    'PySide6': MagicMock(),
    'PySide6.QtCore': MagicMock(),
    'PySide6.QtWidgets': MagicMock(),
    'PySide6.QtGui': MagicMock(),
}
for mod_name, mock_mod in _mock_modules.items():
    if mod_name not in sys.modules:
        sys.modules[mod_name] = mock_mod

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Mock the videotrans config modules
mock_config = types.ModuleType('videotrans.configure.config')
mock_config.tr = lambda *a, **kw: a[0] if a else ''
mock_config.params = {
    'minimax_key': 'test-key',
    'minimax_model': 'MiniMax-M2.7',
    'minimax_api': 'api.minimax.io',
}
mock_config.settings = {
    'aitrans_thread': '50',
    'aitrans_temperature': '0.2',
}
mock_config.app_cfg = MagicMock()
mock_config.app_cfg.exit_soft = False
mock_config.app_cfg.stoped_uuid_set = set()
mock_config.logger = MagicMock()
mock_config.ROOT_DIR = PROJECT_ROOT
mock_config.TEMP_DIR = '/tmp/pyvt_test'
mock_config.TEMP_ROOT = '/tmp/pyvt_test'
mock_config.HOME_DIR = '/tmp'
mock_config.defaulelang = 'en'

sys.modules['videotrans'] = types.ModuleType('videotrans')
sys.modules['videotrans.configure'] = types.ModuleType('videotrans.configure')
sys.modules['videotrans.configure.config'] = mock_config
sys.modules['videotrans.configure._except'] = types.ModuleType('videotrans.configure._except')
sys.modules['videotrans.configure._except'].NO_RETRY_EXCEPT = (Exception,)
sys.modules['videotrans.configure._except'].StopRetry = type('StopRetry', (Exception,), {})

mock_base_con = types.ModuleType('videotrans.configure._base')
mock_base_con.BaseCon = type('BaseCon', (), {
    '__init__': lambda self, **kw: None,
    '__post_init__': lambda self: None,
    '_signal': lambda self, **kw: None,
})
sys.modules['videotrans.configure._base'] = mock_base_con

mock_tools = types.ModuleType('videotrans.util')
sys.modules['videotrans.util'] = mock_tools

mock_tools_mod = types.ModuleType('videotrans.util.tools')
mock_tools_mod.get_prompt = lambda ainame, aisendsrt=True: 'Translate into {lang}:\n{batch_input}\n{context_block}'
mock_tools_mod.get_md5 = lambda s: 'mock_md5'
mock_tools_mod.cleartext = lambda s: s
mock_tools_mod.show_error = lambda s: None
mock_tools_mod.open_url = lambda url: None
sys.modules['videotrans.util.tools'] = mock_tools_mod
mock_tools.tools = mock_tools_mod

# Mock translator package - set up as a package with __path__
mock_translator = types.ModuleType('videotrans.translator')
mock_translator.AI_TRANS_CHANNELS = [23]
mock_translator.MINIMAX_INDEX = 23
mock_translator.__path__ = [os.path.join(PROJECT_ROOT, 'videotrans', 'translator')]
sys.modules['videotrans.translator'] = mock_translator

# Mock the _base module for translator
mock_base_trans_mod = types.ModuleType('videotrans.translator._base')
# Load BaseTrans from the real file using importlib
_base_spec = importlib.util.spec_from_file_location(
    'videotrans.translator._base',
    os.path.join(PROJECT_ROOT, 'videotrans', 'translator', '_base.py')
)
_base_module = importlib.util.module_from_spec(_base_spec)
sys.modules['videotrans.translator._base'] = _base_module
_base_spec.loader.exec_module(_base_module)

# Load the MiniMax translator
_minimax_spec = importlib.util.spec_from_file_location(
    'videotrans.translator._minimax',
    os.path.join(PROJECT_ROOT, 'videotrans', 'translator', '_minimax.py')
)
_minimax_module = importlib.util.module_from_spec(_minimax_spec)
sys.modules['videotrans.translator._minimax'] = _minimax_module
_minimax_spec.loader.exec_module(_minimax_module)
MiniMax = _minimax_module.MiniMax


class TestMiniMaxTranslatorInit(unittest.TestCase):
    """Test MiniMax translator initialization."""

    def _make_translator(self, **overrides):
        kwargs = {
            'text_list': [{'text': 'Hello', 'time': '00:00:01,000 --> 00:00:02,000', 'line': 1}],
            'target_language_name': 'Chinese',
            'source_code': 'en',
            'target_code': 'zh-cn',
            'uuid': 'test-uuid',
            'is_test': True,
            'translate_type': 23,
        }
        kwargs.update(overrides)
        return MiniMax(**kwargs)

    def test_default_model(self):
        t = self._make_translator()
        self.assertEqual(t.model_name, 'MiniMax-M2.7')

    def test_default_api_url(self):
        t = self._make_translator()
        self.assertEqual(t.api_url, 'https://api.minimax.io/v1')

    def test_custom_model(self):
        mock_config.params['minimax_model'] = 'MiniMax-M2.7-highspeed'
        try:
            t = self._make_translator()
            self.assertEqual(t.model_name, 'MiniMax-M2.7-highspeed')
        finally:
            mock_config.params['minimax_model'] = 'MiniMax-M2.7'

    def test_custom_api_url(self):
        mock_config.params['minimax_api'] = 'api.minimaxi.com'
        try:
            t = self._make_translator()
            self.assertEqual(t.api_url, 'https://api.minimaxi.com/v1')
        finally:
            mock_config.params['minimax_api'] = 'api.minimax.io'

    def test_api_key_loaded(self):
        t = self._make_translator()
        self.assertEqual(t.api_key, 'test-key')

    def test_prompt_contains_target_language(self):
        t = self._make_translator()
        self.assertIn('Chinese', t.prompt)


class TestMiniMaxTranslatorTask(unittest.TestCase):
    """Test MiniMax translator _item_task method."""

    def _make_translator(self, **overrides):
        kwargs = {
            'text_list': [{'text': 'Hello', 'time': '00:00:01,000 --> 00:00:02,000', 'line': 1}],
            'target_language_name': 'Chinese',
            'source_code': 'en',
            'target_code': 'zh-cn',
            'uuid': 'test-uuid',
            'is_test': True,
            'translate_type': 23,
        }
        kwargs.update(overrides)
        return MiniMax(**kwargs)

    @patch.object(_minimax_module, 'OpenAI')
    def test_item_task_with_list(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].finish_reason = 'stop'
        mock_response.choices[0].message.content = '<TRANSLATE_TEXT>你好\n世界</TRANSLATE_TEXT>'
        mock_client.chat.completions.create.return_value = mock_response

        t = self._make_translator()
        result = t._item_task(['Hello', 'World'])
        self.assertEqual(result, '你好\n世界')
        mock_openai_cls.assert_called_once_with(api_key='test-key', base_url='https://api.minimax.io/v1')

    @patch.object(_minimax_module, 'OpenAI')
    def test_item_task_with_string(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].finish_reason = 'stop'
        mock_response.choices[0].message.content = '你好世界'
        mock_client.chat.completions.create.return_value = mock_response

        t = self._make_translator()
        result = t._item_task('Hello World')
        self.assertEqual(result, '你好世界')

    @patch.object(_minimax_module, 'OpenAI')
    def test_item_task_uses_correct_model(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].finish_reason = 'stop'
        mock_response.choices[0].message.content = 'translated'
        mock_client.chat.completions.create.return_value = mock_response

        t = self._make_translator()
        t._item_task(['test'])
        call_kwargs = mock_client.chat.completions.create.call_args
        self.assertEqual(call_kwargs.kwargs['model'], 'MiniMax-M2.7')

    @patch.object(_minimax_module, 'OpenAI')
    def test_temperature_clamping(self, mock_openai_cls):
        """Test that temperature 0 is clamped to 0.01."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].finish_reason = 'stop'
        mock_response.choices[0].message.content = 'translated'
        mock_client.chat.completions.create.return_value = mock_response

        mock_config.settings['aitrans_temperature'] = '0'
        try:
            t = self._make_translator()
            t._item_task(['test'])
            call_kwargs = mock_client.chat.completions.create.call_args
            self.assertGreater(call_kwargs.kwargs['temperature'], 0)
            self.assertAlmostEqual(call_kwargs.kwargs['temperature'], 0.01)
        finally:
            mock_config.settings['aitrans_temperature'] = '0.2'

    @patch.object(_minimax_module, 'OpenAI')
    def test_item_task_raises_on_no_choices(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock(spec=[])
        mock_client.chat.completions.create.return_value = mock_response

        t = self._make_translator()
        with self.assertRaises(RuntimeError):
            t._item_task(['test'])

    @patch.object(_minimax_module, 'OpenAI')
    def test_item_task_raises_on_empty_content(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].finish_reason = 'stop'
        mock_response.choices[0].message.content = None
        mock_client.chat.completions.create.return_value = mock_response

        t = self._make_translator()
        with self.assertRaises(RuntimeError):
            t._item_task(['test'])

    @patch.object(_minimax_module, 'OpenAI')
    def test_translate_text_extraction(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].finish_reason = 'stop'
        mock_response.choices[0].message.content = 'Preamble\n<TRANSLATE_TEXT>actual translation</TRANSLATE_TEXT>\nepilogue'
        mock_client.chat.completions.create.return_value = mock_response

        t = self._make_translator()
        result = t._item_task(['test'])
        self.assertEqual(result, 'actual translation')

    @patch.object(_minimax_module, 'OpenAI')
    def test_result_without_translate_text_tags(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].finish_reason = 'stop'
        mock_response.choices[0].message.content = '你好世界'
        mock_client.chat.completions.create.return_value = mock_response

        t = self._make_translator()
        result = t._item_task(['test'])
        self.assertEqual(result, '你好世界')

    @patch.object(_minimax_module, 'OpenAI')
    def test_system_message_sent(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].finish_reason = 'stop'
        mock_response.choices[0].message.content = 'translated'
        mock_client.chat.completions.create.return_value = mock_response

        t = self._make_translator()
        t._item_task(['test'])
        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs['messages']
        self.assertEqual(messages[0]['role'], 'system')
        self.assertIn('Translation Engine', messages[0]['content'])


class TestMiniMaxRegistration(unittest.TestCase):
    """Test MiniMax translator registration constants."""

    def test_minimax_index_defined(self):
        self.assertEqual(mock_translator.MINIMAX_INDEX, 23)

    def test_minimax_in_ai_channels(self):
        self.assertIn(23, mock_translator.AI_TRANS_CHANNELS)


if __name__ == '__main__':
    unittest.main()
