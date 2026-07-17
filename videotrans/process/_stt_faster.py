# 语音识别，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
import json, traceback
from pathlib import Path
from typing import List, Tuple, Union
from videotrans.task.taskcfg import SrtItem
from videotrans.util import tools
from videotrans.configure.config import logger
from videotrans.process._stt_utils import _write_log, _resegment


def faster_whisper(
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
        local_dir=None,
        compute_type="default",
        beam_size=5,
        best_of=5,
        jianfan=False,
        audio_duration=0,
        temperature=None,
        hotwords=None,
        repetition_penalty=1.0,
        compression_ratio_threshold=2.2,
        device_index=0,  # gpu索引
        max_speech_ms=6000,
        subtitle_srt=None
) -> Tuple[Union[List[SrtItem], bool], Union[str, None]]:
    import zhconv
    from faster_whisper import WhisperModel, BatchedInferencePipeline

    raws = []
    if detect_language == 'fil':
        detect_language = 'tl'

    def _create_model(_compute_type):
        try:
            logger.debug(f'[faster_whisper]加载模型{model_name}: {is_cuda=},{_compute_type=}')
            model = WhisperModel(
                local_dir,
                device="cuda" if is_cuda else 'cpu',
                device_index=device_index if is_cuda else 0,
                compute_type=_compute_type
            )
            return model
        except Exception as e:
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
        if speech_timestamps and isinstance(speech_timestamps, str):
            speech_timestamps = json.loads(Path(speech_timestamps).read_text(encoding='utf-8'))
        last_end_time = audio_duration / 1000.0 if audio_duration > 0 else (speech_timestamps[-1][1] / 1000.0 if speech_timestamps else 0)

        try:
            # 1. 加载基础模型
            _write_log(logs_file, json.dumps({"type": "logs", "text": 'loading model'}))
            logger.debug(f'开始加载 faster-whisper模型{model_name},数据类型:{compute_type}')
            model = _create_model(compute_type)
        except Exception as e:
            error = traceback.format_exc()
            logger.error(f'[faster_whisper][{is_cuda=}]语音转录加载模型失败:{local_dir=}\n{error}')
            return False, f'{e},{error}'

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

        if speech_timestamps:

            _write_log(logs_file, json.dumps({"type": "logs", "text": 'Transcribe batch...'}))
            logger.debug(f'预先VAD处理后，将断句时间数据传给 BatchedInferencePipeline 批量识别,batch_size=4')
            # 4. 执行批量推理
            # 使用 batched_model.transcribe
            batched_model = BatchedInferencePipeline(model=model)

            # 3. 转换时间戳格式
            # BatchedInferencePipeline 需要 [{'start': start_sec, 'end': end_sec}, ...]
            clip_timestamps_dicts = [
                {"start": it[0] / 1000.0, "end": it[1] / 1000.0}
                for it in speech_timestamps
            ]
            segments, info = batched_model.transcribe(
                audio_file,
                batch_size=4,  #
                beam_size=beam_size,
                best_of=best_of,
                no_speech_threshold=no_speech_threshold,
                # vad_filter 必须为 False，否则 clip_timestamps 可能被忽略或产生冲突，
                vad_filter=False,
                clip_timestamps=clip_timestamps_dicts,  # 自定义分段
                condition_on_previous_text=condition_on_previous_text,
                word_timestamps=False,
                without_timestamps=True,
                temperature=temperature,
                hotwords=hotwords,
                repetition_penalty=repetition_penalty,
                compression_ratio_threshold=compression_ratio_threshold,
                language=detect_language.split('-')[0] if detect_language and detect_language != 'auto' else None,
                initial_prompt=prompt if prompt else None
            )
            i = 0
            logger.debug(f'faster-whisper模式下，预先使用VAD分割音频，对{model_name}模型返回的文字结果直接使用')
            for segment in segments:
                if segment.end > last_end_time:
                    continue
                text = segment.text
                if not text.strip():
                    continue
                i += 1
                s, e = int(segment.start * 1000), int(segment.end * 1000)
                if jianfan:
                    text = zhconv.convert(text, 'zh-hans')
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
        else:
            logger.debug(f'直接传递完整音频，由faster-whisper内部VAD处理，返回字级时间戳数据')
            _write_log(logs_file, json.dumps({"type": "logs", "text": 'Transcribe word_timestamps'}))
            segments, info = model.transcribe(
                audio_file,
                beam_size=beam_size,
                best_of=best_of,
                condition_on_previous_text=condition_on_previous_text,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=140, min_speech_duration_ms=0),
                no_speech_threshold=no_speech_threshold,
                # clip_timestamps="0",  # clip_timestamps,
                word_timestamps=True,
                # without_timestamps=False,
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
                _write_log(logs_file, json.dumps({"type": "subtitle", "text": f'[{i}] {segment.text}\n'}))

            logger.debug(f'faster-whisper模式下，对{model_name}模型返回的字级时间戳进行断句')
            if not texts:
                return False, "No transcription results returned. Please check the original audio/video or model and try again."
            raws = _resegment(texts, info.language, max_speech_ms, logs_file)
            if jianfan and raws:
                for it in raws:
                    it['text'] = zhconv.convert(it['text'], 'zh-hans')
            logger.debug('断句完毕返回结果')
        # 保存识别结果到临时目录下，防止进程崩溃后永久等待
        if subtitle_srt:
            Path(subtitle_srt).write_text("\n\n".join([f'{i+1}\n{it.startraw} --> {it.endraw}\n{it.text}' for i,it in enumerate(raws)]),encoding="utf-8")
            logger.debug(f'faster-whisper下已临时保存识别结果到 {subtitle_srt}，防止进程崩溃后永久等待')
        
        return raws,None
    except BaseException as e:
        msg = traceback.format_exc()
        logger.exception(e,exc_info=True)
        return False, f'{e}:{msg}'
