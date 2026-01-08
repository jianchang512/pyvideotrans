# zh_recogn 识别
import re,sys,os
import threading
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union


from videotrans.configure import config
from videotrans.process import faster_whisper, pipe_asr
from videotrans.util import tools
from videotrans.recognition._base import BaseRecogn

import json,shutil,requests
from huggingface_hub import snapshot_download


@dataclass
class HuggingfaceRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()
        self.local_dir=f'{config.ROOT_DIR}/models/models--'+self.model_name.replace('/','--')
        self._signal(text=f"use {self.model_name}")

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit(): return
        self._signal(text=f"loading {self.model_name}")
        config.logger.debug(f'[HuggingfaceRecogn]_exec:{self.model_name=}')
        self._get_modeldir_download()
        if self.model_name in ['JhonVanced/whisper-large-v3-japanese-4k-steps-ct2','zh-plus/faster-whisper-large-v2-japanese-5k-steps','Systran/faster-whisper-tiny']:
            result=self._faster()
        else:
            #self.model_name in ['nvidia/parakeet-ctc-1.1b','biodatlab/whisper-th-medium','biodatlab/whisper-th-large-v3','kotoba-tech/kotoba-whisper-v2.0',,'suzii/vi-whisper-large-v3-turbo-v1','reazon-research/japanese-wav2vec2-large-rs35kh','jonatasgrosman/wav2vec2-large-xlsr-53-japanese']:
            result=self._pipe_asr()
        if result:
            return result
        raise RuntimeError(f'No recognition results found:{self.model_name}')

    def _pipe_asr(self):
        # 1. 准备数据
        raws = self.cut_audio()
        self._signal(text=f"load {self.model_name}")
        logs_file=f'{config.TEMP_DIR}/{self.uuid}/huggingface-pipeasr-{self.detect_language}-{time.time()}.log'
        kwars={
            "cut_audio_list":raws,
            "prompt": config.settings.get(f'initial_prompt_{self.detect_language}') if self.detect_language != 'auto' else None,
            "detect_language":self.detect_language,
            "model_name":self.model_name,
            "ROOT_DIR":config.ROOT_DIR,
            "logs_file":logs_file,
            "defaulelang":config.defaulelang,
            "is_cuda":self.is_cuda,
            "audio_file":None,
            "TEMP_ROOT":config.TEMP_ROOT,
            "local_dir":self.local_dir,
            "batch_size":int(config.settings.get('batch_size', 8)),
            "jianfan":self.jianfan
        }
        # 获取进度
        threading.Thread(target=self._process,args=(logs_file,),daemon=True).start()
        with ProcessPoolExecutor(max_workers=1) as executor:
                # 提交任务，并显式传入参数，确保子进程拿到正确的参数
                future = executor.submit(
                    pipe_asr,
                    **kwars
                )
                # .result() 会阻塞当前线程直到子进程计算完毕，并返回结果
                raws = future.result()
        if isinstance(raws,str):
            raise RuntimeError(raws)
        return raws

    # JhonVanced/whisper-large-v3-japanese-4k-steps-ct2','zh-plus/faster-whisper-large-v2-japanese-5k-steps
    def _faster(self):
        self._signal(text=f"load {self.model_name}")
        logs_file=f'{config.TEMP_DIR}/{self.uuid}/huggingface-faster-{self.detect_language}-{time.time()}.log'
        kwars={
            "prompt": config.settings.get(f'initial_prompt_{self.detect_language}') if self.detect_language != 'auto' else None,
            "detect_language":self.detect_language,
            "model_name":self.model_name,
            "ROOT_DIR":config.ROOT_DIR,
            "logs_file":logs_file,
            "defaulelang":config.defaulelang,
            "is_cuda":self.is_cuda,
            "no_speech_threshold":float(config.settings.get('no_speech_threshold',0.5)),
            "condition_on_previous_text":config.settings.get('condition_on_previous_text',False),
            "speech_timestamps":self.speech_timestamps,
            "audio_file":self.audio_file,
            "TEMP_ROOT":config.TEMP_ROOT,
            "local_dir":self.local_dir,
            "compute_type":config.settings.get('cuda_com_type', 'default'),
            "batch_size":int(config.settings.get('batch_size', 8)),
            "beam_size":int(config.settings.get('beam_size', 5)),
            "best_of":int(config.settings.get('best_of', 5)),
            "jianfan":self.jianfan
        }
        # 获取进度
        threading.Thread(target=self._process,args=(logs_file,),daemon=True).start()
        raws=[]
        with ProcessPoolExecutor(max_workers=1) as executor:
                # 提交任务，并显式传入参数，确保子进程拿到正确的参数
                future = executor.submit(
                    faster_whisper,
                    **kwars
                )
                # .result() 会阻塞当前线程直到子进程计算完毕，并返回结果
                raws = future.result()
        if isinstance(raws,str):
            raise RuntimeError(raws)
        return raws

    # 获取进度
    def _process(self,logs_file):
        last_mtime=0
        while 1:
            _p=Path(logs_file)
            if _p.is_file() and _p.stat().st_mtime!=last_mtime:
                last_mtime=_p.stat().st_mtime
                _tmp=json.loads(_p.read_text(encoding='utf-8'))
                self._signal(text=_tmp.get('text'),type=_tmp.get('type','logs'))
                if _tmp.get('type','')=='error':
                    return
            time.sleep(0.5)



    def _progress_callback(self, data):
        """
        这个方法会被 tqdm 内部调用。
        在这里将数据压入队列。
        """
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

    
    def _get_modeldir_download(self):

        """
        下载模型到指定目录，保持干净的文件结构。
        """
        Path(self.local_dir).mkdir(exist_ok=True, parents=True)
        is_file=False
        if [it for it in Path(self.local_dir).glob('*.bin')] or [it for it in Path(self.local_dir).glob('*.safetensors')]:
            is_file=True
        if is_file:
            self._signal(text=f"{self.model_name} has exists")
            print('已存在模型')
            return
        self._signal(text=f"Downloading {self.model_name} ...")
        # 先测试能否连接 huggingface.co, 中国大陆地区不可访问，除非使用VPN
        try:
            requests.head('https://huggingface.co',timeout=5)
        except Exception:
            print('无法连接 huggingface.co, 使用镜像替换: hf-mirror.com')
            endpoint = 'https://hf-mirror.com'
            os.environ["HF_HUB_DISABLE_XET"] = "1"
        else:
            print('可以使用 huggingface.co')
            endpoint = 'https://huggingface.co'
            os.environ["HF_HUB_DISABLE_XET"] = "0"
        try:
            MyTqdmClass = tools.create_tqdm_class(self._progress_callback)
            print(f'{self.model_name=}##################')
            snapshot_download(
                repo_id=self.model_name,
                local_dir=self.local_dir,
                local_dir_use_symlinks=False,
                endpoint=endpoint,
                etag_timeout=5,
                tqdm_class=MyTqdmClass,
                ignore_patterns=["*.msgpack", "*.h5", ".git*"]
            )
            self._signal(text="Downloaded end")
            
        except Exception as e:
            raise RuntimeError(config.tr('downloading all files',self.local_dir)+f'\n[https://huggingface.co/{self.model_name}/tree/main]\n\n')

        """删除 huggingface_hub 下载时产生的缓存文件夹"""
        junk_paths = [
            ".cache",
            "blobs",
            "refs",
            "snapshots",
            ".no_exist"
        ]
        
        for junk in junk_paths:
            full_path = Path(self.local_dir) / junk
            if full_path.exists():
                try:
                    if full_path.is_dir():
                        shutil.rmtree(full_path) # 强制删除文件夹
                    else:
                        os.remove(full_path)     # 删除文件
                    print(f"已清理: {junk}")
                except Exception as e:
                    print(f"清理 {junk} 失败: {e}")
        self._signal(text=f"Downloaded ")



