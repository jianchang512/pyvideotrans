import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
import multiprocessing
import shutil
import time
from pathlib import Path



# 该文件运行在独立进程


def run(raws, err, detect, *, model_name, is_cuda, detect_language, audio_file,
        q: multiprocessing.Queue,proxy=None,TEMP_DIR=None,settings=None,defaulelang='zh',split_type=0,whisper_type=0):
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    os.environ["OMP_NUM_THREADS"] = "1"
    import torch
    from videotrans.configure import config
    from videotrans.process._iscache import _MODELS,is_model_cached,check_huggingface_connect
    from videotrans.util.tools import cleartext
    os.chdir(config.ROOT_DIR)
    down_root = config.ROOT_DIR + "/models"
    model=None
    batched_model=None
    prompt = settings.get(f'initial_prompt_{detect_language}') if detect_language != 'auto' else None

    def write_log(jsondata):
        try:
            q.put_nowait(jsondata)
        except Exception:
            pass
    
    def _get_modeldir_download(model_name):   
        write_log({"text": "Checking if the model exists", "type": "logs"})
        local_dir=f'{down_root}/models--'
        if model_name in _MODELS:
            local_dir+=_MODELS[model_name].replace('/','--')
            repo_id=_MODELS[model_name]
        else:
            repo_id=model_name
            local_dir+=model_name.replace('/','--')
        # 已存在
        if Path(local_dir).exists() and Path(local_dir+"/model.bin").is_file():
            write_log({"text": "The model already exists.", "type": "logs"})
            return local_dir
        Path(local_dir).mkdir(exist_ok=True, parents=True)
        # 不存在，判断缓存中是否存在
        # 用于兼容处理旧版本模型目录
        rs=is_model_cached(model_name, f"{down_root}")
        if isinstance(rs,str) and Path(rs).exists():
            #移动
            for item in Path(rs).iterdir():
                if item.is_dir():
                    continue
                try:                
                    shutil.move(str(item), local_dir)
                    print(f"Moved: {item.name}")
                except shutil.Error as e:
                    print(f"{e}")
            try:
                shutil.rmtree(f'{local_dir}/blobs')
                shutil.rmtree(f'{local_dir}/refs')
                shutil.rmtree(f'{local_dir}/snapshots')
            except:
                pass
            write_log({"text": "The model already exists.", "type": "logs"})
            return local_dir
        # 不存在，需要下载
        write_log({"text": "Downloading the model...", "type": "logs"})
        from huggingface_hub import snapshot_download
        check_huggingface_connect(config.ROOT_DIR,proxy)
        try:
            snapshot_download(
                repo_id=repo_id,
                local_dir=local_dir,
                local_dir_use_symlinks=False,
                ignore_patterns=["*.msgpack", "*.h5", ".git*"]
            )
            write_log({"text": "The model downloaded ", "type": "logs"})
        except Exception as e:
            msg=f'下载模型失败，你可以打开以下网址，将 .bin/.txt/.json 文件下载到\n {local_dir} 文件夹内\n' if defaulelang=='zh' else f'The model download failed. You can try opening the following URL and downloading the .bin/.txt/.json files to the {local_dir} folder.'
            raise RuntimeError(f'{msg}\n[https://huggingface.co/{repo_id}/tree/main]\n\n')
        else:
            junk_paths = [
                ".cache",
                "blobs",
                "refs",
                "snapshots",
                ".no_exist"
            ]
            
            for junk in junk_paths:
                full_path = Path(local_dir) / junk
                if full_path.exists():
                    try:
                        if full_path.is_dir():
                            shutil.rmtree(full_path)
                        else:
                            os.remove(full_path)
                        print(f"clear cache: {junk}")
                    except Exception as e:
                        print(f"{junk} {e}")
            return local_dir

    
    
    if whisper_type==1:
        import whisper
        if not Path(f'{down_root}/{model_name}.pt').exists():
            msg = f"模型 {model_name} 不存在，将自动下载 " if defaulelang == 'zh' else f'Model {model_name} does not exist and will be automatically downloaded'
            write_log({"text": msg, "type": "logs"})
        try:
            model = whisper.load_model(
                model_name,
                device="cuda" if is_cuda else "cpu",
                download_root=down_root
            )
            result = model.transcribe(
                    audio_file,
                    language=detect_language.split('-')[0] if detect_language != 'auto' else None,
                    word_timestamps=True,
                    initial_prompt=prompt if prompt else None,
                    condition_on_previous_text=config.settings.get('condition_on_previous_text',False)
                )
            nums = 0

            for segment in result['segments']:
                nums += 1
                if not Path(TEMP_DIR + f'/{os.getpid()}.lock').exists():
                    return
                new_seg = []
                for idx, word in enumerate(segment['words']):
                    new_seg.append({"start": word['start'], "end": word['end'], "word": word['word']})
                text = cleartext(segment['text'], remove_start_end=False)
                raws.append({"words": new_seg, "text": text})

                write_log({"text": f'{text}\n', "type": "subtitle"})
                write_log({"text": f' Subtitles {len(raws) + 1} ', "type": "logs"})
        except Exception as e:
            import traceback
            err['msg'] = traceback.format_exc()
    else:
        if model_name not in _MODELS:
            split_type=0
             
        try:
            local_dir=_get_modeldir_download(model_name)
        except Exception as e:# 可能下载失败
            err['msg'] = str(e)
            return


        from faster_whisper import WhisperModel,BatchedInferencePipeline
        
        try:
            if model_name.startswith('distil-'):
                com_type = "default"
            else:
                com_type = settings.get('cuda_com_type','default')

            try:
                model = WhisperModel(
                    local_dir,
                    device="cuda" if is_cuda else "cpu",
                    compute_type=com_type
                )
            except Exception as e:
                import traceback
                error = "".join(traceback.format_exception(e))
                if 'json.exception.parse_error' in error or 'EOF while parsing a value' in error:
                    msg = (
                        f'模型下载不完整，请删除目录 {local_dir}，重新下载' if defaulelang == "zh" else f"The model download may be incomplete, please delete the directory {local_dir} and download it again")
                elif "CUBLAS_STATUS_NOT_SUPPORTED" in error:
                    msg = f"数据类型不兼容：请打开菜单--工具--高级选项--faster/openai语音识别调整--CUDA数据类型--选择 float16，保存后重试:{error}" if defaulelang == 'zh' else f'Incompatible data type: Please open the menu - Tools - Advanced options - Faster/OpenAI speech recognition adjustment - CUDA data type - select float16, save and try again:{error}'
                elif "cudaErrorNoKernelImageForDevice" in error:
                    msg = f"pytorch和cuda版本不兼容，请更新显卡驱动后，安装或重装CUDA12.x及cuDNN9.x:{error}" if defaulelang == 'zh' else f'Pytorch and cuda versions are incompatible. Please update the graphics card driver and install or reinstall CUDA12.x and cuDNN9.x'
                else:
                    msg = error
                err['msg'] = msg
                return

            write_log({"text": model_name + " Loaded", "type": "logs"})
            
            # 批量或均等分割
            if split_type==1 or settings.get('faster_batch'):
                chunk_length=int(float(settings.get('max_speech_duration_s',6)))
                chunk_length=max(chunk_length,1)
                batched_model = BatchedInferencePipeline(model=model)
                segments, info=batched_model.transcribe(audio_file,
                    batch_size=16,
                    beam_size=int(settings.get('beam_size',5)),
                    best_of=int(settings.get('best_of',5)),
                    condition_on_previous_text=bool(settings.get('condition_on_previous_text',False)),
                    vad_filter=bool(settings.get('vad',False)),
                    vad_parameters=dict(
                        threshold=float(settings.get('threshold',0.45)),
                        min_speech_duration_ms=int(settings.get('min_speech_duration_ms',0)),
                        min_silence_duration_ms=int(settings.get('min_silence_duration_ms',140)),
                        speech_pad_ms=int(settings.get('speech_pad_ms',0))
                    ),
                    chunk_length=chunk_length,
                    word_timestamps=True,
                    language=detect_language.split('-')[0] if detect_language and detect_language != 'auto' else None,
                    initial_prompt=prompt if prompt else None
                )
            else:
                segments, info = model.transcribe(
                    audio_file,
                    beam_size=int(settings.get('beam_size',5)),
                    best_of=int(settings.get('best_of',5)),
                    condition_on_previous_text=bool(settings.get('condition_on_previous_text',False)),
                    vad_filter=bool(settings.get('vad',False)),
                    vad_parameters=dict(
                        threshold=float(settings.get('threshold',0.45)),
                        min_speech_duration_ms=int(settings.get('min_speech_duration_ms',0)),
                        max_speech_duration_s=float(settings.get('max_speech_duration_s',5)),
                        min_silence_duration_ms=int(settings.get('min_silence_duration_ms',140)),
                        speech_pad_ms=int(settings.get('speech_pad_ms',0))
                    ),
                    word_timestamps=True,
                    language=detect_language.split('-')[0] if detect_language and detect_language != 'auto' else None,
                    initial_prompt=prompt if prompt else None
                )
            if detect_language == 'auto' and info.language != detect['langcode']:
                detect['langcode'] = 'zh-cn' if info.language[:2] == 'zh' else info.language
            nums = 0

            for segment in segments:
                nums += 1
                if not Path(TEMP_DIR + f'/{os.getpid()}.lock').exists():
                    return
                new_seg = []
                for idx, word in enumerate(segment.words):
                    new_seg.append({"start": word.start, "end": word.end, "word": word.word})
                text = cleartext(segment.text, remove_start_end=False)
                raws.append({"words": new_seg, "text": text})

                write_log({"text": f'{text}\n', "type": "subtitle"})
                write_log({"text": f' Subtitles {len(raws) + 1} ', "type": "logs"})
        except BaseException as e:
            import traceback
            err['msg'] = traceback.format_exc()

    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        import gc
        gc.collect()
        del model
        del batched_model
        shutil.rmtree(config.TEMP_DIR,ignore_errors=True)
    except Exception:
        pass
    time.sleep(1)
