# -*- coding: utf-8 -*-
import traceback, time, json
from videotrans.configure.config import ROOT_DIR, logger
from pathlib import Path


def _assign_speakers(subtitles, diarizations):
    output = []
    for sub in subtitles:
        if len(sub) != 2 or sub[0] >= sub[1]:
            output.append("spk0")
            continue

        s_start, s_end = sub
        s_duration = s_end - s_start
        if s_duration <= 0:
            output.append("spk0")
            continue

        overlaps = {}
        for dia in diarizations:
            if len(dia) != 2 or len(dia[0]) != 2 or dia[0][0] >= dia[0][1]:
                continue

            d_start, d_end = dia[0]
            speaker = dia[1]

            overlap_start = max(s_start, d_start)
            overlap_end = min(s_end, d_end)
            overlap = max(0, overlap_end - overlap_start)

            if overlap > 0:
                if speaker in overlaps:
                    overlaps[speaker] += overlap
                else:
                    overlaps[speaker] = overlap

        if not overlaps:
            output.append("spk0")
            continue

        num_unique_speakers = len(overlaps)
        max_overlap = max(overlaps.values())
        best_speaker = max(overlaps, key=overlaps.get)

        if num_unique_speakers > 1:
            output.append(best_speaker)
        elif num_unique_speakers == 1:
            if max_overlap > 0.2 * s_duration:
                output.append(best_speaker)
            else:
                output.append("spk0")
    return output


def _map_speakers(diarizations):
    speaker_list = sorted(list(set(d['speaker'] for d in diarizations)))
    spk_map = {spk: f'spk{i}' for i, spk in enumerate(speaker_list)}
    for d in diarizations:
        d['speaker'] = spk_map.get(d['speaker'], 'spk0')
    logger.debug(f'原始说话人排序后：{speaker_list=}')
    logger.debug(f'映射为新说话人标识：{spk_map=}')
    return diarizations


def _normalize_diarizations(raw_output):
    """将原始说话人分离结果标准化为统一格式"""
    output = []
    speaker_list = set()
    for item in raw_output:
        speaker_list.add(item['speaker'])
        output.append({
            'times': [int(item['start'] * 1000), int(item['end'] * 1000)],
            'speaker': item['speaker']
        })
    speaker_list = sorted(list(speaker_list))
    spk_map = {spk: f'spk{i}' for i, spk in enumerate(speaker_list)}
    for d in output:
        d['speaker'] = spk_map.get(d['speaker'], 'spk0')
    logger.debug(f'原始说话人排序后：{speaker_list=}')
    logger.debug(f'映射为新说话人标识：{spk_map=}')
    return output


def _diarize_and_write(subtitles_file, diarizations, speak_file):
    """通用：读取字幕文件，将说话人分离结果分配到字幕，写入结果"""
    subtitles = json.loads(Path(subtitles_file).read_text(encoding='utf-8'))
    diar_list = [[d['times'], d['speaker']] for d in diarizations]
    output = _assign_speakers(subtitles, diar_list)
    if output:
        Path(speak_file).write_text(json.dumps(output), encoding='utf-8')
        return True, None
    return False, "0 speakers"


def cam_speakers(*, input_file, subtitles_file: str, speak_file: str, num_speakers=-1, is_cuda=False, logs_file=None,
                 device_index=0):
    from modelscope.pipelines import pipeline
    device = f"cuda:{device_index}" if is_cuda else "cpu"
    _st = time.time()
    logger.debug(f'开始说话人分离:使用阿里cam++模型')

    try:
        subtitles = json.loads(Path(subtitles_file).read_text(encoding='utf-8'))

        ans = pipeline(
            task='speaker-diarization',
            model='iic/speech_campplus_speaker-diarization_common',
            disable_update=True,
            disable_progress_bar=True,
            disable_log=True,
            device=device
        )
        result = ans(input_file, oracle_num=num_speakers, ignore_errors=True) if num_speakers > 1 else ans(input_file,
                                                                                                           ignore_errors=True)
        logger.debug(f'说话人分离原始返回结果:{result=}')
        diarizations = _normalize_diarizations(
            [{'start': it[0], 'end': it[1], 'speaker': f'spk{int(it[2])}'} for it in result['text']]
        )
        diar_list = [[d['times'], d['speaker']] for d in diarizations]
        output = _assign_speakers(subtitles, diar_list)
        logger.debug(f'说话人分离成功结束,识别出 {len(set(output))} 个说话人,耗时:{int(time.time() - _st)}s')
        if output:
            Path(speak_file).write_text(json.dumps(output), encoding='utf-8')
            return True, None
        return False, "0 speakers"
    except Exception as e:
        msg = traceback.format_exc()
        logger.exception(f'说话人分离失败{e}:{msg}', exc_info=True)
        return False, f'{e}{msg}'


def pyannote_speakers(*, input_file, subtitles_file: str, speak_file: str, num_speakers=-1, is_cuda=False,
                      logs_file=None,
                      device_index=0):
    import torch, pyannote.audio, torchaudio
    torch.serialization.add_safe_globals([
        torch.torch_version.TorchVersion,
        pyannote.audio.core.task.Specifications,
        pyannote.audio.core.task.Problem,
        pyannote.audio.core.task.Resolution
    ])
    from pyannote.audio import Pipeline

    def _get_diariz():
        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")

        if is_cuda:
            pipeline.to(torch.device(f"cuda:{device_index}"))

        waveform, sample_rate = torchaudio.load(input_file)
        if num_speakers > 0:
            diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate}, num_speakers=num_speakers)
        else:
            diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate})

        raw_output = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speaker = speaker.replace('SPEAKER_', '')
            raw_output.append({'start': turn.start, 'end': turn.end, 'speaker': f'spk{speaker}'})
        return _normalize_diarizations(raw_output)

    try:
        _st = time.time()
        logger.debug(f'开始说话人分离,使用 pyannote/speaker-diarization-3.1 模型')
        subtitles = json.loads(Path(subtitles_file).read_text(encoding='utf-8'))
        diarizations = _get_diariz()
        if not diarizations:
            return False, "Unkonw error"
        diar_list = [[d['times'], d['speaker']] for d in diarizations]
        output = _assign_speakers(subtitles, diar_list)
        logger.debug(f'说话人分离成功结束,识别出个 {len(set(output))} 说话人,耗时:{int(time.time() - _st)}s')
        if output:
            Path(speak_file).write_text(json.dumps(output), encoding='utf-8')
            return True, None
        return False, "0 speakers"
    except Exception as e:
        msg = traceback.format_exc()
        logger.exception(f'说话人分离出错{e}:{msg}', exc_info=True)
        return False, f'{e}{msg}'


def reverb_speakers(*, input_file, subtitles_file: str, speak_file: str, num_speakers=-1, is_cuda=False, logs_file=None,
                    device_index=0):
    import torch, pyannote.audio, torchaudio
    torch.serialization.add_safe_globals([
        torch.torch_version.TorchVersion,
        pyannote.audio.core.task.Specifications,
        pyannote.audio.core.task.Problem,
        pyannote.audio.core.task.Resolution
    ])
    from pyannote.audio import Pipeline

    def _get_diariz():
        pipeline = Pipeline.from_pretrained('Revai/reverb-diarization-v1')

        if is_cuda:
            pipeline.to(torch.device(f"cuda:{device_index}"))

        waveform, sample_rate = torchaudio.load(input_file)
        if num_speakers > 0:
            diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate}, num_speakers=num_speakers)
        else:
            diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate})

        raw_output = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speaker = speaker.replace('SPEAKER_', '')
            raw_output.append({'start': turn.start, 'end': turn.end, 'speaker': f'spk{speaker}'})
        return _normalize_diarizations(raw_output)

    try:
        _st = time.time()
        logger.debug(f'开始说话人分离,使用模型 Revai/reverb-diarization-v1')
        subtitles = json.loads(Path(subtitles_file).read_text(encoding='utf-8'))
        diarizations = _get_diariz()
        if not diarizations:
            return False, "Unknwo error"
        diar_list = [[d['times'], d['speaker']] for d in diarizations]
        output = _assign_speakers(subtitles, diar_list)
        logger.debug(f'说话人分离成功结束,识别出个 {len(set(output))} 说话人,耗时:{int(time.time() - _st)}s')
        if output:
            Path(speak_file).write_text(json.dumps(output), encoding='utf-8')
            return True, None
        return False, "0 speakers"
    except Exception as e:
        msg = traceback.format_exc()
        logger.exception(f'说话人分离出错{e}:{msg}', exc_info=True)
        return False, f'{e}{msg}'


def built_speakers(*, input_file, subtitles_file: str, speak_file: str, num_speakers=-1, language="zh", logs_file=None,
                   is_cuda=False):
    import librosa
    import soundfile as sf

    def resample_audio(audio, sample_rate, target_sample_rate):
        if sample_rate != target_sample_rate:
            audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=target_sample_rate)
            return audio, target_sample_rate
        return audio, sample_rate

    def init_speaker_diarization(language, num_speakers=-1):
        import sherpa_onnx
        segmentation_model = f"{ROOT_DIR}/models/onnx/seg_model.onnx"
        embedding_extractor_model = (
            f"{ROOT_DIR}/models/onnx/3dspeaker_speech_eres2net_large_sv_zh-cn_3dspeaker_16k.onnx" if language == 'zh' else f"{ROOT_DIR}/models/onnx/nemo_en_titanet_small.onnx"
        )
        if not Path(embedding_extractor_model).exists():
            raise RuntimeError('Not found speaker_diarization model')

        _cf = sherpa_onnx.OfflineSpeakerDiarizationConfig(
            segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
                pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                    model=segmentation_model
                ),
            ),
            embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(
                model=embedding_extractor_model
            ),
            clustering=sherpa_onnx.FastClusteringConfig(
                num_clusters=num_speakers, threshold=0.5
            ),
            min_duration_on=0.3,
            min_duration_off=0.5,
        )
        if not _cf.validate():
            raise RuntimeError(
                "Please check your config and make sure all required files exist"
            )

        return sherpa_onnx.OfflineSpeakerDiarization(_cf)

    def _progress_callback(num_processed_chunk: int, num_total_chunks: int) -> int:
        return int(num_processed_chunk / num_total_chunks * 100 if num_total_chunks > 0 else 0)

    def _get_diariz():
        audio, sample_rate = sf.read(input_file, dtype="float32", always_2d=True)
        audio = audio[:, 0]

        sd = init_speaker_diarization(language, num_speakers)

        target_sample_rate = sd.sample_rate
        audio, sample_rate = resample_audio(audio, sample_rate, target_sample_rate)

        if sample_rate != sd.sample_rate:
            raise RuntimeError(
                f"Expected samples rate: {sd.sample_rate}, given: {sample_rate}"
            )

        show_progress = True

        if show_progress:
            result = sd.process(audio, callback=_progress_callback).sort_by_start_time()
        else:
            result = sd.process(audio).sort_by_start_time()

        raw_output = []
        for r in result:
            raw_output.append({'start': r.start, 'end': r.end, 'speaker': f'spk{r.speaker}'})
        return _normalize_diarizations(raw_output)

    try:
        _st = time.time()
        logger.debug(f'开始说话人分离,使用内置模型 {language=},{num_speakers=}')
        subtitles = json.loads(Path(subtitles_file).read_text(encoding='utf-8'))
        diarizations = _get_diariz()
        if not diarizations:
            return False, 'Unknow error'
        diar_list = [[d['times'], d['speaker']] for d in diarizations]
        output = _assign_speakers(subtitles, diar_list)
        logger.debug(f'说话人分离成功结束,识别出个 {len(set(output))} 说话人,耗时：{int(time.time() - _st)}s')
        if output:
            Path(speak_file).write_text(json.dumps(output), encoding='utf-8')
            return True, None
        return False, "0 speakers"
    except Exception as e:
        msg = traceback.format_exc()
        logger.exception(f'分离说话人失败:{e}', exc_info=True)
        return False, f'{e}{msg}'
