import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
import multiprocessing
import shutil
import time
from pathlib import Path

# 中国大陆除非已使用VPN，否则无法连接 huggingface.co, 使用镜像站 hf-mirror.com 替换，但不太稳定，下载大文件容易失败
# 针对默认模型 large-v3-turbo，在无法连接 huggingface.co 时，优先从 modelscope.cn 下载


def run(raws, err, detect, *, model_name, is_cuda, detect_language, audio_file,
        q: multiprocessing.Queue,proxy=None,TEMP_DIR=None,settings=None,defaulelang='zh',split_type=0,whisper_type=0,speech_timestamps=None):
    from videotrans.configure import config
    from videotrans.process._iscache import _MODELS,is_model_cached
    import torch,requests
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
    
    # 在下载默认模型 large-v3-turbo时，针对国内无法连接huggingface.co，且镜像站不稳定的情况，使用 modelscope.cn替换
    def _faster_turbo_from_modelscope(local_dir):
        print('阿里镜像下载')
        urls=[
            'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/config.json',
            'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/preprocessor_config.json',
            'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/tokenizer.json',
            'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/vocabulary.json',
            'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/model.bin',
        ]
        write_log({"text": f"downloading large-v3-turbo from modelscope.cn", "type": "logs"})
        for index,url in enumerate(urls):
            filename=os.path.basename(url)
            write_log({"text": f"start downloading {index+1}/5 from modelscope.cn", "type": "logs"})
            with requests.get(url, stream=True, timeout=60) as response:
                response.raise_for_status()
                
                total_length = response.headers.get('content-length')
                dest_file_obj = open(f'{local_dir}/{filename}', 'wb')
                try:
                    if total_length is None:
                        dest_file_obj.write(response.content)
                    else:
                        total_length = int(total_length)
                        downloaded = 0
                        last_send=time.time()
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                dest_file_obj.write(chunk)
                                downloaded += len(chunk)
                                file_percent = min((downloaded / total_length)*100,100)
                                if time.time()-last_send>3:
                                    last_send=time.time()
                                    write_log({"text": f"downloading {index+1}/5 {file_percent:.2f}%", "type": "logs"})
                finally:
                    dest_file_obj.close()                   
            write_log({"text": f"end downloading {index+1}/5 from modelscope.cn", "type": "logs"})
            
        
        return local_dir
        
    # 下载模型，首先测试 huggingface.co 连通性，不可用则回退镜像 hf-mirror.com
    def _get_modeldir_download(model_name):   
        print(f'下载 {model_name=},proxy={os.environ.get("HTTPS_PROXY")}')
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
        
        try:
            requests.head('https://huggingface.co',timeout=5)
        except Exception:
            print(f'无法连接 huggingface.co, 使用镜像替换: hf-mirror.com, {model_name=}')
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            os.environ["HF_HUB_DISABLE_XET"] = "1"
            if model_name in ['large-v3-turbo','turbo']:
                try:
                    # 针对 large-v3-turbo 模型使用 modelscope.cn 下载
                    return _faster_turbo_from_modelscope(local_dir)
                except Exception as e:
                    print(e)
                    pass#失败继续使用镜像尝试
        else:
            print('可以使用 huggingface.co')
            os.environ['HF_ENDPOINT'] = 'https://huggingface.co'
            os.environ["HF_HUB_DISABLE_XET"] = "0"
        
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
        write_log({"text": f"Downloading the model from {os.environ['HF_ENDPOINT']} ...", "type": "logs"})
        from huggingface_hub import snapshot_download
        try:
            snapshot_download(
                repo_id=repo_id,
                local_dir=local_dir,
                local_dir_use_symlinks=False,
                ignore_patterns=["*.msgpack", "*.h5", ".git*","*.md"]
            )
            write_log({"text": "The model downloaded ", "type": "logs"})
        except Exception as e:
            msg=f'下载模型失败，你可以打开以下网址，将 .bin/.txt/.json 文件下载到\n {local_dir} 文件夹内\n' if defaulelang=='zh' else f'The model download failed. You can try opening the following URL and downloading the .bin/.txt/.json files to the {local_dir} folder.'
            raise RuntimeError(f'{msg}\n[https://huggingface.co/{repo_id}/tree/main]\n{e}')
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

    
    last_end_time=speech_timestamps[-1][1]/1000.0
    print(f's={time.time()}')
    print(float(settings.get('no_speech_threshold',0.5)))
    try:
        if whisper_type==1:
            import whisper
            if not Path(f'{down_root}/{model_name}.pt').exists():
                msg = f"模型 {model_name} 不存在，将自动下载 " if defaulelang == 'zh' else f'Model {model_name} does not exist and will be automatically downloaded'
                write_log({"text": msg, "type": "logs"})
            write_log({"text": f"load {model_name}", "type": "logs"})
            model = whisper.load_model(
                model_name,
                device="cuda" if is_cuda else "cpu",
                download_root=down_root
            )
            write_log({"text": f"Loaded {model_name}", "type": "logs"})
            speech_timestamps_flat=[]
            
            if split_type==1 or settings.get('faster_batch'):
                print(f'openai-whisper 批量')
                from pydub import AudioSegment
                audio=AudioSegment.from_file(audio_file)
                time_int=int(time.time()*1000)
                for i,it in enumerate(speech_timestamps):
                    filename=f'{config.ROOT_DIR}/tmp/{i}-{it[0]}-{it[1]}-{time_int}.wav'
                    audio[it[0]:it[1]].export(filename,format="wav")
                    result = model.transcribe(
                        filename,
                        language=detect_language.split('-')[0] if detect_language != 'auto' else None,
                        initial_prompt=prompt if prompt else None,
                        no_speech_threshold=float(settings.get('no_speech_threshold',0.5)),
                        condition_on_previous_text=config.settings.get('condition_on_previous_text',False)
                    )
                    text=''
                    for segment in result['segments']:
                        text+=segment['text']
                    if text:
                        raws.append({"text": text,"start":it[0]/1000.0,'end':it[1]/1000.0})
                        write_log({"text": f'{text}\n', "type": "subtitle"})
                        write_log({"text": f' Subtitles {len(raws) + 1} ', "type": "logs"})
                    try:
                        Path(filename).unlink(missing_ok=True)
                    except:
                        pass
                    
            else:
                print(f'openai-whisper 整体识别')
                for it in speech_timestamps:
                    speech_timestamps_flat.extend([it[0]/1000.0,it[1]/1000.0])
                
                result = model.transcribe(
                        audio_file,
                        no_speech_threshold=float(settings.get('no_speech_threshold',0.5)),
                        language=detect_language.split('-')[0] if detect_language != 'auto' else None,
                        clip_timestamps=speech_timestamps_flat,
                        initial_prompt=prompt if prompt else None,
                        condition_on_previous_text=config.settings.get('condition_on_previous_text',False)
                    )
                for segment in result['segments']:
                    #print(f'{time.time()=}')
                    if not Path(TEMP_DIR + f'/{os.getpid()}.lock').exists():
                        return
                    # 时间戳大于总时长，出错跳过
                    if segment['end']>last_end_time:
                        continue
                    text = segment['text']
                    if not text.strip():
                        continue
                    raws.append({"text": text,"start":segment['start'],'end':segment['end']})
                    write_log({"text": f'{text}\n', "type": "subtitle"})
                    write_log({"text": f' Subtitles {len(raws) + 1} ', "type": "logs"})
        else:
            if model_name not in _MODELS:
                split_type=0
                 
            try:
                local_dir=_get_modeldir_download(model_name)
            except Exception as e:# 可能下载失败
                err['msg'] = str(e)
                return

            write_log({"text": f"load {model_name}", "type": "logs"})
            from faster_whisper import WhisperModel,BatchedInferencePipeline
            
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
                print(f'faster-whisper 批量')
                from pydub import AudioSegment
                audio=AudioSegment.from_file(audio_file)
                time_int=int(time.time()*1000)
                for i,it in enumerate(speech_timestamps):
                    filename=f'{config.ROOT_DIR}/tmp/{i}-{it[0]}-{it[1]}-{time_int}.wav'
                    audio[it[0]:it[1]].export(filename,format="wav")
                    segments, info = model.transcribe(
                        filename,
                        beam_size=int(settings.get('beam_size',5)),
                        best_of=int(settings.get('best_of',5)),
                        no_speech_threshold=float(settings.get('no_speech_threshold',0.5)),
                        condition_on_previous_text=bool(settings.get('condition_on_previous_text',False)),
                        word_timestamps=False,
                        #clip_timestamps=speech_timestamps_flat,
                        language=detect_language.split('-')[0] if detect_language and detect_language != 'auto' else None,
                        initial_prompt=prompt if prompt else None
                    )
                    if not Path(TEMP_DIR + f'/{os.getpid()}.lock').exists():
                        return
                    text=''
                    for segment in segments:
                        text+=segment.text
            
                    raws.append({"text": text,"start":it[0]/1000.0,'end':it[1]/1000.0})
                    write_log({"text": f'{text}\n', "type": "subtitle"})
                    write_log({"text": f' Subtitles {len(raws) + 1} ', "type": "logs"})
                    try:
                        Path(filename).unlink(missing_ok=True)
                    except:
                        pass
            else:
                print(f'faster-whisper 整体识别')
                speech_timestamps_flat=[]
                for it in speech_timestamps:
                    speech_timestamps_flat.extend([it[0]/1000.0,it[1]/1000.0])
                segments, info = model.transcribe(
                    audio_file,
                    beam_size=int(settings.get('beam_size',5)),
                    best_of=int(settings.get('best_of',5)),
                    no_speech_threshold=float(settings.get('no_speech_threshold',0.5)),
                    condition_on_previous_text=bool(settings.get('condition_on_previous_text',False)),
                    word_timestamps=False,
                    clip_timestamps=speech_timestamps_flat,
                    language=detect_language.split('-')[0] if detect_language and detect_language != 'auto' else None,
                    initial_prompt=prompt if prompt else None
                )
                #if detect_language == 'auto' and info.language != detect['langcode']:
                    #detect['langcode'] = 'zh-cn' if info.language[:2] == 'zh' else info.language

                for segment in segments:
                    if not Path(TEMP_DIR + f'/{os.getpid()}.lock').exists():
                        return
                    if segment.end>last_end_time:
                        continue
                    text = segment.text
                    if not text.strip():
                        continue
                    s,e=segment.start,segment.end
                    raws.append({"text": text,"start":s,'end':e})
                    write_log({"text": f'{text}\n', "type": "subtitle"})
                    write_log({"text": f' Subtitles {len(raws) + 1} ', "type": "logs"})
        
        
    except BaseException as e:
        import traceback
        err['msg'] = traceback.format_exc()
    print(f'e={time.time()}')
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
