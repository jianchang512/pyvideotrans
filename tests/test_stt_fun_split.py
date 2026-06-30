import inspect
import os
import tempfile


class TestSTTFunImports:
    def test_openai_whisper_importable(self):
        from videotrans.process.stt_fun import openai_whisper
        assert callable(openai_whisper)

    def test_faster_whisper_importable(self):
        from videotrans.process.stt_fun import faster_whisper
        assert callable(faster_whisper)

    def test_pipe_asr_importable(self):
        from videotrans.process.stt_fun import pipe_asr
        assert callable(pipe_asr)

    def test_paraformer_importable(self):
        from videotrans.process.stt_fun import paraformer
        assert callable(paraformer)

    def test_qwen3asr_fun_importable(self):
        from videotrans.process.stt_fun import qwen3asr_fun
        assert callable(qwen3asr_fun)

    def test_funasr_mlt_importable(self):
        from videotrans.process.stt_fun import funasr_mlt
        assert callable(funasr_mlt)

    def test_write_log_importable(self):
        from videotrans.process.stt_fun import _write_log
        assert callable(_write_log)

    def test_remove_unwanted_characters_importable(self):
        from videotrans.process.stt_fun import _remove_unwanted_characters
        assert callable(_remove_unwanted_characters)

    def test_resegment_importable(self):
        from videotrans.process.stt_fun import _resegment
        assert callable(_resegment)

    def test_direct_submodule_imports(self):
        from videotrans.process._stt_openai import openai_whisper as a
        from videotrans.process._stt_faster import faster_whisper as b
        from videotrans.process._stt_pipe import pipe_asr as c
        from videotrans.process._stt_paraformer import paraformer as d
        from videotrans.process._stt_qwen import qwen3asr_fun as e
        from videotrans.process._stt_funasr import funasr_mlt as f
        from videotrans.process._stt_utils import _write_log, _remove_unwanted_characters, _resegment
        assert all(callable(x) for x in [a, b, c, d, e, f, _write_log, _remove_unwanted_characters, _resegment])


class TestFunctionSignatures:
    def test_openai_whisper_signature(self):
        from videotrans.process.stt_fun import openai_whisper
        sig = inspect.signature(openai_whisper)
        params = list(sig.parameters.keys())
        assert 'prompt' in params
        assert 'detect_language' in params
        assert 'model_name' in params
        assert 'logs_file' in params
        assert 'is_cuda' in params
        assert 'audio_file' in params
        assert 'device_index' in params
        assert sig.return_annotation is not inspect.Signature.empty

    def test_faster_whisper_signature(self):
        from videotrans.process.stt_fun import faster_whisper
        sig = inspect.signature(faster_whisper)
        params = list(sig.parameters.keys())
        assert 'prompt' in params
        assert 'detect_language' in params
        assert 'model_name' in params
        assert 'logs_file' in params
        assert 'is_cuda' in params
        assert 'audio_file' in params
        assert 'local_dir' in params
        assert 'compute_type' in params
        assert 'device_index' in params
        assert 'subtitle_srt' in params
        assert sig.return_annotation is not inspect.Signature.empty

    def test_pipe_asr_signature(self):
        from videotrans.process.stt_fun import pipe_asr
        sig = inspect.signature(pipe_asr)
        params = list(sig.parameters.keys())
        assert 'prompt' in params
        assert 'cut_audio_list' in params
        assert 'detect_language' in params
        assert 'model_name' in params
        assert 'logs_file' in params
        assert 'is_cuda' in params
        assert 'audio_file' in params
        assert 'local_dir' in params
        assert 'device_index' in params
        assert sig.return_annotation is not inspect.Signature.empty

    def test_paraformer_signature(self):
        from videotrans.process.stt_fun import paraformer
        sig = inspect.signature(paraformer)
        params = list(sig.parameters.keys())
        assert 'cut_audio_list' in params
        assert 'detect_language' in params
        assert 'model_name' in params
        assert 'logs_file' in params
        assert 'is_cuda' in params
        assert 'audio_file' in params
        assert 'max_speakers' in params
        assert 'device_index' in params
        assert 'hotword' in params
        assert sig.return_annotation is not inspect.Signature.empty

    def test_qwen3asr_fun_signature(self):
        from videotrans.process.stt_fun import qwen3asr_fun
        sig = inspect.signature(qwen3asr_fun)
        params = list(sig.parameters.keys())
        assert 'cut_audio_list' in params
        assert 'logs_file' in params
        assert 'is_cuda' in params
        assert 'audio_file' in params
        assert 'model_name' in params
        assert 'device_index' in params
        assert 'hotword' in params
        assert sig.return_annotation is not inspect.Signature.empty

    def test_funasr_mlt_signature(self):
        from videotrans.process.stt_fun import funasr_mlt
        sig = inspect.signature(funasr_mlt)
        params = list(sig.parameters.keys())
        assert 'cut_audio_list' in params
        assert 'detect_language' in params
        assert 'model_name' in params
        assert 'logs_file' in params
        assert 'is_cuda' in params
        assert 'audio_file' in params
        assert 'jianfan' in params
        assert 'max_speakers' in params
        assert 'device_index' in params
        assert 'hotword' in params
        assert sig.return_annotation is not inspect.Signature.empty


class TestRemoveUnwantedCharacters:
    def test_strips_angle_bracket_markers(self):
        from videotrans.process.stt_fun import _remove_unwanted_characters
        assert _remove_unwanted_characters('Hello <|en|> world') == 'Hello  world'
        assert _remove_unwanted_characters('测试<|zh|>文本') == '测试文本'
        assert _remove_unwanted_characters('no markers here') == 'no markers here'
        assert _remove_unwanted_characters('<|unk|><|noise|>text') == 'text'

    def test_preserves_normal_text(self):
        from videotrans.process.stt_fun import _remove_unwanted_characters
        assert _remove_unwanted_characters('abc 123 !@#') == 'abc 123 !@#'
        assert _remove_unwanted_characters('中文日文 Korean') == '中文日文 Korean'


class TestResegment:
    def test_short_segment_not_split(self):
        from videotrans.process.stt_fun import _resegment
        texts = [
            {
                'text': 'Hello world',
                'start': 0.0,
                'end': 1.0,
                'words': [
                    {'word': 'Hello', 'start': 0.0, 'end': 0.5},
                    {'word': 'world', 'start': 0.5, 'end': 1.0},
                ]
            }
        ]
        result = _resegment(texts, 'en', 6000)
        assert len(result) == 1
        assert result[0]['text'] == 'Hello world'
        assert result[0]['start_time'] == 0
        assert result[0]['end_time'] == 1000

    def test_chinese_text_no_spaces(self):
        from videotrans.process.stt_fun import _resegment
        texts = [
            {
                'text': '你好世界',
                'start': 0.0,
                'end': 1.0,
                'words': [
                    {'word': '你好', 'start': 0.0, 'end': 0.5},
                    {'word': '世界', 'start': 0.5, 'end': 1.0},
                ]
            }
        ]
        result = _resegment(texts, 'zh', 6000)
        assert len(result) == 1
        assert result[0]['text'] == '你好世界'

    def test_long_segment_with_punctuation_split(self):
        from videotrans.process.stt_fun import _resegment
        texts = [
            {
                'text': 'Hello world, this is a very long sentence that should be split.',
                'start': 0.0,
                'end': 8.0,
                'words': [
                    {'word': 'Hello', 'start': 0.0, 'end': 0.5},
                    {'word': 'world,', 'start': 0.6, 'end': 1.5},
                    {'word': 'this', 'start': 1.6, 'end': 2.0},
                    {'word': 'is', 'start': 2.1, 'end': 2.3},
                    {'word': 'a', 'start': 2.4, 'end': 2.5},
                    {'word': 'very', 'start': 2.6, 'end': 3.0},
                    {'word': 'long', 'start': 3.1, 'end': 3.5},
                    {'word': 'sentence', 'start': 3.6, 'end': 4.2},
                    {'word': 'that', 'start': 4.3, 'end': 4.6},
                    {'word': 'should', 'start': 4.7, 'end': 5.1},
                    {'word': 'be', 'start': 5.2, 'end': 5.3},
                    {'word': 'split.', 'start': 5.4, 'end': 6.0},
                ]
            }
        ]
        result = _resegment(texts, 'en', 3000)
        assert len(result) >= 2
        for item in result:
            assert item['end_time'] - item['start_time'] <= 3000

    def test_no_words_fallback(self):
        from videotrans.process.stt_fun import _resegment
        texts = [
            {
                'text': 'Some text without words field',
                'start': 0.0,
                'end': 2.0,
            }
        ]
        result = _resegment(texts, 'en', 6000)
        assert len(result) == 1
        assert result[0]['text'] == 'Some text without words field'


class TestWriteLog:
    def test_writes_to_file(self):
        from videotrans.process.stt_fun import _write_log
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            log_path = f.name
        try:
            _write_log(log_path, '{"type":"logs","text":"test message"}')
            content = open(log_path, 'r', encoding='utf-8').read()
            assert 'test message' in content
        finally:
            os.unlink(log_path)

    def test_writes_to_nonexistent_file(self):
        from videotrans.process.stt_fun import _write_log
        log_path = os.path.join(tempfile.gettempdir(), '_stt_test_nonexistent_dir', 'test.log')
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        try:
            _write_log(log_path, 'hello')
            content = open(log_path, 'r', encoding='utf-8').read()
            assert content == 'hello'
        finally:
            os.unlink(log_path)
            os.rmdir(os.path.dirname(log_path))


class TestProcessInitReExports:
    def test_process_init_exports(self):
        from videotrans.process import openai_whisper, faster_whisper, pipe_asr, paraformer, qwen3asr_fun, funasr_mlt
        assert all(callable(x) for x in [openai_whisper, faster_whisper, pipe_asr, paraformer, qwen3asr_fun, funasr_mlt])
