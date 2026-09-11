import json
import logging
import sys
from unittest import mock

from videotrans.configure._redact import RedactFilter, redact
from videotrans.configure.config import params, settings
from videotrans.recognition._base import BaseRecogn


class TestRedact:
    def test_query_bearer_and_known_formats(self):
        text = ("POST http://127.0.0.1:1188/translate?key=abcdef123456&x=1\n"
                "Authorization: Bearer abcdefghijklmnopqrstuvwxyz\n"
                "sk-abcdefghijklmnopqrstuvwxyz hf_abcdefghijklmnopqrstuvwxyz")
        result = redact(text)
        assert "abcdef123456" not in result
        assert "abcdefghijklmnopqrstuvwxyz" not in result
        assert "?key=***&x=1" in result

    def test_configured_secret_value(self):
        old = params.get('deeplx_key', '')
        params['deeplx_key'] = 'my-deeplx-secret-value'
        try:
            assert 'my-deeplx-secret-value' not in redact('failed: my-deeplx-secret-value')
        finally:
            params['deeplx_key'] = old

    def test_max_token_values_not_redacted(self):
        old = params.get('chatgpt_max_token', '')
        params['chatgpt_max_token'] = '12345678'
        try:
            assert redact('max 12345678') == 'max 12345678'
        finally:
            params['chatgpt_max_token'] = old

    def test_log_filter_redacts_message_and_traceback(self):
        record = logging.LogRecord('VideoTrans', logging.ERROR, __file__, 1, 'url=%s',
                                   ('http://h/?sk=abcdef123456',), None)
        try:
            raise ValueError('http://h/?key=zyxwvu987654')
        except ValueError:
            record.exc_info = sys.exc_info()
        assert RedactFilter().filter(record) is True
        assert 'abcdef123456' not in record.getMessage()
        assert 'zyxwvu987654' not in record.exc_text


class TestRecognitionBase:
    def test_cjk_job_does_not_mutate_shared_punctuation(self):
        from videotrans.configure import contants
        before = list(contants.PUNC_FLAGS)
        BaseRecogn(detect_language="zh-cn")
        assert contants.PUNC_FLAGS == before
        assert " " not in BaseRecogn(detect_language="en").flag

    def test_asr_wait_reads_current_setting(self):
        old = settings.get('asr_wait', 0)
        settings['asr_wait'] = 3
        try:
            assert BaseRecogn().asr_wait == 3
        finally:
            settings['asr_wait'] = old

    def test_stop_after_retry_nums_reads_setting_each_time(self):
        from videotrans.configure._retry import stop_after_retry_nums
        state = mock.Mock(attempt_number=2)
        old = settings.get('retry_nums', 1)
        try:
            settings['retry_nums'] = 3
            assert stop_after_retry_nums()(state) is False
            settings['retry_nums'] = 2
            assert stop_after_retry_nums()(state) is True
        finally:
            settings['retry_nums'] = old


def _xxl_cls():
    from videotrans.recognition import _xxl
    return next(v for v in vars(_xxl).values()
                if isinstance(v, type) and issubclass(v, BaseRecogn) and v is not BaseRecogn)


def test_xxl_parses_all_consecutive_lines(tmp_path):
    content = "\n".join([
        "[00:00.000 --> 00:01.500] one",
        "[00:01.500 --> 00:03.000] two",
        "[00:03.000 --> 00:04.000]  three ",
        "[01:00:04.000 --> 01:00:05.250] four",
    ]) + "\n"
    cls = _xxl_cls()
    out = tmp_path / "a.srt"
    cls._getsrt_from_stdout(cls, content, str(out))
    text = out.read_text(encoding='utf-8')
    assert text.count(" --> ") == 4
    assert "\nthree" in text
    assert "01:00:04,000 --> 01:00:05,250" in text


def test_recognapi_accepts_srt_string_and_keeps_url_case(tmp_path):
    from videotrans.recognition import _recognapi
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF")
    srt = "1\n00:00:00,000 --> 00:00:01,000\nhello\n\n2\n00:00:01,000 --> 00:00:02,000\nworld\n"
    resp = mock.Mock(headers={"Content-Type": "application/json"})
    resp.json.return_value = {"code": 0, "data": srt}
    old_url, old_key = params.get('recognapi_url', ''), params.get('recognapi_key', '')
    params['recognapi_url'] = 'http://127.0.0.1:9977/API/Recogn'
    params['recognapi_key'] = ''
    try:
        rec = _recognapi.APIRecogn(detect_language="en", audio_file=str(audio), cache_folder=str(tmp_path))
        assert rec.api_url == 'http://127.0.0.1:9977/API/Recogn'
        with mock.patch.object(_recognapi.requests, "post", return_value=resp), \
                mock.patch.object(rec, "signal"), mock.patch.object(rec, "_exit", return_value=False):
            raws = rec._exec()
    finally:
        params['recognapi_url'], params['recognapi_key'] = old_url, old_key
    assert [it['text'] for it in raws] == ['hello', 'world']


def test_ai302_diarize_speaker_ids_are_stable(tmp_path):
    from videotrans.recognition import _ai302
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF")
    segs = [{"start": i, "end": i + 1, "text": f"t{i}", "speaker": sp}
            for i, sp in enumerate(["A", "B", "A", "C", "C", None])]
    resp = mock.Mock()
    resp.json.return_value = {"segments": segs}
    rec = _ai302.AI302Recogn(detect_language="en", audio_file=str(audio), cache_folder=str(tmp_path))
    with mock.patch.object(_ai302.requests, "post", return_value=resp):
        raws = rec._diarize()
    assert len(raws) == 6
    speakers = json.loads((tmp_path / "speaker.json").read_text(encoding="utf-8"))
    assert speakers == ["spk0", "spk1", "spk0", "spk2", "spk2", "spk3"]


def test_ai302_gpt4o_uses_filename_field(tmp_path):
    from videotrans.recognition import _ai302
    chunk = tmp_path / "0.wav"
    chunk.write_bytes(b"RIFF")
    resp = mock.Mock()
    resp.json.return_value = {"text": "hello"}
    rec = _ai302.AI302Recogn(detect_language="en", cache_folder=str(tmp_path))
    rec.asr_wait = 0
    with mock.patch.object(rec, "cut_audio", return_value=[{"filename": str(chunk), "text": ""}]), \
            mock.patch.object(_ai302.requests, "post", return_value=resp):
        raws = rec._thrid_api()
    assert raws[0]["text"] == "hello"


def test_gemini_summary_uses_absolute_times(tmp_path):
    from videotrans.recognition import _gemini

    def word(text, start, end):
        return mock.Mock(text=text, start_offset=f"{start}s", end_offset=f"{end}s")

    chunks = [{"filename": "a", "start_time": 0}, {"filename": "b", "start_time": 300000}]
    rec = _gemini.GeminiRecogn(detect_language="en", cache_folder=str(tmp_path))
    rec.asr_wait = 0
    captured = {}

    def fake_resegment(texts, *args, **kwargs):
        captured['texts'] = texts
        return []

    with mock.patch.object(rec, "_cut", return_value=chunks), \
            mock.patch.object(rec, "_req", side_effect=[([word("a", 1, 2), word("b", 250, 251)], "a b"),
                                                        ([word("c", 3, 4)], "c")]), \
            mock.patch.object(rec, "signal"), \
            mock.patch.object(_gemini, "_resegment", side_effect=fake_resegment):
        rec._exec()
    summary = captured['texts'][0]
    assert summary['start'] == 1
    assert summary['end'] == 304
    assert summary['text'] == "a b c"


def test_qwen_flash_skips_segment_blocked_by_inspection(tmp_path):
    from videotrans.recognition import _qwen3asr
    files = []
    for i in range(2):
        f = tmp_path / f"{i}.wav"
        f.write_bytes(b"RIFF")
        files.append({"filename": str(f), "text": ""})
    blocked = mock.Mock(status_code=400, text='{"code":"DataInspectionFailed"}')
    ok = mock.Mock(status_code=200, text='{}')
    ok.json.return_value = {"output": {"text": "hello"}}
    with mock.patch.object(_qwen3asr.Qwen3ASRRecogn, "cut_audio", return_value=files):
        rec = _qwen3asr.Qwen3ASRRecogn(detect_language="zh-cn", model_name="fun-asr-flash-2026-06-15")
    rec.asr_wait = 0
    with mock.patch.object(_qwen3asr.requests, "post", side_effect=[blocked, ok]) as post, \
            mock.patch.object(rec, "signal"), mock.patch.object(rec, "_exit", return_value=False):
        raws = rec._audio_funasr_flash("sk-test", rec.model_name)
    assert [it["text"] for it in raws] == ["", "hello"]
    for call in post.call_args_list:
        assert "timeout" in call.kwargs
        assert "verify" not in call.kwargs


def test_glmasr_retries_on_rate_limit(tmp_path):
    from videotrans.recognition import _glmasr
    chunk = tmp_path / "0.wav"
    chunk.write_bytes(b"RIFF")
    limited = mock.Mock(status_code=429, text="limited")
    limited.json.return_value = {"error": {"code": "1302", "message": "rate limited"}}
    ok = mock.Mock(status_code=200)
    ok.json.return_value = {"text": " hi "}
    rec = _glmasr.GLMASRRecogn(detect_language="zh-cn")
    rec.asr_wait = 0
    with mock.patch.object(rec, "cut_audio", return_value=[{"filename": str(chunk), "text": ""}]), \
            mock.patch.object(_glmasr.requests, "post", side_effect=[limited, ok]), \
            mock.patch.object(_glmasr.time, "sleep"), \
            mock.patch.object(rec, "signal"), mock.patch.object(rec, "_exit", return_value=False):
        raws = rec._exec()
    assert raws[0]["text"] == "hi"


def test_is_input_api_names_actual_channel():
    from videotrans import recognition
    old = params.get('qwenmt_key', '')
    params['qwenmt_key'] = ''
    try:
        msg = recognition.is_input_api(recognition.QWEN3ASR, return_str=True)
    finally:
        params['qwenmt_key'] = old
    assert "Deepgram" not in msg
    assert "Qwen" in msg


def test_update_ffmpeg_selects_stable_build_and_checksum():
    from videotrans.task import update_ffmpeg as uf
    assert uf._stable_version("ffmpeg-n8.1-latest-win64-gpl-8.1.zip") == (8, 1)
    assert uf._stable_version("ffmpeg-n8.1-latest-win64-gpl-shared-8.1.zip") is None
    text = "aaa  ffmpeg-master-latest-win64-gpl.zip\nBBB  ffmpeg-n8.1-latest-win64-gpl-8.1.zip\n"
    assert uf._expected_sha256(text, "ffmpeg-n8.1-latest-win64-gpl-8.1.zip") == "bbb"
