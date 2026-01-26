# 语音识别，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
from videotrans.util import gpus
def openai_whisper(
        *,
        prompt=None,
        detect_language=None,
        model_name=None,
        ROOT_DIR=None,
        logs_file=None,
        defaulelang="en",
        is_cuda=False,
        no_speech_threshold=0.5,
        condition_on_previous_text=False,
        speech_timestamps=None,
        audio_file=None,
        TEMP_ROOT=None,
        jianfan=False,
        batch_size=1,
        audio_duration=0,
        temperature=None,
        compression_ratio_threshold=2.2,
        device_index=0 # gpu索引
):
    import re, os, traceback, json, time
    import shutil
    from pathlib import Path
    from videotrans.configure import config
    import torch
    torch.set_num_threads(1)
    import whisper
    from videotrans.util import tools

    import zhconv


    if not Path(f'{ROOT_DIR}/models/{model_name}.pt').exists():
        msg = f"模型 {model_name} 不存在，将自动下载 " if defaulelang == 'zh' else f'Model {model_name} does not exist and will be automatically downloaded'
    else:
        msg = f"load {model_name}"
    _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
    model = None
    raws = []
    try:
        if speech_timestamps and isinstance(speech_timestamps, str):
            speech_timestamps = json.loads(Path(speech_timestamps).read_text(encoding='utf-8'))
        if not temperature:
            temperature = (
                0.0,
                0.2,
                0.4,
                0.6,
                0.8,
                1.0,
            )
        elif str(temperature).startswith('['):
            temperature = tuple(str(temperature)[1:-1].split(','))

        model = whisper.load_model(
            model_name,
            device=f"cuda:{device_index}" if is_cuda else gpus.mps_or_cpu(),
            download_root=ROOT_DIR + "/models"
        )
        msg = f"Loaded {model_name}"
        _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))

        last_end_time = audio_duration / 1000.0 if audio_duration > 0 else speech_timestamps[-1][1] / 1000.0
        speech_timestamps_flat = []
        if speech_timestamps and batch_size > 1:
            for it in speech_timestamps:
                speech_timestamps_flat.extend([it[0] / 1000.0, it[1] / 1000.0])
        else:
            speech_timestamps_flat = "0"

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
            tmp = {
                'text': text,
                'start_time': s,
                'end_time': e
            }
            tmp['startraw'] = tools.ms_to_time_string(ms=tmp['start_time'])
            tmp['endraw'] = tools.ms_to_time_string(ms=tmp['end_time'])
            tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
            raws.append(tmp)
            _write_log(logs_file, json.dumps({"type": "subtitle", "text": f'[{i}] {text}\n'}))
    except Exception:
        msg = traceback.format_exc()
        config.logger.exception(f'语音识别失败:{model_name=},{msg}', exc_info=True)
        return False, msg
    else:
        return raws, None
    finally:
        try:
            if model:
                del model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
        except Exception:
            pass


def faster_whisper(
        *,
        prompt=None,
        detect_language=None,
        model_name=None,
        ROOT_DIR=None,
        logs_file=None,
        defaulelang="en",
        is_cuda=False,
        no_speech_threshold=0.5,
        condition_on_previous_text=False,
        speech_timestamps=None,
        audio_file=None,
        TEMP_ROOT=None,
        local_dir=None,
        compute_type="default",
        batch_size=8,
        beam_size=5,
        best_of=5,
        jianfan=False,
        audio_duration=0,
        temperature=None,
        hotwords=None,
        repetition_penalty=1.0,
        compression_ratio_threshold=2.2,
        device_index=0 # gpu索引
):
    import re, os, traceback, json, time
    import shutil
    from pathlib import Path
    from videotrans.configure import config

    import torch
    torch.set_num_threads(1)
    from faster_whisper import WhisperModel, BatchedInferencePipeline
    from videotrans.util import tools
    import zhconv

    model = None
    batched_model = None
    raws = []

    try:
        if speech_timestamps and isinstance(speech_timestamps, str):
            speech_timestamps = json.loads(Path(speech_timestamps).read_text(encoding='utf-8'))
        last_end_time = audio_duration / 1000.0 if audio_duration > 0 else speech_timestamps[-1][1] / 1000.0
        try:
            # 1. 加载基础模型
            model = WhisperModel(
                local_dir,
                device="cuda" if is_cuda else 'cpu',
                device_index=device_index if is_cuda 0,
                compute_type=compute_type
            )
        except Exception as e:
            error = traceback.format_exc()
            if 'json.exception.parse_error' in error or 'EOF while parsing a value' in error:
                msg = (
                    f'模型下载不完整，请删除目录 {local_dir}，重新下载' if defaulelang == "zh" else f"The model download may be incomplete, please delete the directory {local_dir} and download it again")
            elif "CUBLAS_STATUS_NOT_SUPPORTED" in error:
                msg = f"数据类型不兼容...:{error}"
            elif "cudaErrorNoKernelImageForDevice" in error:
                msg = f"pytorch和cuda版本不兼容...:{error}"
            else:
                msg = error
            return False, msg

        if not temperature:
            temperature = [
                0.0,
                0.2,
                0.4,
                0.6,
                0.8,
                1.0,
            ]
        elif str(temperature).startswith('['):
            temperature = str(temperature)[1:-1].split(',')
        if batch_size > 1:
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
                batch_size=batch_size,  #
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
        else:
            segments, info = model.transcribe(
                audio_file,
                beam_size=beam_size,
                best_of=best_of,
                condition_on_previous_text=condition_on_previous_text,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
                no_speech_threshold=no_speech_threshold,
                clip_timestamps="0",  # clip_timestamps,
                word_timestamps=False,
                without_timestamps=False,
                temperature=temperature,
                hotwords=hotwords,
                repetition_penalty=repetition_penalty,
                compression_ratio_threshold=compression_ratio_threshold,
                language=detect_language.split('-')[0] if detect_language and detect_language != 'auto' else None,
                initial_prompt=prompt if prompt else None
            )
        i = 0
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
            tmp = {
                'text': text,
                'start_time': s,
                'end_time': e
            }
            tmp['startraw'] = tools.ms_to_time_string(ms=tmp['start_time'])
            tmp['endraw'] = tools.ms_to_time_string(ms=tmp['end_time'])
            tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
            raws.append(tmp)
            _write_log(logs_file, json.dumps({"type": "subtitle", "text": f'[{i}] {text}\n'}))
    except Exception:
        msg = traceback.format_exc()
        config.logger.exception(f'语音识别失败:{model_name=},{msg}', exc_info=True)
        return False, msg
    else:
        return raws, None
    finally:
        try:
            if model:
                del model
            if batched_model:
                del batched_model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
        except Exception:
            pass


def pipe_asr(
        prompt=None,
        cut_audio_list=None,
        detect_language=None,
        model_name=None,
        ROOT_DIR=None,
        logs_file=None,
        defaulelang="en",
        is_cuda=False,
        audio_file=None,
        TEMP_ROOT=None,
        local_dir=None,
        batch_size=8,
        jianfan=False,
        device_index=0 # gpu索引
):
    import re, os, traceback, json, time
    import shutil
    from pathlib import Path
    from videotrans.configure import config

    import torch
    torch.set_num_threads(1)
    from transformers import pipeline
    import zhconv

    # 定义输入生成器，直接把路径或音频数据喂给 pipeline
    def inputs_generator():
        for item in raws:
            yield item['file']

    # 2. 初始化 Pipeline
    # 使用 device_map="auto" 自动分配，或指定 device
    device_arg = device_index if is_cuda else gpus.mps_or_cpu()
    # 注意：使用 device_map="auto" 时通常不需要传 device 参数，二者选一
    # 如果是单卡环境，直接传 device=0 效率通常比 device_map="auto" 稍微高一点点
    p = None
    msg = f"Loading pipeline from {local_dir}"
    _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
    try:
        if cut_audio_list and isinstance(cut_audio_list, str):
            cut_audio_list = json.loads(Path(cut_audio_list).read_text(encoding='utf-8'))

        raws = cut_audio_list

        p = pipeline(
            task="automatic-speech-recognition",
            model=local_dir,
            batch_size=batch_size,
            device=device_arg,
            dtype=torch.float16 if is_cuda else torch.float32,
        )

        msg = f'Pipeline loaded on device={(p.model.device)}'
        _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
        # 3. 动态构建 generate_kwargs
        generate_kwargs = {}

        # 获取模型类型，例如 'whisper', 'wav2vec2', 'huBERT', 'parakeet' 等
        model_type = p.model.config.model_type
        is_whisper = "whisper" in model_type.lower()

        if is_whisper:
            # === Whisper 专用参数 ===
            lang = detect_language.split('-')[0] if detect_language != 'auto' else None

            generate_kwargs["task"] = "transcribe"
            if lang:
                generate_kwargs["language"] = lang

            # 处理 Prompt
            if prompt:
                # 获取 tokenizer 并转换 prompt 为 token IDs
                # 兼容旧版本 transformers
                if hasattr(p.tokenizer, "get_prompt_ids"):
                    prompt_ids = p.tokenizer.get_prompt_ids(prompt, return_tensors="pt")
                else:
                    # 通用回退方案
                    prompt_ids = p.tokenizer(prompt, add_special_tokens=False, return_tensors="pt").input_ids

                # 确保 tensor 在正确的设备上
                if is_cuda:
                    prompt_ids = prompt_ids.to(p.model.device)

                # 注意：这里需要取 [0] 或者是 tensor 本身，取决于 pipeline 版本，
                # 通常传入 tensor 即可，但某些版本需要 list。
                # 安全起见，转为 tensor 传入通常是支持的，或者转为 list: prompt_ids.tolist()[0]
                generate_kwargs["prompt_ids"] = prompt_ids

        else:
            # === 其他架构 (如 Parakeet, Wav2Vec2) ===
            # 这些模型通常不需要 language 参数（或者是预定义好的），也不支持 prompt_ids
            pass

        # 4. 执行批量推理
        # 这里的 p(...) 返回的是一个迭代器，它会在后台进行 batch 处理
        results_iterator = p(
            inputs_generator(),
            generate_kwargs=generate_kwargs
        )

        total = len(raws)

        # 5. 收集结果
        # 注意：这里我们同时遍历 raws 和 results_iterator
        # 因为 inputs_generator 是按顺序 yield 的，results_iterator 也会按顺序输出
        for i, (it, res) in enumerate(zip(raws, results_iterator)):
            _write_log(logs_file, json.dumps({"type": "logs", "text": f"subtitles {i + 1}/{total}..."}))

            text = res.get('text', '')

            # 清理文件路径引用（如果需要）
            if 'file' in it:
                del it['file']

            if text:
                # 清理特殊标记
                cleaned_text = re.sub(r'<unk>|</unk>', '', text).strip()
                if jianfan:
                    cleaned_text = zhconv.convert(cleaned_text, 'zh-hans')
                raws[i]['text'] = cleaned_text

                # 如果 pipeline 返回了时间戳（取决于 chunk_length_s 和 return_timestamps 参数）
                _write_log(logs_file, json.dumps({"type": "subtitles", "text": f'[{i}] {cleaned_text}\n'}))
        return raws, None
    except Exception:
        msg = traceback.format_exc()
        config.logger.exception(f'语音识别失败:{model_name=},{msg}', exc_info=True)
        return False, msg
    finally:
        try:
            if p:
                del p
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
        except Exception:
            pass


def paraformer(
        cut_audio_list=None,
        detect_language=None,
        model_name=None,
        ROOT_DIR=None,
        logs_file=None,
        defaulelang="en",
        is_cuda=False,
        audio_file=None,
        TEMP_ROOT=None,
        max_speakers=-1,
        cache_folder=None,
        device_index=0 # gpu索引
):
    import re, os, traceback, json, time
    import shutil
    from pathlib import Path
    from videotrans.configure import config

    import torch
    torch.set_num_threads(1)
    from videotrans.util import tools
    # from funasr import AutoModel
    from modelscope.pipelines import pipeline
    from modelscope.utils.constant import Tasks

    raw_subtitles = []
    model_dir = f'{ROOT_DIR}/models/models/iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch'
    if not Path(model_dir).exists():
        msg = f'Download {model_name} from modelscope.cn'
    else:
        msg = f'Load {model_name} model'
    _write_log(logs_file, json.dumps({"type": "logs", "text": f'{msg}'}))
    model = None
    device = f'cuda:{device_index}' if is_cuda else gpus.mps_or_cpu()
    try:
        inference_pipeline = pipeline(
            task=Tasks.auto_speech_recognition,
            model='iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch',
            model_revision="v2.0.4",
            vad_model='iic/speech_fsmn_vad_zh-cn-16k-common-pytorch',
            # vad_model_revision="v2.0.4",
            punc_model='iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch',
            # punc_model_revision="v2.0.3",
            spk_model="iic/speech_campplus_sv_zh-cn_16k-common",
            # spk_model_revision="v2.0.2",
            disable_update=True,
            disable_progress_bar=True,
            disable_log=True,
            device=device
            # trust_remote_code=True,
        )

        msg = "Model loading is complete, enter recognition"
        _write_log(logs_file, json.dumps({"type": "logs", "text": f'{msg}'}))
        num = 0
        res = inference_pipeline(audio_file)
        speaker_list = []
        i = 0
        for it in res[0]['sentence_info']:
            if not it.get('text', '').strip():
                continue
            i += 1
            if max_speakers > -1:
                speaker_list.append(f"spk{it.get('spk', 0)}")
            tmp = {
                "line": len(raw_subtitles) + 1,
                "text": it['text'].strip(),
                "start_time": it['start'],
                "end_time": it['end'],
                "startraw": f'{tools.ms_to_time_string(ms=it["start"])}',
                "endraw": f'{tools.ms_to_time_string(ms=it["end"])}'
            }
            _write_log(logs_file, json.dumps({"type": "subtitles", "text": f'[{i}] {it["text"]}\n'}))
            tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
            raw_subtitles.append(tmp)
        if speaker_list:
            Path(f'{cache_folder}/speaker.json').write_text(json.dumps(speaker_list), encoding='utf-8')
    except Exception:
        msg = traceback.format_exc()
        config.logger.exception(f'语音识别失败:{model_name=},{msg}', exc_info=True)
        return False, msg
    finally:
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            if model:
                del model
            import gc
            gc.collect()
        except Exception:
            pass

    return raw_subtitles, None


def _write_log(file, msg):
    from pathlib import Path
    from videotrans.configure import config
    try:
        Path(file).write_text(msg, encoding='utf-8')
    except Exception as e:
        config.logger.exception(f'写入新进程日志时出错', exc_info=True)


def _remove_unwanted_characters(text: str) -> str:
    import re
    # 保留中文、日文、韩文、英文、数字和常见符号，去除其他字符
    allowed_characters = re.compile(r'<\|\w+\|>')
    return re.sub(allowed_characters, '', text)


def funasr_mlt(
        cut_audio_list=None,
        detect_language=None,
        model_name=None,
        ROOT_DIR=None,
        logs_file=None,
        defaulelang="en",
        is_cuda=False,
        audio_file=None,
        TEMP_ROOT=None,
        jianfan=False,
        max_speakers=-1,
        cache_folder=None,
        device_index=0 # gpu索引
):
    import re, os, traceback, json, time
    import shutil
    from pathlib import Path
    from videotrans.configure import config

    import torch
    torch.set_num_threads(1)
    from funasr import AutoModel
    from modelscope.pipelines import pipeline
    from modelscope.utils.constant import Tasks

    if not Path(f'{ROOT_DIR}/models/models/{model_name}').exists():
        msg = f'Download {model_name} from modelscope.cn'
    else:
        msg = f'Load {model_name}'
    _write_log(logs_file, json.dumps({"type": "logs", "text": f'{msg}'}))

    model = None
    device = f"cuda:{device_index}" if is_cuda else gpus.mps_or_cpu()
    try:
        if cut_audio_list and isinstance(cut_audio_list, str):
            cut_audio_list = json.loads(Path(cut_audio_list).read_text(encoding='utf-8'))

        srts = cut_audio_list
        if model_name == 'iic/SenseVoiceSmall':
            inference_pipeline = pipeline(
                task=Tasks.auto_speech_recognition,
                model='iic/SenseVoiceSmall',
                # model_revision="master",
                disable_update=True,
                disable_progress_bar=True,
                disable_log=True,
                device=device
            )

            res = inference_pipeline([it['file'] for it in cut_audio_list], batch_size=4, disable_pbar=True)
        else:
            model = AutoModel(
                model=model_name,
                punc_model="iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
                device=device,
                local_dir=ROOT_DIR + "/models",
                disable_update=True,
                disable_progress_bar=True,
                disable_log=True,
                trust_remote_code=True,
                remote_code=f"{ROOT_DIR}/videotrans/codes/model.py",
                hub='ms',
            )

            # vad
            msg = "Recognition may take a while, please be patient"
            _write_log(logs_file, json.dumps({"type": "logs", "text": f'{msg}'}))
            num = 0

            def _show_process(ex, dx):
                nonlocal num
                num += 1
                _write_log(logs_file, json.dumps({"type": "logs", "text": f'STT {num}'}))

            res = model.generate(
                input=[it['file'] for it in srts],
                language=detect_language[:2],  # "zh", "en", "yue", "ja", "ko", "nospeech"
                use_itn=True,
                batch_size=1,
                progress_callback=_show_process,
                disable_pbar=True
            )
        for i, it in enumerate(res):
            text = _remove_unwanted_characters(it['text'])
            srts[i]['text'] = text
            _write_log(logs_file, json.dumps({"type": "subtitles", "text": f'[{i}] {text}\n'}))
        return srts, None
    except Exception:
        msg = traceback.format_exc()
        config.logger.exception(f'语音识别失败:{model_name=},{msg}', exc_info=True)
        return False, msg
    finally:
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            if model:
                del model
            import gc
            gc.collect()
        except Exception:
            pass
