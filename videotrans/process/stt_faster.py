# 语音识别，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
import json, traceback
from pathlib import Path
from typing import List, Tuple, Union

from videotrans.configure._paths import TEMP_ROOT
from videotrans.task.taskcfg import SrtItem
from videotrans.configure.config import logger



def faster_whisper(
        *,
        prompt=None,
        detect_language=None,
        model_name=None,
        logs_file=None,
        is_cuda=False,
        no_speech_threshold=0.6,
        threshold=0.5,
        condition_on_previous_text=False,
        audio_file=None,
        local_dir=None,
        compute_type="default",
        beam_size=5,
        best_of=5,
        jianfan=False,
        audio_duration=0,
        temperature=None,
        hotwords=None,
        repetition_penalty=1.0,
        compression_ratio_threshold=2.4,
        max_speech_ms=6000,
        min_speech_ms=3000,
        subtitle_srt=None,
        **kw
) -> Tuple[Union[List[SrtItem], bool], Union[str, None]]:
    import zhconv
    from videotrans.process._stt_utils import _write_log,_resegment2,_resegment
    from videotrans.util._srt_parse import ms_to_time_string
    from faster_whisper import WhisperModel, BatchedInferencePipeline

    raws = []
    if detect_language == 'fil':
        detect_language = 'tl'
    device=kw.get('device_name','auto')
    if device == 'auto':
        device="cuda" if is_cuda else 'cpu'
    def _create_model(_compute_type):
        try:
            logger.debug(f'[faster_whisper]加载模型{model_name}: running on {device},{_compute_type=}')
            model = WhisperModel(
                local_dir,
                device=device,
                compute_type=_compute_type
            )
            return model
        except Exception as e:
            if 'Unable to open file' in str(e) or _compute_type == 'float32':
                raise
            # 对数据类型问题引发的错误重试
            # cuda下先尝试使用 float16
            if is_cuda and _compute_type != 'float16':
                logger.warning(f'faster-whisper CUDA下 加载模型失败，更改为 [float16] 类型后重试{e}')
                return _create_model('float16')


            # 如果cpu并且非 int8,先尝试 int8
            if not is_cuda and _compute_type != 'int8':
                logger.warning(f'faster-whisper CPU下 加载模型失败，更改为 [int8] 类型后重试{e}')
                return _create_model('int8')
            # 保底 float32
            if _compute_type != 'float32':
                logger.warning(f'faster-whisper  加载模型失败，更改为 [float32] 类型后重试, {is_cuda=}')
                return _create_model('float32')
            raise

    try:
        # 1. 加载基础模型
        _write_log(logs_file, json.dumps({"type": "logs", "text": f'Loading {model_name}'}))
        logger.debug(f'开始加载 faster-whisper模型{model_name},数据类型:{compute_type}')
        model = _create_model(compute_type)
    except Exception as e:
        error = traceback.format_exc()
        logger.error(f'[faster_whisper][{is_cuda=}]语音转录加载模型失败:{local_dir=}\n{error}')
        return False, f'{e},{error}'

    try:
        if not temperature:
            temperature = [
                0.0,
                0.2,
                0.4,
                0.6,
                0.8,
                1.0,
            ]
        elif str(temperature).startswith('[') or str(temperature).startswith('('):
            temperature = [float(i) for i in str(temperature)[1:-1].split(',')]
        else:
            temperature = float(temperature)

        logger.debug(f'直接传递完整音频，由faster-whisper内部VAD处理，返回字级时间戳数据')
        _write_log(logs_file, json.dumps({"type": "logs", "text": 'Transcribe word timestamps'}))
        segments, info = model.transcribe(
            audio_file,
            beam_size=beam_size,
            best_of=best_of,
            condition_on_previous_text=condition_on_previous_text,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=2000,
                min_speech_duration_ms=0,
                threshold=threshold
                ),
            no_speech_threshold=no_speech_threshold,
            word_timestamps=True,
            temperature=temperature,
            hotwords=hotwords,
            repetition_penalty=repetition_penalty,
            compression_ratio_threshold=compression_ratio_threshold,
            language=detect_language.split('-')[0] if detect_language and detect_language != 'auto' else None,
            initial_prompt=prompt if prompt else None
        )
        texts = []
        i = 0
        for segment in segments:
            i += 1
            texts.append({
                "text": segment.text,
                "start": segment.start,
                "end": segment.end,
                "words": [{'word': it.word, 'start': it.start, 'end': it.end} for it in segment.words]
            })
            _write_log(logs_file, json.dumps({"type": "subtitle", "text": f'Faster-whisper [{i}] {segment.text}\n'}))

        logger.debug(f'faster-whisper模式下，对{model_name}模型返回的字级时间戳进行断句')
        if not texts:
            _kw=dict(beam_size=beam_size,
                best_of=best_of,
                condition_on_previous_text=condition_on_previous_text,
                threshold=threshold,
                no_speech_threshold=no_speech_threshold,
                temperature=temperature,
                repetition_penalty=repetition_penalty,
                compression_ratio_threshold=compression_ratio_threshold,
                initial_prompt=prompt
            )
            msg=f"No human voice detected. Please confirm that human speech is present in the original file. [{info.duration_after_vad=}s].\n{_kw=}\n{info=}"
            logger.error(msg)
            return False, msg
        recogn2_max_speech,recogn2_min_speech=kw.get('recogn2_max_speech'), kw.get('recogn2_min_speech')
        if recogn2_max_speech and recogn2_min_speech:
            logger.debug(f'进入二次识别重新断句:{recogn2_min_speech=},{recogn2_max_speech=},{info.language=}')
            raws = _resegment2(texts, info.language, recogn2_max_speech,recogn2_min_speech, logs_file)
            logger.debug(f'二次识别断句完成')
        else:
            raws = _resegment(texts, info.language, max_speech_ms,min_speech_ms, logs_file)
            Path(f'{TEMP_ROOT}/detect_language_source_{kw.get("uuid")}.txt').write_text(info.language)
            logger.debug(f'断句完毕返回结果:{max_speech_ms=},{min_speech_ms=}')
        if jianfan and raws:
            for it in raws:
                it['text'] = zhconv.convert(it['text'], 'zh-hans')
        # 保存识别结果到临时目录下，防止进程崩溃后永久等待
        if subtitle_srt:
            Path(subtitle_srt).write_text("\n\n".join([f'{i+1}\n{it.startraw} --> {it.endraw}\n{it.text}' for i,it in enumerate(raws)]),encoding="utf-8")
            logger.debug(f'faster-whisper下已临时保存识别结果到 {subtitle_srt}，防止进程崩溃后永久等待')
        return raws,None
    except BaseException as e:
        msg = traceback.format_exc()
        logger.exception(e,exc_info=True)
        return False, f'{e}:{msg}'
