from types import SimpleNamespace

import pytest

from videotrans import translator
from videotrans.configure.config import app_cfg, params, settings
from videotrans.configure.excepts import StopTask
from videotrans.task.taskcfg import SrtItem
from videotrans.translator import _base
from videotrans.translator._localllm import LocalLLM

# six subtitle lines, two per request: three requests for a translation
LINES = [f"line {i}" for i in range(1, 7)]
TRANSLATION = [f"LINE {i}" for i in range(1, 7)]

SEND_SRT = pytest.mark.parametrize(
    "send_srt", [True, False], ids=["send-srt", "by-lines"]
)


@pytest.fixture
def translate(monkeypatch, tmp_path):
    """Translates LINES with the LocalLLM channel, whose API upper-cases each
    batch, and returns the translated texts and the number of requests sent."""
    # print progress messages instead of sending them to the GUI
    monkeypatch.setattr(app_cfg, "exec_mode", "cli")
    # the translation cache, kept for the whole test as tmp/translate_cache
    # is kept between runs of the app
    monkeypatch.setattr(_base, "TEMP_ROOT", tmp_path.as_posix())
    # the channel needs an API URL, though no request is sent
    monkeypatch.setattr(params, "localllm_api", "http://127.0.0.1:8000/v1")
    monkeypatch.setattr(settings, "trans_thread", 2)
    monkeypatch.setattr(settings, "aitrans_thread", 2)

    def run(send_srt, fail_at=None):
        sent = []

        def complete(self, kwargs):
            sent.append(kwargs)
            if len(sent) == fail_at:
                # as when the account runs out of balance
                raise StopTask("Insufficient balance")
            # the batch is in the prompt's last <INPUT> block
            prompt = kwargs["messages"][-1]["content"]
            batch = prompt.rsplit("<INPUT>", 1)[1].split("</INPUT>", 1)[0]
            message = SimpleNamespace(content=batch.strip().upper())
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

        monkeypatch.setattr(LocalLLM, "_create_completion", complete)
        # the "Send SRT" setting
        monkeypatch.setattr(settings, "aisendsrt", send_srt)
        items = [
            SrtItem(
                text=text,
                line=i + 1,
                time=f"00:00:{2 * i + 1:02},000 --> 00:00:{2 * i + 2:02},000",
            )
            for i, text in enumerate(LINES)
        ]
        result = LocalLLM(
            text_list=items,
            translate_type=translator.LOCALLLM_INDEX,
            source_code="en",
            target_code="French",
            wait_sec=0,
        ).run()
        return [it["text"] for it in result], len(sent)

    return run


@SEND_SRT
def test_retry_sends_only_the_batches_not_translated_yet(translate, send_srt):
    # the third request fails, after two batches were translated
    with pytest.raises(StopTask):
        translate(send_srt, fail_at=3)
    # Start again: the first two batches come from the translation cache
    assert translate(send_srt) == (TRANSLATION, 1)


@SEND_SRT
def test_same_subtitles_again_send_no_request(translate, send_srt):
    assert translate(send_srt) == (TRANSLATION, 3)
    assert translate(send_srt) == (TRANSLATION, 0)


def test_full_transcript_context_is_part_of_the_cache_key(translate, monkeypatch):
    monkeypatch.setattr(settings, "aitrans_context", False)
    assert translate(True) == (TRANSLATION, 3)
    # "Include Full Transcript Context in AI Translation" changes the SRT
    # prompt, so batches cached without it are translated again
    monkeypatch.setattr(settings, "aitrans_context", True)
    assert translate(True) == (TRANSLATION, 3)
    assert translate(True) == (TRANSLATION, 0)
