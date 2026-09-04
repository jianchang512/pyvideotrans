# 语音识别，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
import json, traceback
from pathlib import Path
from typing import List, Tuple, Union

from videotrans.configure._paths import TEMP_ROOT
from videotrans.task.taskcfg import SrtItem
from videotrans.configure.config import logger, ROOT_DIR

def openai_whisper(
        *,
        prompt=None,
        detect_language=None,
        model_name=None,
        logs_file=None,
        is_cuda=False,
        no_speech_threshold=0.5,
        condition_on_previous_text=False,
        audio_file=None,
        jianfan=False,
        temperature=None,
        compression_ratio_threshold=2.2,
        device_index=0,  # gpu索引
        max_speech_ms=6000,
        min_speech_ms=3000,
        **kw
) -> Tuple[Union[List[SrtItem], bool], Union[str, None]]:
    import whisper,zhconv
    from videotrans.process._stt_utils import _write_log, _resegment
    device=kw.get('device_name','auto')
    if device=='auto':
        device=f"cuda:{device_index}" if is_cuda else 'cpu'

    if not Path(f'{ROOT_DIR}/models/{model_name}.pt').exists():
        msg = f'Model {model_name} will be automatically downloaded'
        _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))

    try:
        if not temperature:
            temperature = (
                0.0, 0.2, 0.4, 0.6, 0.8, 1.0
            )
        elif str(temperature).startswith('[') or str(temperature).startswith('('):
            temperature = tuple([float(i) for i in str(temperature)[1:-1].split(',')])
        else:
            temperature = float(temperature)

        msg = f"Loading {model_name} running on {device}"
        _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
        logger.debug(msg)

        model = whisper.load_model(
            model_name,
            device=device,
            download_root=ROOT_DIR + "/models"
        )

        if detect_language == 'fil':
            detect_language = 'tl'

        _write_log(logs_file, json.dumps({"type": "logs", "text": 'Transcribe word timestamps'}))
        segments = model.transcribe(
            audio_file,
            language=detect_language.split('-')[0] if detect_language != 'auto' else None,
            word_timestamps=True,
            no_speech_threshold=no_speech_threshold,
            initial_prompt=prompt if prompt else None,
            temperature=temperature,
            compression_ratio_threshold=compression_ratio_threshold,
            condition_on_previous_text=condition_on_previous_text
        )
        Path(f'{TEMP_ROOT}/detect_language_source_{kw.get("uuid")}.txt').write_text(segments['language'])
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
            _kw=dict(no_speech_threshold=no_speech_threshold,
            initial_prompt=prompt,
            temperature=temperature,
            compression_ratio_threshold=compression_ratio_threshold,
            condition_on_previous_text=condition_on_previous_text)
            msg=f"No human voice detected. Please confirm that human speech is present in the original file.\n{_kw=}\n{segments=}"
            logger.error(msg)
            return False, msg

        raws = _resegment(texts, segments['language'], max_speech_ms,min_speech_ms, logs_file)
        if jianfan and raws:
            for it in raws:
                it['text'] = zhconv.convert(it['text'], 'zh-hans')
        logger.debug(f'断句完毕，返回结果:{max_speech_ms=},{min_speech_ms=}')
        return raws, None
    except BaseException as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'
