
import time,json,shutil
import os
from pathlib import Path
from dataclasses import dataclass
from videotrans.configure import config
from videotrans.configure.config import tr

from videotrans.recognition._base import BaseRecogn
from videotrans.task.simple_runnable_qt import run_in_threadpool

from faster_whisper.utils import _MODELS
import threading,requests
from videotrans.util import tools


"""
faster-whisper
内置的本地大模型不重试
"""


@dataclass
class FasterAll(BaseRecogn):
    def __post_init__(self):
        super().__post_init__()


    def _exec(self):
        if self._exit():
            return
        self.has_done = False
        self.error = ''
        self._signal(text="STT starting, hold on...")
        if self.recogn_type==1:#openai-whisper
            raws=self._openai()
        else:
            raws=self._faster()        
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
        except Exception:
            pass
        return self._get_srtlist(raws)

    
    def _openai(self):
        import whisper
        raws=[]
        prompt=config.settings.get(f'initial_prompt_{self.detect_language}') if self.detect_language != 'auto' else None
        if not Path(f'{config.ROOT_DIR}/models/{self.model_name}.pt').exists():
            msg = f"模型 {self.model_name} 不存在，将自动下载 " if config.defaulelang == 'zh' else f'Model {self.model_name} does not exist and will be automatically downloaded'
            self._signal(text=msg)
        else:
            self._signal(text=f"load {self.model_name}")
        model = whisper.load_model(
            self.model_name,
            device="cuda" if self.is_cuda else "cpu",
            download_root=config.ROOT_DIR + "/models"
        )
        self._signal(text=f"Loaded {self.model_name}")
        raws=[]
        print(f'openai-whisper 整体识别')
        speech_timestamps=self.get_speech_timestamp(self.audio_file)
        last_end_time=speech_timestamps[-1][1]/1000.0
        speech_timestamps_flat=[]
        for it in speech_timestamps:
            speech_timestamps_flat.extend([it[0]/1000.0,it[1]/1000.0])
        
        result = model.transcribe(
                self.audio_file,
                no_speech_threshold=float(config.settings.get('no_speech_threshold',0.5)),
                language=self.detect_language.split('-')[0] if self.detect_language != 'auto' else None,
                clip_timestamps=speech_timestamps_flat,
                initial_prompt=prompt if prompt else None,
                condition_on_previous_text=config.settings.get('condition_on_previous_text',False)
            )
        for segment in result['segments']:
            # 时间戳大于总时长，出错跳过
            if segment['end']>last_end_time:
                continue
            text = segment['text']
            if not text.strip():
                continue
            raws.append({"text": text,"start":segment['start'],'end':segment['end']})
            self._signal(text=f'{text}\n', type="subtitle")
            self._signal(text=f' Subtitles {len(raws) + 1} ')
        try:
            if model:
                del model
        except Exception:
            pass

        
        return raws


    def _faster(self):
        prompt=config.settings.get(f'initial_prompt_{self.detect_language}') if self.detect_language != 'auto' else None
        raws=[]
        
        local_dir=self._get_modeldir_download(self.model_name)

        self._signal(text=f"load {self.model_name}")
        
        from faster_whisper import WhisperModel,BatchedInferencePipeline
        
        if self.model_name.startswith('distil-'):
            com_type = "default"
        else:
            com_type = config.settings.get('cuda_com_type','default')

        try:
            model = WhisperModel(
                local_dir,
                device="cuda" if self.is_cuda else "cpu",
                compute_type=com_type
            )
        except Exception as e:
            import traceback
            error = "".join(traceback.format_exception(e))
            if 'json.exception.parse_error' in error or 'EOF while parsing a value' in error:
                msg = (
                    f'模型下载不完整，请删除目录 {local_dir}，重新下载' if config.defaulelang == "zh" else f"The model download may be incomplete, please delete the directory {local_dir} and download it again")
            elif "CUBLAS_STATUS_NOT_SUPPORTED" in error:
                msg = f"数据类型不兼容：请打开菜单--工具--高级选项--faster/openai语音识别调整--CUDA数据类型--选择 float16，保存后重试:{error}" if config.defaulelang == 'zh' else f'Incompatible data type: Please open the menu - Tools - Advanced options - Faster/OpenAI speech recognition adjustment - CUDA data type - select float16, save and try again:{error}'
            elif "cudaErrorNoKernelImageForDevice" in error:
                msg = f"pytorch和cuda版本不兼容，请更新显卡驱动后，安装或重装CUDA12.x及cuDNN9.x:{error}" if config.defaulelang == 'zh' else f'Pytorch and cuda versions are incompatible. Please update the graphics card driver and install or reinstall CUDA12.x and cuDNN9.x'
            else:
                msg = error
            raise RuntimeError(msg)

        self._signal(text=self.model_name + " Loaded")

        # 批量或均等分割
        speech_timestamps=self.get_speech_timestamp(self.audio_file)            
        print(f'faster-whisper 整体识别')
        last_end_time=speech_timestamps[-1][1]/1000.0
        speech_timestamps_flat=[]
        for it in speech_timestamps:
            speech_timestamps_flat.extend([it[0]/1000.0,it[1]/1000.0])
        segments, info = model.transcribe(
            self.audio_file,
            beam_size=int(config.settings.get('beam_size',5)),
            best_of=int(config.settings.get('best_of',5)),
            no_speech_threshold=float(config.settings.get('no_speech_threshold',0.5)),
            condition_on_previous_text=bool(config.settings.get('condition_on_previous_text',False)),
            word_timestamps=False,
            clip_timestamps=speech_timestamps_flat,
            language=self.detect_language.split('-')[0] if self.detect_language and self.detect_language != 'auto' else None,
            initial_prompt=prompt if prompt else None
        )


        for segment in segments:
            if segment.end>last_end_time:
                continue
            text = segment.text
            if not text.strip():
                continue
            s,e=segment.start,segment.end
            raws.append({"text": text,"start":s,'end':e})
            self._signal(text=f'{text}\n', type="subtitle")
            self._signal(text=f' Subtitles {len(raws) + 1} ')
        
        try:
            if model:
                del model
        except Exception:
            pass
        return raws
        
    def _get_srtlist(self, raws):
        
        if self.jianfan:
            import zhconv
        srt_raws = []
        raws=list(raws)
        raws_len=len(raws)
        for idx,it in enumerate(raws):
            if not it['text'].strip():
                continue
            if self.jianfan:
                self._signal(text=f"简繁转换中 [{idx+1}/{raws_len}]...")
            text=zhconv.convert(it['text'], 'zh-hans') if self.jianfan else it['text']
            if it.get('start_time'):
                s,e=it['start_time'],it['end_time']
            else:
                s,e=int(it['start']*1000),int(it['end']*1000)
            
            tmp = {
                'text': text,
                'start_time': s,
                'end_time': e
            }

            tmp['startraw'] = tools.ms_to_time_string(ms=tmp['start_time'])
            tmp['endraw'] = tools.ms_to_time_string(ms=tmp['end_time'])
            tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
            srt_raws.append(tmp)
        
        return srt_raws
        


    # 在下载默认模型 large-v3-turbo时，针对国内无法连接huggingface.co，且镜像站不稳定的情况，使用 modelscope.cn替换
    def _faster_turbo_from_modelscope(self,local_dir):
        print('阿里镜像下载')
        urls=[
            'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/config.json',
            'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/preprocessor_config.json',
            'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/tokenizer.json',
            'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/vocabulary.json',
            'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/model.bin',
        ]
        self._signal(text=f"downloading large-v3-turbo from modelscope.cn")
        for index,url in enumerate(urls):
            filename=os.path.basename(url)
            print(filename)
            self._signal(text=f"start downloading {index+1}/5 from modelscope.cn")
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
                                    self._signal(text=f"downloading {index+1}/5 {file_percent:.2f}%")
                finally:
                    dest_file_obj.close()                   
            self._signal(text=f"end downloading {index+1}/5 from modelscope.cn")
        return local_dir
        
        
    def _progress_callback(self, data):
        msg_type = data.get("type")
        percent = data.get("percent")
        filename = data.get("filename")
        
        if msg_type == "file":
           
            # 标签显示当前文件名
            self._signal(text=f"{filename} {percent:.2f}%")
            
        else:
            # === 情况 B：这是总文件计数 (Fetching 4 files) ===
            # 不要更新进度条！否则会由 100% 突然跳回 25%
            # 建议只在某个副标签显示总进度，或者干脆忽略
            current_file_idx = data.get("current")
            total_files = data.get("total")
            
            self._signal(text=f"{current_file_idx}/{total_files} files")
    
    # 下载模型，首先测试 huggingface.co 连通性，不可用则回退镜像 hf-mirror.com
    def _get_modeldir_download(self,model_name):   
        print(f'下载 {model_name=},proxy={config.proxy}')
        self._signal(text="Checking if the model exists")
        local_dir=f'{config.ROOT_DIR}/models/models--'
        if model_name in _MODELS:
            local_dir+=_MODELS[model_name].replace('/','--')
            repo_id=_MODELS[model_name]
        else:
            repo_id=model_name
            local_dir+=model_name.replace('/','--')
        Path(local_dir).mkdir(exist_ok=True,parents=True)
        # 已存在
        is_file=False
        if [it for it in Path(local_dir).glob('*.bin')] or [it for it in Path(local_dir).glob('*.safetensors')]:
            is_file=True
        if is_file:
            self._signal(text="The model already exists.")
            return local_dir
        
        try:
            requests.head('https://huggingface.co',timeout=5)
        except Exception:
            print(f'无法连接 huggingface.co, 使用镜像替换: hf-mirror.com, {model_name=}')
            endpoint = 'https://hf-mirror.com'
            if model_name in ['large-v3-turbo','turbo']:
                try:
                    # 针对 large-v3-turbo 模型使用 modelscope.cn 下载
                    return self._faster_turbo_from_modelscope(local_dir)
                except Exception as e:
                    print(f'阿里镜像下载 失败:{e}')
                    #失败继续使用镜像尝试
        else:
            print('可以使用 huggingface.co')
            endpoint = 'https://huggingface.co'

        
        Path(local_dir).mkdir(exist_ok=True, parents=True)
        # 不存在，判断缓存中是否存在
        # 用于兼容处理旧版本模型目录
        rs=self._is_model_cached(model_name, f"{config.ROOT_DIR}/models")
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
            self._signal(text="The model already exists.")
            return local_dir
        # 不存在，需要下载
        self._signal(text=f"Downloading the model from {endpoint} ...")
        from huggingface_hub import snapshot_download
        try:
            MyTqdmClass = tools.create_tqdm_class(self._progress_callback)
            snapshot_download(
                repo_id=repo_id,
                local_dir=local_dir,
                local_dir_use_symlinks=False,
                endpoint=endpoint,
                tqdm_class=MyTqdmClass,
                ignore_patterns=["*.msgpack", "*.h5", ".git*","*.md"]
            )
            self._signal(text="Downloaded end")

        except Exception as e:
            msg=f'下载模型失败，你可以打开以下网址，将 .bin/.txt/.json 文件下载到\n {local_dir} 文件夹内\n' if config.defaulelang=='zh' else f'The model download failed. You can try opening the following URL and downloading the .bin/.txt/.json files to the {local_dir} folder.'
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

    
    
    def _is_model_cached(self,repo_id: str, cache_dir: str = ''):
        try:
            # 将 repo_id 转换为缓存目录的命名格式
            if repo_id in _MODELS:
                org_name, model_name = _MODELS[repo_id].split('/')
                repo_cache_dir = Path(cache_dir) / f"models--{org_name}--{model_name}"
            else:
                repo_cache_dir = Path(cache_dir) / f"models--"/ repo_id.replace('/','--')
            
            # 检查是否存在 refs/main 文件以获取当前版本的哈希值
            refs_main_file = repo_cache_dir / "refs" / "main"
            if not refs_main_file.exists():
                return False

            with open(refs_main_file, 'r') as f:
                target_hash = f.read().strip()

            # 检查对应的 snapshots 目录
            snapshot_dir = repo_cache_dir / "snapshots" / target_hash
            if not snapshot_dir.exists():
                return False

            # 检查关键文件：config.json 和 model.bin
            for it in ["config.json", "model.bin", "tokenizer.json","vocabulary"]:
                if it =='vocabulary':
                    if not _is_file_valid(snapshot_dir / 'vocabulary.txt') and not _is_file_valid(snapshot_dir / 'vocabulary.json'):
                        return False
                    continue
                if not _is_file_valid(snapshot_dir / it):
                    return False
            return str(snapshot_dir)
        except Exception:
            return False

    def _is_file_valid(self,file_path) -> bool:
        try:
            if not file_path.exists():
                return False

            # 如果是符号链接，获取真实路径
            if file_path.is_symlink():
                real_path = file_path.resolve()
                # 确保解析后的路径仍然存在
                if not real_path.exists():
                    return False
                file_path = real_path

            # 检查文件大小
            return file_path.stat().st_size > 0

        except (OSError, ValueError):
            return False


            
            
        