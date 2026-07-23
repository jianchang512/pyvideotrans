# 语音识别，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
import json, traceback
from pathlib import Path
from typing import List, Tuple, Union
from videotrans.task.taskcfg import SrtItem
from videotrans.util import tools
from videotrans.configure.config import logger, ROOT_DIR, defaulelang
from videotrans.process._stt_utils import _write_log, _resegment


def openai_whisper(
        *,
        prompt=None,
        detect_language=None,
        model_name=None,
        logs_file=None,
        is_cuda=False,
        no_speech_threshold=0.5,
        condition_on_previous_text=False,
        speech_timestamps=None,
        audio_file=None,
        jianfan=False,
        audio_duration=0,
        temperature=None,
        compression_ratio_threshold=2.2,
        device_index=0,  # gpu索引
        max_speech_ms=6000
) -> Tuple[Union[List[SrtItem], bool], Union[str, None]]:
    import whisper,zhconv
    if not Path(f'{ROOT_DIR}/models/{model_name}.pt').exists():
        msg = f"模型 {model_name} 不存在，将自动下载 " if defaulelang == 'zh' else f'Model {model_name} does not exist and will be automatically downloaded'
    else:
        msg = f"loading {model_name}"
    _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))

    raws = []
    try:
        if speech_timestamps and isinstance(speech_timestamps, str):
            speech_timestamps = json.loads(Path(speech_timestamps).read_text(encoding='utf-8'))
        if not temperature:
            temperature = (
                0.0, 0.2, 0.4, 0.6, 0.8, 1.0
            )
        elif str(temperature).startswith('[') or str(temperature).startswith('('):
            temperature = tuple([float(i) for i in str(temperature)[1:-1].split(',')])
        else:
            temperature = float(temperature)

        model = whisper.load_model(
            model_name,
            device=f"cuda:{device_index}" if is_cuda else 'cpu',
            download_root=ROOT_DIR + "/models"
        )
        msg = f"Loaded {model_name}"
        _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))

        last_end_time = audio_duration / 1000.0 if audio_duration > 0 else (speech_timestamps[-1][1] / 1000.0 if speech_timestamps else 0)
        speech_timestamps_flat = []
        if detect_language == 'fil':
            detect_language = 'tl'
        if speech_timestamps:
            _write_log(logs_file, json.dumps({"type": "logs", "text": 'Transcribe batch...'}))
            for it in speech_timestamps:
                speech_timestamps_flat.extend([it[0] / 1000.0, it[1] / 1000.0])
            result = model.transcribe(
                audio_file,
                no_speech_threshold=no_speech_threshold,
                language=detect_language.split('-')[0] if detect_language != 'auto' else None,
                clip_timestamps=speech_timestamps_flat,
                initial_prompt=prompt if prompt else None,
                temperature=temperature,
                compression_ratio_threshold=compression_ratio_threshold,
                condition_on_previous_text=condition_on_previous_text
            )
            i = 0
            for segment in result['segments']:
                # 时间戳大于总时长，出错跳过
                if segment['end'] > last_end_time:
                    continue
                text = segment['text']
                if not text.strip():
                    continue
                i += 1
                if jianfan:
                    text = zhconv.convert(text, 'zh-hans')
                s, e = int(segment['start'] * 1000), int(segment['end'] * 1000)
                tmp = SrtItem(**{
                    'text': text,
                    'start_time': s,
                    'end_time': e
                })
                tmp['startraw'] = tools.ms_to_time_string(ms=tmp['start_time'])
                tmp['endraw'] = tools.ms_to_time_string(ms=tmp['end_time'])
                tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
                raws.append(tmp)
                _write_log(logs_file, json.dumps({"type": "subtitle", "text": f'[{i}] {text}\n'}))
            logger.debug(f'openai-whisper模式下，预先使用VAD分割音频，直接使用{model_name}模型返回的各个片段音频的文字结果')
        else:
            _write_log(logs_file, json.dumps({"type": "logs", "text": 'Transcribe word timestamps'}))
            segments = model.transcribe(
                audio_file,
                no_speech_threshold=no_speech_threshold,
                language=detect_language.split('-')[0] if detect_language != 'auto' else None,
                initial_prompt=prompt if prompt else None,
                temperature=temperature,
                word_timestamps=True,
                compression_ratio_threshold=compression_ratio_threshold,
                condition_on_previous_text=condition_on_previous_text
            )
            texts = []
            i = 0
            for segment in segments['segments']:
                i += 1
                texts.append({
                    "text": segment['text'],
                    "start": segment['start'],
                    "end": segment['end'],
                    "words": [{'word': it['word'], 'start': it['start'], 'end': it['end']} for it in segment['words']]
                })
                _write_log(logs_file, json.dumps({"type": "subtitle", "text": f'[{i}] {segment["text"]}\n'}))
            logger.debug(f'openai-whisper模式下，传递完整音频由模型{model_name} 输出字级时间戳')
            if not texts:
                logger.error(f'no texts:{segments=}')
                return False, "No transcription results returned. Please check the original audio/video or model and try again."
            logger.debug(f'对字级时间戳进行组合断句')
            raws = _resegment(texts, segments['language'], max_speech_ms, logs_file)
            if jianfan and raws:
                for it in raws:
                    it['text'] = zhconv.convert(it['text'], 'zh-hans')
            logger.debug('断句完毕，返回结果')
        return raws, None
    except BaseException as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'
