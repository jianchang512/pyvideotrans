# 语音识别前进行各项处理，单独进程实现
# 返回元组
# 失败：第一个值为 False，第二个值存储失败原因
# 成功，第一个返回数据，不需要数据时返回True，第二个值为None


import traceback
def _write_log(file=None,msg=None,type='logs'):
    if not file or not msg:
        return
    from pathlib import Path
    import json
    from videotrans.configure import config
    try:
        Path(file).write_text(json.dumps({"text":msg,"type":type}),encoding='utf-8')
    except Exception as e:
        config.logger.exception(f'写入新进程日志时出错',exc_info=True)

# 1. 分离背景声和人声 https://k2-fsa.github.io/sherpa/onnx/source-separation/models.html#uvr
# 仅使用cpu，不使用gpu
def vocal_bgm(*, input_file, vocal_file, instr_file, TEMP_DIR=None,logs_file=None,is_cuda=False):
    """
    UVR for source separation.

     UVR model from
    https://github.com/k2-fsa/sherpa-onnx/releases/tag/source-separation-models

    """
    import time, torch, shutil, os
    from videotrans.configure import config as cfg
    from pathlib import Path
    import numpy as np
    import sherpa_onnx
    import soundfile as sf

    def create_offline_source_separation():
        model = f"{cfg.ROOT_DIR}/models/onnx/UVR-MDX-NET-Inst_HQ_4.onnx"

        if not Path(model).is_file():
            raise ValueError(f"{model} does not exist.")

        config = sherpa_onnx.OfflineSourceSeparationConfig(
            model=sherpa_onnx.OfflineSourceSeparationModelConfig(
                uvr=sherpa_onnx.OfflineSourceSeparationUvrModelConfig(
                    model=model,
                ),
                num_threads=4,
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
        assert (
                samples.shape[1] > samples.shape[0]
        ), f"You should use (num_channels, num_samples). {samples.shape}"

        assert (
                samples.dtype == np.float32
        ), f"Expect np.float32 as dtype. Given: {samples.dtype}"

        return samples, sample_rate
    sp=None
    try:
        sp = create_offline_source_separation()
        samples, sample_rate = load_audio(input_file)
        samples = np.ascontiguousarray(samples)
        _write_log(logs_file,"vocals non_vocals...")
        start = time.time()
        output = sp.process(sample_rate=sample_rate, samples=samples)
        end = time.time()
        non_vocals = output.stems[0].data
        vocals = output.stems[1].data

        vocals = np.transpose(vocals)
        non_vocals = np.transpose(non_vocals)

        sf.write(vocal_file, vocals, samplerate=output.sample_rate)
        sf.write(instr_file, non_vocals, samplerate=output.sample_rate)

        elapsed_seconds = end - start
        _write_log(logs_file,f" use time:{elapsed_seconds}s")
        return True,None
    except Exception as e:
        msg=traceback.format_exc()
        cfg.logger.exception(f"人声背景声分离失败:{msg}", exc_info=True)
        return False,msg
    finally:
        try:
            del sp
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
        except:
            pass


# 2. 降噪 https://modelscope.cn/models/iic/speech_frcrn_ans_cirm_16k
def remove_noise(*, input_file, output_file, TEMP_DIR=None, is_cuda=False,logs_file=None,device_index=0):
    import torch, os, shutil, time
    from pathlib import Path
    from videotrans.configure import config
    from videotrans.util import tools
    from modelscope.pipelines import pipeline
    from modelscope.utils.constant import Tasks
    import platform
    if platform.system() == 'Darwin' and torch.backends.mps.is_available():
        device="mps"
    else:
        device = f"cuda:{device_index}" if is_cuda else "cpu"
    _st=time.time()
    config.logger.info('开始语音降噪')
    ans = None
    result = None
    tmp_name = Path(output_file).parent.as_posix() + f'/noise-{time.time()}.wav'
    try:
        ans = pipeline(
            Tasks.acoustic_noise_suppression,
            model='iic/speech_frcrn_ans_cirm_16k',
            disable_update=True,
            disable_progress_bar=True,
            disable_log=True,
            device=device
        )
        result = ans(input_file, output_path=tmp_name, disable_pbar=True)
        tools.runffmpeg(['-y', '-i', tmp_name, '-af', "volume=2.0,alimiter=limit=1.0", output_file])
        config.logger.info(f'降噪成功完成，耗时:{int(time.time()-_st)}s')
        return output_file,None
    except Exception as e:
        msg=traceback.format_exc()
        config.logger.exception(f'降噪失败:{msg}', exc_info=True)
        return False,msg
    finally:
        try:
            del ans
            del result
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
        except Exception:
            pass


# 3. 恢复标点 https://modelscope.cn/models/iic/punc_ct-transformer_cn-en-common-vocab471067-large
def fix_punc(*, text_dict, TEMP_DIR=None, is_cuda=False,logs_file=None,device_index=0):
    import torch, os, shutil, time
    from pathlib import Path
    from videotrans.configure import config
    from modelscope.pipelines import pipeline
    from modelscope.utils.constant import Tasks
    import platform
    if platform.system() == 'Darwin' and torch.backends.mps.is_available():
        device="mps"
    else:
        device = f"cuda:{device_index}" if is_cuda else "cpu"
    result = None
    ans = None

    try:
        _st=time.time()
        config.logger.debug(f'开始标点恢复')
        ans = pipeline(
            task=Tasks.punctuation,
            model='iic/punc_ct-transformer_cn-en-common-vocab471067-large',
            model_revision="v2.0.4",
            disable_update=True,
            disable_progress_bar=True,
            disable_log=True,
            device=device
        )
        _str = "\n".join([f'{line}\t{it}' for line, it in text_dict.items()])
        tmp_name = f'{TEMP_DIR}/fix_flag-{time.time()}.txt'
        Path(tmp_name).write_text(_str, encoding='utf-8')
        result = ans(tmp_name, disable_pbar=True)
        for it in result:
            text_dict[it["key"]] = it['text']
        config.logger.debug(f'标点恢复完成，耗时:{int(time.time()-_st)}s')
        return text_dict,None
    except Exception as e:
        msg=traceback.format_exc()
        config.logger.exception(f'恢复标点失败:{msg}', exc_info=True)
        return False,msg
    finally:
        try:
            del ans
            del result
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
        except Exception:
            pass


# 4. ali_CAM阿里 说话人分离  https://modelscope.cn/models/iic/speech_campplus_speaker-diarization_common/files
def cam_speakers(*, input_file, subtitles, num_speakers=-1, TEMP_DIR=None, is_cuda=False,logs_file=None,device_index=0):
    import torch, os, shutil, time
    from pathlib import Path
    from videotrans.configure import config
    from modelscope.pipelines import pipeline
    import platform
    if platform.system() == 'Darwin' and torch.backends.mps.is_available():
        device="mps"
    else:
        device = f"cuda:{device_index}" if is_cuda else "cpu"
    _st=time.time()
    config.logger.debug(f'开始说话人分离:使用阿里cam++模型')
    result = None
    ans = None
    try:
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
        config.logger.debug(f'说话人分离原始返回结果:{result=}')
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

        config.logger.debug(f'说话人分离成功结束,识别出个 {len(set(output))} 说话人,耗时:{int(time.time()-_st)}s')
        return output,None
    except Exception as e:
        msg=traceback.format_exc()
        config.logger.exception(f'说话人分离失败:{msg}', exc_info=True)
        return False,msg
    finally:
        try:
            del ans
            del result
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
        except Exception:
            pass


# 4. 说话人分离，pyannote https://huggingface.co/pyannote/speaker-diarization-3.0
def pyannote_speakers(*, input_file, subtitles, num_speakers=-1, TEMP_DIR=None, is_cuda=False,logs_file=None,device_index=0):
    import torch, pyannote.audio, torchaudio, os, shutil,time
    torch.serialization.add_safe_globals([
        torch.torch_version.TorchVersion,
        pyannote.audio.core.task.Specifications,
        pyannote.audio.core.task.Problem,
        pyannote.audio.core.task.Resolution
    ])
    from pyannote.audio import Pipeline
    from pathlib import Path
    from videotrans.configure import config

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
        config.logger.debug(f'原始说话人排序后：{speaker_list=}')
        config.logger.debug(f'映射为新说话人标识：{spk_neworder_dict=}')
        for i, it in enumerate(output):
            output[i][1] = spk_neworder_dict.get(it[1], 'spk0')
        return output

    try:
        _st=time.time()
        config.logger.debug(f'开始说话人分离,使用 pyannote/speaker-diarization-3.1 模型')
        diarizations = _get_diariz()
        if not diarizations:
            return False,"Unkonw error"
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

        config.logger.debug(f'说话人分离成功结束,识别出个 {len(set(output))} 说话人,耗时:{int(time.time()-_st)}s')
        return output,None
    except Exception as e:
        msg=traceback.format_exc()
        config.logger.exception(f'说话人分离出错:{msg}', exc_info=True)
        return False,msg
    finally:
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
        except Exception:
            pass


# 4. 说话人分离 reverb  https://huggingface.co/Revai/reverb-diarization-v1
def reverb_speakers(*, input_file, subtitles, num_speakers=-1, TEMP_DIR=None, is_cuda=False,logs_file=None,device_index=0):
    import torch, pyannote.audio, torchaudio, os, shutil,time
    torch.serialization.add_safe_globals([
        torch.torch_version.TorchVersion,
        pyannote.audio.core.task.Specifications,
        pyannote.audio.core.task.Problem,
        pyannote.audio.core.task.Resolution
    ])
    from pyannote.audio import Pipeline
    from pathlib import Path
    from videotrans.configure import config

    def _get_diariz():
        # pyannote-audio==3.4.0
        pipeline = Pipeline.from_pretrained("Revai/reverb-diarization-v1")

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
        config.logger.debug(f'原始说话人排序后：{speaker_list=}')
        config.logger.debug(f'映射为新说话人标识：{spk_neworder_dict=}')

        for i, it in enumerate(output):
            output[i][1] = spk_neworder_dict.get(it[1], 'spk0')
        return output

    try:
        _st=time.time()
        config.logger.debug(f'开始说话人分离,使用模型 Revai/reverb-diarization-v1')
        diarizations = _get_diariz()
        if not diarizations:
            return False,"Unknwo error"
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

        config.logger.debug(f'说话人分离成功结束,识别出个 {len(set(output))} 说话人,耗时:{int(time.time()-_st)}s')
        return output,None
    except Exception as e:
        msg=traceback.format_exc()
        config.logger.exception(f'说话人分离出错:{msg}', exc_info=True)
        return False,msg
    finally:
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
        except Exception:
            pass


# 内置中英文说话人分离模型
# 仅使用cpu，不使用gpu
def built_speakers(*, input_file, subtitles, num_speakers=-1, language="zh", TEMP_DIR=None,logs_file=None,is_cuda=False):
    from pathlib import Path
    from videotrans.configure import config as cfg
    import torch
    import os, shutil,time
    import librosa
    import soundfile as sf

    def resample_audio(audio, sample_rate, target_sample_rate):
        """
        Resample audio to target sample rate using librosa
        """
        if sample_rate != target_sample_rate:
            print(f"Resampling audio from {sample_rate}Hz to {target_sample_rate}Hz...")
            audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=target_sample_rate)
            print(f"Resampling completed. New audio shape: {audio.shape}")
            return audio, target_sample_rate
        return audio, sample_rate

    def init_speaker_diarization(language, num_speakers=-1):
        import sherpa_onnx
        segmentation_model = f"{cfg.ROOT_DIR}/models/onnx/seg_model.onnx"
        embedding_extractor_model = (
            f"{cfg.ROOT_DIR}/models/onnx/3dspeaker_speech_eres2net_large_sv_zh-cn_3dspeaker_16k.onnx" if language == 'zh' else f"{cfg.ROOT_DIR}/models/onnx/nemo_en_titanet_small.onnx"
        )
        if not Path(embedding_extractor_model).exists():
            raise RuntimeError('Not found speaker_diarization model')

        config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
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
        if not config.validate():
            raise RuntimeError(
                "Please check your config and make sure all required files exist"
            )

        return sherpa_onnx.OfflineSpeakerDiarization(config)

    def _progress_callback(num_processed_chunk: int, num_total_chunks: int) -> int:
        progress = num_processed_chunk / num_total_chunks * 100
        msg = f"{cfg.tr('Begin separating the speakers')}: {progress:.3f}%"
        return 0

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
        cfg.logger.debug(f'原始说话人排序后：{speaker_list=}')
        cfg.logger.debug(f'映射为新说话人标识：{spk_neworder_dict=}')

        for i, it in enumerate(output):
            output[i][1] = spk_neworder_dict.get(it[1], 'spk0')

        return output

    try:
        _st=time.time()
        cfg.logger.info(f'开始说话人分离,使用内置模型 {language=},{num_speakers=}')
        # 根据选择使用内置或 pyannote 方式
        diarizations = _get_diariz()
        if not diarizations:
            return False,'Unknow error'
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

        cfg.logger.debug(f'说话人分离成功结束,识别出个 {len(set(output))} 说话人,耗时：{int(time.time()-_st)}s')
        return output,None
    except Exception as e:
        msg=traceback.format_exc()
        cfg.logger.exception(f'分离说话人失败:{e}', exc_info=True)
        return False,msg
    finally:
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
        except Exception:
            pass
