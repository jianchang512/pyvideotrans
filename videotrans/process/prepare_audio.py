import traceback, time, json
from videotrans.configure.config import ROOT_DIR, logger, settings
from pathlib import Path


# 1. 分离背景声和人声 https://k2-fsa.github.io/sherpa/onnx/source-separation/models.html#uvr
# 仅使用cpu，不使用gpu
def vocal_bgm(*, input_file, vocal_file, instr_file, logs_file=None, is_cuda=False, uvr_models="UVR-MDX-NET-Inst_HQ_4"):
    if uvr_models.startswith('spleeter'):
        return vocal_bgm_spleeter(input_file=input_file, vocal_file=vocal_file, instr_file=instr_file,
                                  logs_file=logs_file)
    """
    UVR for source separation.

     UVR model from
    https://github.com/k2-fsa/sherpa-onnx/releases/tag/source-separation-models

    """

    import numpy as np
    import sherpa_onnx
    import soundfile as sf

    def create_offline_source_separation():
        model = f"{ROOT_DIR}/models/onnx/{uvr_models}.onnx"

        if not Path(model).is_file():
            raise ValueError(f"{model} does not exist.")

        _cf = sherpa_onnx.OfflineSourceSeparationConfig(
            model=sherpa_onnx.OfflineSourceSeparationModelConfig(
                uvr=sherpa_onnx.OfflineSourceSeparationUvrModelConfig(
                    model=model,
                ),
                num_threads=int(settings.get('noise_separate_nums', 4)),
                debug=False,
                provider="cpu",
            )
        )
        if not _cf.validate():
            raise ValueError("Please check your config.")

        return sherpa_onnx.OfflineSourceSeparation(_cf)

    def load_audio(wav_file):
        samples, sample_rate = sf.read(wav_file, dtype="float32", always_2d=True)
        samples = np.transpose(samples)
        assert (
                samples.shape[1] > samples.shape[0]
        ), f"You should use (num_channels, num_samples). {samples.shape}"

        assert (
                samples.dtype == np.float32
        ), f"Expect np.float32 as dtype. Given: {samples.dtype}"

        return samples, sample_rate

    start = time.time()
    try:
        sp = create_offline_source_separation()
        samples, sample_rate = load_audio(input_file)
        samples = np.ascontiguousarray(samples)
        _write_log(logs_file, "vocals non_vocals...")
        output = sp.process(sample_rate=sample_rate, samples=samples)
        end = time.time()
        non_vocals = output.stems[0].data
        vocals = output.stems[1].data

        vocals = np.transpose(vocals)
        non_vocals = np.transpose(non_vocals)

        sf.write(vocal_file, vocals, samplerate=output.sample_rate)
        sf.write(instr_file, non_vocals, samplerate=output.sample_rate)

        elapsed_seconds = end - start
        _write_log(logs_file, f" use time:{elapsed_seconds:.3f}s")
        logger.debug(f'分离背景声和人声成功[{uvr_models}],耗时 {elapsed_seconds:.3f}s')
        return True, None
    except Exception as e:
        msg = traceback.format_exc()
        logger.exception(f"人声背景声分离失败{e}:{msg}", exc_info=True)
        return False, f'{e}{msg}'


def vocal_bgm_spleeter(*, input_file, vocal_file, instr_file, logs_file=None):
    import numpy as np
    import sherpa_onnx
    import soundfile as sf

    def create_offline_source_separation():
        # Please read the help message at the beginning of this file
        # to download model files
        vocals = f"{ROOT_DIR}/models/onnx/vocals.fp16.onnx"
        accompaniment = f"{ROOT_DIR}/models/onnx/accompaniment.fp16.onnx"
        config = sherpa_onnx.OfflineSourceSeparationConfig(
            model=sherpa_onnx.OfflineSourceSeparationModelConfig(
                spleeter=sherpa_onnx.OfflineSourceSeparationSpleeterModelConfig(
                    vocals=vocals,
                    accompaniment=accompaniment,
                ),
                num_threads=int(settings.get('noise_separate_nums', 4)),
                debug=False,
                provider="cpu",
            )
        )
        if not config.validate():
            raise ValueError("Please check your config.")

        return sherpa_onnx.OfflineSourceSeparation(config)

    def load_audio(wav_file):

        samples, sample_rate = sf.read(wav_file, dtype="float32", always_2d=True)
        samples = np.transpose(samples)
        # now samples is of shape (num_channels, num_samples)
        assert (
                samples.shape[1] > samples.shape[0]
        ), f"You should use (num_channels, num_samples). {samples.shape}"

        assert (
                samples.dtype == np.float32
        ), f"Expect np.float32 as dtype. Given: {samples.dtype}"

        return samples, sample_rate

    start = time.time()
    try:
        sp = create_offline_source_separation()
        samples, sample_rate = load_audio(input_file)
        samples = np.ascontiguousarray(samples)

        output = sp.process(sample_rate=sample_rate, samples=samples)
        end = time.time()

        assert len(output.stems) == 2, len(output.stems)

        vocals = output.stems[0].data
        non_vocals = output.stems[1].data
        vocals = np.transpose(vocals)
        non_vocals = np.transpose(non_vocals)
        sf.write(vocal_file, vocals, samplerate=output.sample_rate)
        sf.write(instr_file, non_vocals, samplerate=output.sample_rate)

        elapsed_seconds = end - start
        audio_duration = samples.shape[1] / sample_rate
        _write_log(logs_file, f" use time:{elapsed_seconds:.3f}s")
        logger.debug(f"分离背景声和人声成功[spleeter],耗时: {elapsed_seconds:.3f}s")
        return True, None
    except Exception as e:
        msg = traceback.format_exc()
        logger.exception(f"人声背景声分离失败{e}:{msg}", exc_info=True)
        return False, f'{e}{msg}'


# 2. 降噪
def remove_noise(*, input_file, output_file, is_cuda=False, logs_file=None, device_index=0):
    import numpy as np
    import sherpa_onnx, time
    import soundfile as sf
    from videotrans.util import tools

    _st = time.time()
    logger.debug(f'开始降噪，使用模型 dpdfnet4')

    def load_audio(filename: str):
        samples, sample_rate = sf.read(
            filename,
            always_2d=True,
            dtype="float32",
        )
        samples = np.ascontiguousarray(samples[:, 0])
        return samples, sample_rate

    try:
        config = sherpa_onnx.OfflineSpeechDenoiserConfig(
            model=sherpa_onnx.OfflineSpeechDenoiserModelConfig(
                dpdfnet=sherpa_onnx.OfflineSpeechDenoiserDpdfNetModelConfig(
                    model=f"{ROOT_DIR}/models/onnx/dpdfnet4.onnx",
                ),
                num_threads=int(settings.get('noise_separate_nums', 4)),
                debug=False,
                provider="cpu",
            )
        )

        assert config.validate(), config

        denoiser = sherpa_onnx.OfflineSpeechDenoiser(config)
        samples, sample_rate = load_audio(input_file)
        denoised = denoiser.run(samples, sample_rate)
        logger.debug(f'{input_file=}, {sample_rate=}, {denoised.sample_rate=}')
        tmp_name = Path(output_file).parent.as_posix() + f'/noise-{time.time()}.wav'
        sf.write(tmp_name, denoised.samples, denoised.sample_rate)
        tools.runffmpeg(['-y', '-i', tmp_name, '-af', "volume=1.5", output_file])
        logger.debug(f'降噪成功完成，耗时:{int(time.time() - _st)}s')
        return output_file, None
    except Exception as e:
        msg = traceback.format_exc()
        logger.exception(f'降噪失败{e}:{msg}', exc_info=True)
        return False, f'{e}{msg}'


def fix_punc(*, text_dict_file: str, is_cuda=False, logs_file=None, device_index=0):
    import sherpa_onnx
    model = f"{ROOT_DIR}/models/puntc/model.onnx"
    try:
        if not Path(model).is_file():
            raise ValueError(f"{model} does not exist")
        _st = time.time()
        logger.debug(f'开始标点恢复')
        # 反序列化 text_dict
        text_dict_obj = json.loads(Path(text_dict_file).read_text(encoding='utf-8'))

        config = sherpa_onnx.OfflinePunctuationConfig(
            model=sherpa_onnx.OfflinePunctuationModelConfig(ct_transformer=model),
        )

        punct = sherpa_onnx.OfflinePunctuation(config)

        _text_dict_obj = {}
        for line, text in text_dict_obj.items():
            text_with_punct = punct.add_punctuation(text)
            _text_dict_obj[line] = text_with_punct
        # 写回该文件
        Path(text_dict_file).write_text(json.dumps(_text_dict_obj), encoding="utf-8")
        logger.debug(f'标点恢复完成，耗时:{int(time.time() - _st)}s')
        return True, None
    except Exception as e:
        msg = traceback.format_exc()
        logger.exception(f'恢复标点失败{e}:{msg}', exc_info=True)
        return False, f'{e}{msg}'


# 4. ali_CAM阿里 说话人分离  https://modelscope.cn/models/iic/speech_campplus_speaker-diarization_common/files
def cam_speakers(*, input_file, subtitles_file: str, speak_file: str, num_speakers=-1, is_cuda=False, logs_file=None,
                 device_index=0):
    from modelscope.pipelines import pipeline
    device = f"cuda:{device_index}" if is_cuda else "cpu"
    _st = time.time()
    logger.debug(f'开始说话人分离:使用阿里cam++模型')

    try:
        # 从文件中读取所需要的字幕时间戳数据
        subtitles = json.loads(Path(subtitles_file).read_text(encoding='utf-8'))

        ans = pipeline(
            task='speaker-diarization',
            model='iic/speech_campplus_speaker-diarization_common',
            disable_update=True,
            disable_progress_bar=True,
            disable_log=True,
            device=device
        )
        # 如果有先验信息，输入实际的说话人数，会得到更准确的预测结果
        # result 类似 {'text': [[0.0, 2.04, 0], [4.18, 24.97, 0], [25.33, 81.0, 0], [81.0, 97.55, 1], [99.49, 141.11, 0], [142.41, 155.93, 0], [158.28, 190.34, 0]]}
        result = ans(input_file, oracle_num=num_speakers, ignore_errors=True) if num_speakers > 1 else ans(input_file,
                                                                                                           ignore_errors=True)
        # 整理为 [ [[start_ms,end_ms],"spk\d"],... ]
        logger.debug(f'说话人分离原始返回结果:{result=}')
        diarizations = [[[int(it[0] * 1000), int(it[1] * 1000)], f'spk{int(it[2])}'] for it in result['text']]
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

            overlaps = {}  # speaker -> total overlap (sum if multiple segments)
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
            best_speaker = max(overlaps, key=overlaps.get)  # gets the one with max overlap

            if num_unique_speakers > 1:
                # Assign to the one with max overlap, regardless of threshold
                output.append(best_speaker)
            elif num_unique_speakers == 1:
                # For single, check thresholds: >20% overall (covers >50% or 20%<x<=50%)
                if max_overlap > 0.2 * s_duration:
                    output.append(best_speaker)
                else:
                    output.append("spk0")
        logger.debug(f'说话人分离成功结束,识别出 {len(set(output))} 个说话人,耗时:{int(time.time() - _st)}s')
        if output:
            Path(speak_file).write_text(json.dumps(output), encoding='utf-8')
            return True, None
        return False, "0 speakers"
    except Exception as e:
        msg = traceback.format_exc()
        logger.exception(f'说话人分离失败{e}:{msg}', exc_info=True)
        return False, f'{e}{msg}'


# 4. 说话人分离，pyannote https://huggingface.co/pyannote/speaker-diarization-3.0
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
        # pyannote-audio==3.4.0
        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")

        if is_cuda:
            pipeline.to(torch.device(f"cuda:{device_index}"))

        # apply pretrained pipeline
        waveform, sample_rate = torchaudio.load(input_file)
        if num_speakers > 0:
            diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate}, num_speakers=num_speakers)
        else:
            diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate})

        output = []
        # 获取的说话人数字id可能很乱，并非顺序增长，需要重新整理为0-n递增
        speaker_list = set()
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speaker = speaker.replace('SPEAKER_', '')
            speaker_list.add(f'spk{speaker}')
            output.append([[int(turn.start * 1000), int(turn.end * 1000)], f'spk{speaker}'])
        speaker_list = sorted(list(speaker_list))

        # 映射
        spk_neworder_dict = {}
        for i, it in enumerate(speaker_list):
            spk_neworder_dict[it] = f'spk{i}'
        logger.debug(f'原始说话人排序后：{speaker_list=}')
        logger.debug(f'映射为新说话人标识：{spk_neworder_dict=}')
        for i, it in enumerate(output):
            output[i][1] = spk_neworder_dict.get(it[1], 'spk0')
        return output

    try:
        _st = time.time()
        logger.debug(f'开始说话人分离,使用 pyannote/speaker-diarization-3.1 模型')
        # 从文件中读取所需要的字幕时间戳数据
        subtitles = json.loads(Path(subtitles_file).read_text(encoding='utf-8'))
        diarizations = _get_diariz()
        if not diarizations:
            return False, "Unkonw error"
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

            overlaps = {}  # speaker -> total overlap (sum if multiple segments)
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
            best_speaker = max(overlaps, key=overlaps.get)  # gets the one with max overlap

            if num_unique_speakers > 1:
                # Assign to the one with max overlap, regardless of threshold
                output.append(best_speaker)
            elif num_unique_speakers == 1:
                # For single, check thresholds: >20% overall (covers >50% or 20%<x<=50%)
                if max_overlap > 0.2 * s_duration:
                    output.append(best_speaker)
                else:
                    output.append("spk0")
        logger.debug(f'说话人分离成功结束,识别出个 {len(set(output))} 说话人,耗时:{int(time.time() - _st)}s')
        if output:
            Path(speak_file).write_text(json.dumps(output), encoding='utf-8')
            return True, None
        return False, "0 speakers"
    except Exception as e:
        msg = traceback.format_exc()
        logger.exception(f'说话人分离出错{e}:{msg}', exc_info=True)
        return False, f'{e}{msg}'


# 4. 说话人分离 reverb  https://huggingface.co/Revai/reverb-diarization-v1
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
        # pyannote-audio==3.4.0
        pipeline = Pipeline.from_pretrained('Revai/reverb-diarization-v1')

        if is_cuda:
            pipeline.to(torch.device(f"cuda:{device_index}"))

        # apply pretrained pipeline
        waveform, sample_rate = torchaudio.load(input_file)
        if num_speakers > 0:
            diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate}, num_speakers=num_speakers)
        else:
            diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate})

        output = []
        # 获取的说话人数字id可能很乱，并非顺序增长，需要重新整理为0-n递增
        speaker_list = set()
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speaker = speaker.replace('SPEAKER_', '')
            speaker_list.add(f'spk{speaker}')
            output.append([[int(turn.start * 1000), int(turn.end * 1000)], f'spk{speaker}'])
        speaker_list = sorted(list(speaker_list))

        # 映射
        spk_neworder_dict = {}
        for i, it in enumerate(speaker_list):
            spk_neworder_dict[it] = f'spk{i}'
        logger.debug(f'原始说话人排序后：{speaker_list=}')
        logger.debug(f'映射为新说话人标识：{spk_neworder_dict=}')

        for i, it in enumerate(output):
            output[i][1] = spk_neworder_dict.get(it[1], 'spk0')
        return output

    try:
        _st = time.time()
        logger.debug(f'开始说话人分离,使用模型 Revai/reverb-diarization-v1')
        # 从文件中读取所需要的字幕时间戳数据
        subtitles = json.loads(Path(subtitles_file).read_text(encoding='utf-8'))
        diarizations = _get_diariz()
        if not diarizations:
            return False, "Unknwo error"
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

            overlaps = {}  # speaker -> total overlap (sum if multiple segments)
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
            best_speaker = max(overlaps, key=overlaps.get)  # gets the one with max overlap

            if num_unique_speakers > 1:
                # Assign to the one with max overlap, regardless of threshold
                output.append(best_speaker)
            elif num_unique_speakers == 1:
                # For single, check thresholds: >20% overall (covers >50% or 20%<x<=50%)
                if max_overlap > 0.2 * s_duration:
                    output.append(best_speaker)
                else:
                    output.append("spk0")
        logger.debug(f'说话人分离成功结束,识别出个 {len(set(output))} 说话人,耗时:{int(time.time() - _st)}s')
        if output:
            Path(speak_file).write_text(json.dumps(output), encoding='utf-8')
            return True, None
        return False, "0 speakers"
    except Exception as e:
        msg = traceback.format_exc()
        logger.exception(f'说话人分离出错{e}:{msg}', exc_info=True)
        return False, f'{e}{msg}'


# 内置中英文说话人分离模型
# 仅使用cpu，不使用gpu
def built_speakers(*, input_file, subtitles_file: str, speak_file: str, num_speakers=-1, language="zh", logs_file=None,
                   is_cuda=False):
    import librosa
    import soundfile as sf
    def resample_audio(audio, sample_rate, target_sample_rate):
        """
        Resample audio to target sample rate using librosa
        """
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
                num_clusters=num_speakers, threshold=0.5  # cluster_threshold
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
        audio = audio[:, 0]  # only use the first channel

        # Since we know there are 4 speakers in the above test wave file, we use
        # num_speakers 4 here
        sd = init_speaker_diarization(language, num_speakers)

        # Resample audio to match the expected sample rate
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

        output = []
        # 获取的说话人数字id可能很乱，并非顺序增长，需要重新整理为0-n递增
        speaker_list = set()
        for r in result:
            speaker_list.add(f'spk{r.speaker}')
            output.append([[int(r.start * 1000), int(r.end * 1000)], f'spk{r.speaker}'])
        speaker_list = sorted(list(speaker_list))

        # 映射
        spk_neworder_dict = {}
        for i, it in enumerate(speaker_list):
            spk_neworder_dict[it] = f'spk{i}'
        logger.debug(f'原始说话人排序后：{speaker_list=}')
        logger.debug(f'映射为新说话人标识：{spk_neworder_dict=}')

        for i, it in enumerate(output):
            output[i][1] = spk_neworder_dict.get(it[1], 'spk0')

        return output

    try:
        _st = time.time()
        logger.debug(f'开始说话人分离,使用内置模型 {language=},{num_speakers=}')
        # 从文件中读取所需要的字幕时间戳数据
        subtitles = json.loads(Path(subtitles_file).read_text(encoding='utf-8'))
        # 根据选择使用内置或 pyannote 方式
        diarizations = _get_diariz()
        if not diarizations:
            return False, 'Unknow error'
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

            overlaps = {}  # speaker -> total overlap (sum if multiple segments)
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
            best_speaker = max(overlaps, key=overlaps.get)  # gets the one with max overlap

            if num_unique_speakers > 1:
                # Assign to the one with max overlap, regardless of threshold
                output.append(best_speaker)
            elif num_unique_speakers == 1:
                # For single, check thresholds: >20% overall (covers >50% or 20%<x<=50%)
                if max_overlap > 0.2 * s_duration:
                    output.append(best_speaker)
                else:
                    output.append("spk0")
        logger.debug(f'说话人分离成功结束,识别出个 {len(set(output))} 说话人,耗时：{int(time.time() - _st)}s')
        if output:
            Path(speak_file).write_text(json.dumps(output), encoding='utf-8')
            return True, None
        return False, "0 speakers"
    except Exception as e:
        msg = traceback.format_exc()
        logger.exception(f'分离说话人失败:{e}', exc_info=True)
        return False, f'{e}{msg}'


def _write_log(file=None, msg=None, type='logs'):
    if not file or not msg:
        return
    try:
        Path(file).write_text(json.dumps({"text": msg, "type": type}), encoding='utf-8')
    except Exception as e:
        logger.exception(f'写入新进程日志时出错{e}', exc_info=True)
