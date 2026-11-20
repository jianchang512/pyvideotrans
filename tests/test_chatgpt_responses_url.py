from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from videotrans import translator, winform
from videotrans.configure._app_params import AppParams
from videotrans.configure.config import app_cfg, params, settings
from videotrans.translator import _base, _openaicompat
from videotrans.util import TestSrtTrans
from videotrans.util.help_misc import process_openai_api
from videotrans.winform import chatgpt

RESPONSES = "https://api.openai.com/v1/responses"
CHAT = "https://api.openai.com/v1"

# the URL typed in the API URL field of the ChatGPT window, the URL saved,
# and the endpoint the translation is then sent to: (base_url, endpoint)
URLS = pytest.mark.parametrize(
    "typed,saved,sent",
    [
        (RESPONSES, RESPONSES, (CHAT, "responses")),
        ("api.openai.com/v1/responses/", RESPONSES, (CHAT, "responses")),
        (
            "https://api.example.com/v1/responses",
            "https://api.example.com/v1/responses",
            ("https://api.example.com/v1", "responses"),
        ),
        ("", CHAT, (CHAT, "chat.completions")),
        (
            "https://api.openai.com/v1/chat/completions",
            CHAT,
            (CHAT, "chat.completions"),
        ),
    ],
    ids=[
        "openai-responses",
        "openai-responses-no-scheme",
        "third-party-responses",
        "empty",
        "openai-chat",
    ],
)


@pytest.fixture(autouse=True)
def _params(monkeypatch):
    # Save and Test write params.json: leave it as it is, and give the keys
    # of the ChatGPT window their values back afterwards
    monkeypatch.setattr(AppParams, "save", lambda self, data=None: None)
    for key in (
        "chatgpt_key",
        "chatgpt_api",
        "chatgpt_max_token",
        "chatgpt_model",
        "chatgpt_reasoning_effort",
    ):
        monkeypatch.setitem(params, key, params.get(key))
    # the thread that Test starts
    monkeypatch.setattr(TestSrtTrans, "TestSrtTrans", MagicMock())


def _click(monkeypatch, button, typed):
    """Opens the ChatGPT window with openwin(), a MagicMock standing in for
    it, fills it in and clicks Save or Test."""
    win = MagicMock()
    win.chatgpt_api.text.return_value = typed
    win.chatgpt_key.text.return_value = "sk-test"
    win.chatgpt_max_token.text.return_value = "8192"
    win.chatgpt_model.currentText.return_value = "gpt-5-pro"
    win.reasoning_effort.currentText.return_value = "high"
    monkeypatch.setattr(winform, "get_cls", lambda name: lambda: win)
    chatgpt.openwin()
    getattr(win, button).clicked.connect.call_args.args[0]()


@pytest.mark.parametrize(
    "button", ["set_chatgpt", "test_chatgpt"], ids=["save", "test"]
)
@URLS
def test_save_and_test_keep_the_url(monkeypatch, button, typed, saved, sent):
    _click(monkeypatch, button, typed)

    # the URL that the ChatGPT translator reads
    assert params["chatgpt_api"] == saved


@URLS
def test_translation_goes_to_the_endpoint_of_the_saved_url(
    monkeypatch, tmp_path, typed, saved, sent
):
    calls = []
    answer = "<TRANSLATE_TEXT>Hello, my friend.</TRANSLATE_TEXT>"

    class OpenAI:
        # records the requests instead of sending them
        def __init__(self, api_key=None, base_url=None):
            self.responses = SimpleNamespace(
                create=lambda **kwargs: self._send(base_url, "responses")
            )
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: self._send(base_url, "chat.completions")
                )
            )

        def _send(self, base_url, endpoint):
            calls.append((base_url, endpoint))
            if endpoint == "responses":
                return SimpleNamespace(output_text=answer)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=answer))]
            )

    monkeypatch.setattr(_openaicompat, "OpenAI", OpenAI)
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    # keep the translation cache out of the repo's tmp folder
    monkeypatch.setattr(_base, "TEMP_ROOT", tmp_path.as_posix())
    monkeypatch.setattr(settings, "aisendsrt", False)

    _click(monkeypatch, "set_chatgpt", typed)
    # what the Test button's thread runs (videotrans/util/TestSrtTrans.py)
    result = translator.run(
        translate_type=translator.CHATGPT_INDEX,
        text_list=[
            {
                "text": "你好啊我的朋友",
                "line": 1,
                "time": "00:00:00,000 --> 00:00:05,000",
            }
        ],
        target_code="en",
        source_code="zh-cn",
        is_test=True,
    )

    assert calls == [sent]
    assert result[0]["text"] == "Hello, my friend."


@pytest.mark.parametrize(
    "url,expected",
    [
        ("", CHAT),
        ("https://api.openai.com", CHAT),
        ("https://api.openai.com/v1/", CHAT),
        ("https://api.openai.com/v1/chat/completions", CHAT),
        (RESPONSES, RESPONSES),
        ("https://API.openai.com/v1/Responses", RESPONSES),
        ("https://api.example.com/v1/chat/completions", "https://api.example.com/v1"),
        ("api.example.com/v1/", "http://api.example.com/v1"),
        (
            "https://api.example.com/v1/responses",
            "https://api.example.com/v1/responses",
        ),
    ],
)
def test_process_openai_api(url, expected):
    assert process_openai_api(url) == expected
