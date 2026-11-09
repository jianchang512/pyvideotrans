"""WorldRouter wiring and real SDK request/response handling, without a paid API call."""
import json

import pytest

pytest.importorskip('openai._client')
pytest.importorskip('httpx._transports.mock')

import httpx
from openai import OpenAI
from tenacity import stop_after_attempt, wait_none

from videotrans import get_class, translator
from videotrans.configure.config import app_cfg, params, settings
from videotrans.configure._app_params import AppParams
from videotrans.configure._app_settings import AppSettings
from videotrans.configure._default_params import channel_default_params
from videotrans.configure.constants import WORLDROUTER_MODELS
from videotrans.configure.excepts import StopTask, TranslateSrtError
from videotrans.translator import _openaicompat
from videotrans.translator._worldrouter import WorldRouter
from videotrans.ui.menu_list import MENU_CFG_TRANS


SOURCE = '1\n00:00:01,000 --> 00:00:02,000\n你好\n\n2\n00:00:03,000 --> 00:00:04,000\n世界'
TRANSLATED = '1\n00:00:01,000 --> 00:00:02,000\nHello\n\n2\n00:00:03,000 --> 00:00:04,000\nWorld'


def completion(content, finish_reason='stop'):
    return {
        'id': 'chatcmpl-test', 'object': 'chat.completion', 'created': 1,
        'model': 'deepseek-v4-flash',
        'choices': [{'index': 0, 'finish_reason': finish_reason,
                     'message': {'role': 'assistant', 'content': content}}],
    }


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch):
    monkeypatch.setattr(params, 'worldrouter_key', 'test-worldrouter-key')
    monkeypatch.setattr(params, 'worldrouter_model', 'deepseek-v4-flash')
    monkeypatch.setattr(params, 'worldrouter_max_token', 16384)
    monkeypatch.setattr(settings, 'aisendsrt', True)
    monkeypatch.setattr(settings, 'aitrans_temperature', 1.0)
    monkeypatch.setattr(app_cfg, 'exit_soft', False)
    monkeypatch.setattr(WorldRouter, '_set_proxy', lambda *a, **kw: None)
    monkeypatch.setattr(WorldRouter, 'signal', lambda *a, **kw: None)
    monkeypatch.setattr(_openaicompat.OpenAICampat._item_task.retry, 'wait', wait_none())
    monkeypatch.setattr(_openaicompat.OpenAICampat._item_task.retry, 'stop', stop_after_attempt(2))


@pytest.fixture
def api(monkeypatch):
    requests = []
    responses = []
    clients = []

    def handle(request):
        requests.append(request)
        status, body = responses.pop(0)
        return httpx.Response(status, json=body)

    def make_client(**kwargs):
        client = OpenAI(**kwargs, max_retries=0,
                        http_client=httpx.Client(transport=httpx.MockTransport(handle)))
        clients.append(client)
        return client

    monkeypatch.setattr(_openaicompat, 'OpenAI', make_client)
    yield requests, responses
    for client in clients:
        client.close()


def adapter():
    return WorldRouter(translate_type=translator.WORLDROUTER_INDEX, is_test=True,
                       source_code='Chinese', target_code='English', common_target_code='en')


def test_registration_and_defaults():
    channel = translator.ID_NAME_DICT[translator.WORLDROUTER_INDEX]
    assert get_class(translator.WORLDROUTER_INDEX, 'translator', translator.ID_NAME_DICT) is WorldRouter
    assert channel.name == 'WorldRouter'
    assert channel.key_name == 'worldrouter_key'
    assert channel.win == 'worldrouter'
    assert translator.WORLDROUTER_INDEX in translator.AI_TRANS_CHANNELS
    assert ('worldrouter', 'WorldRouter', None) in MENU_CFG_TRANS
    defaults = channel_default_params('worldrouter')
    assert defaults['worldrouter_key'] == ''
    assert defaults['worldrouter_model'] in AppSettings._models_dict()['worldrouter_model'].split(',')


def test_config_round_trip(tmp_path):
    path = str(tmp_path / 'params.json')
    config = AppParams(_json_path=path)
    config['worldrouter_key'] = 'test-key'
    config['worldrouter_model'] = 'custom-model'
    config['worldrouter_max_token'] = 4096
    config.save()
    restored = AppParams(_json_path=path)
    assert restored.get('worldrouter_key') == 'test-key'
    assert restored.get('worldrouter_model') == 'custom-model'
    assert restored.get('worldrouter_max_token') == 4096


def test_model_list_upgrade_preserves_custom_models(tmp_path):
    path = tmp_path / 'cfg.json'
    path.write_text(json.dumps({'worldrouter_model': 'custom-model'}))
    restored = AppSettings(_json_path=str(path))
    assert restored.get('worldrouter_model').split(',') == WORLDROUTER_MODELS.split(',') + ['custom-model']


@pytest.mark.parametrize('full_srt', [False, True])
def test_translation_via_public_runner(api, monkeypatch, full_srt):
    requests, responses = api
    monkeypatch.setattr(settings, 'aisendsrt', full_srt)
    text = TRANSLATED if full_srt else 'Hello\nWorld'
    responses.append((200, completion(f'<think>internal</think><TRANSLATE_TEXT>{text}</TRANSLATE_TEXT>')))
    result = translator.run(
        translate_type=translator.WORLDROUTER_INDEX, source_code='zh-cn', target_code='en', is_test=True,
        text_list=[{'text': '你好', 'line': 1, 'time': '00:00:01,000 --> 00:00:02,000'},
                   {'text': '世界', 'line': 2, 'time': '00:00:03,000 --> 00:00:04,000'}],
    )
    assert [item['text'] for item in result] == ['Hello', 'World']
    assert [item['time'] for item in result] == ['00:00:01,000 --> 00:00:02,000', '00:00:03,000 --> 00:00:04,000']
    assert len(requests) == 1
    request = requests[0]
    assert request.method == 'POST'
    assert str(request.url) == 'https://inference-api.worldrouter.ai/v1/chat/completions'
    assert request.headers['authorization'] == 'Bearer test-worldrouter-key'
    body = json.loads(request.content)
    assert body['model'] == 'deepseek-v4-flash'
    assert body['max_tokens'] == 16384
    assert 'reasoning_effort' not in body  # Do not force vendor-specific reasoning settings.
    assert '{lang}' not in body['messages'][1]['content']
    assert ('00:00:01,000' in body['messages'][1]['content']) is full_srt


@pytest.mark.parametrize('output', [
    TRANSLATED.split('\n\n')[0],
    TRANSLATED.replace('00:00:03,000', '00:00:03,500'),
    TRANSLATED.replace('World', ''),
    'Hello\nWorld',
])
def test_rejects_missing_blocks_changed_times_and_plain_text(api, output):
    api[1].append((200, completion(output)))
    with pytest.raises(TranslateSrtError, match='block count and timestamps'):
        adapter()._item_task(SOURCE)


def test_rejects_text_line_count_mismatch(api, monkeypatch):
    monkeypatch.setattr(settings, 'aisendsrt', False)
    api[1].append((200, completion('Hello world')))
    with pytest.raises(TranslateSrtError, match='line count'):
        adapter()._item_task('你好\n世界')


def test_stops_on_truncated_output_without_retry(api):
    api[1].append((200, completion(TRANSLATED, 'length')))
    with pytest.raises(StopTask, match='token limit'):
        adapter()._item_task(SOURCE)
    assert len(api[0]) == 1


@pytest.mark.parametrize('body', [completion(None), completion('   '), {'choices': []}])
def test_empty_completion_has_useful_error(api, body):
    api[1].append((200, body))
    with pytest.raises(TranslateSrtError):
        adapter()._create_completion({'model': 'deepseek-v4-flash', 'messages': []})


def test_invalid_key_stops_without_retry_or_key_leak(api):
    api[1].append((401, {'error': {'message': 'Invalid API key', 'type': 'authentication_error'}}))
    with pytest.raises(StopTask) as error:
        adapter()._item_task(SOURCE)
    assert 'Invalid API key' in str(error.value)
    assert 'test-worldrouter-key' not in str(error.value)
    assert len(api[0]) == 1


def test_rate_limit_is_retried(api):
    api[1].extend([(429, {'error': {'message': 'Rate limited', 'type': 'rate_limit_error'}}),
                   (200, completion(TRANSLATED))])
    assert adapter()._item_task(SOURCE).strip() == TRANSLATED
    assert len(api[0]) == 2


def test_stop_does_not_send_a_request(api, monkeypatch):
    worker = adapter()
    monkeypatch.setattr(app_cfg, 'exit_soft', True)
    assert worker._item_task(SOURCE) == ''
    assert api[0] == []


def test_invalid_config_token_limit_uses_shared_fallback(monkeypatch):
    monkeypatch.setattr(params, 'worldrouter_max_token', 'invalid')
    assert adapter().max_tokens == 8192


def test_configured_key_is_redacted_from_logs():
    from videotrans.configure._redact import redact
    assert 'test-worldrouter-key' not in redact('worldrouter_key=test-worldrouter-key')
    assert 'test-worldrouter-key' not in repr(adapter())
