# zh_recogn 识别
import re,sys,os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union


from videotrans.configure import config
from videotrans.util import tools
from videotrans.recognition._base import BaseRecogn

import json,shutil,requests
from huggingface_hub import snapshot_download


@dataclass
class HuggingfaceRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()
        config.logger.debug(f'HuggingfaceRecogn 初始化')
        self.local_dir=f'{config.ROOT_DIR}/models/models--'+self.model_name.replace('/','--')
        self._signal(text=f"use {self.model_name}")

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit(): return
        config.logger.debug(f'[HuggingfaceRecogn]_exec {time.time()=}:{self.model_name=}')
        self._get_modeldir_download()
        result=[]        
        if self.model_name in ['JhonVanced/whisper-large-v3-japanese-4k-steps-ct2','zh-plus/faster-whisper-large-v2-japanese-5k-steps']:
            result=self._faster()
        else:
            #self.model_name in ['nvidia/parakeet-ctc-1.1b','biodatlab/whisper-th-medium','biodatlab/whisper-th-large-v3','kotoba-tech/kotoba-whisper-v2.0',,'suzii/vi-whisper-large-v3-turbo-v1','reazon-research/japanese-wav2vec2-large-rs35kh','jonatasgrosman/wav2vec2-large-xlsr-53-japanese']:
            result=self._pipe_asr()

        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
        except Exception:
            pass
        if result:
            return result
        raise RuntimeError(f'No recognition results found:{self.model_name}')

    def _pipe_asr(self):
        config.logger.debug(f'before import pipeline {int(time.time())}')
        from transformers import pipeline
        import torch
        config.logger.debug(f'after import pipeline {int(time.time())}')
        raws = self.cut_audio()
        p = pipeline(
            task="automatic-speech-recognition",
            model=self.local_dir,
            device_map="cuda:0" if self.is_cuda else "auto",
            dtype=torch.float16 if self.is_cuda else torch.float32,
        )
        config.logger.debug(f'use device={(p.model.device)}')
        generate_kwargs={"language": self.detect_language[:2], "task": "transcribe"}
        if self.model_name in ['nvidia/parakeet-ctc-1.1b']:
            generate_kwargs={}
        def inputs_generator():
            for item in raws:
                yield item['file']
        results_iterator = p(
            inputs_generator(), 
            batch_size=4, 
            generate_kwargs=generate_kwargs,
            ignore_warning=True
        )     
        total = len(raws)

        for i, (it,res) in enumerate(zip(raws, results_iterator)):
            self._signal(text=f"subtitles {i+1}/{total}...")
            res=p(it['file'],ignore_warning=True,generate_kwargs=generate_kwargs)
            if 'file' in it:
                del it['file']

            if res.get('text'):
                it['text']=re.sub(r'<unk>|</unk>','',res['text'])
                self._signal(text=f'{it["text"]}\n', type="subtitle")       
        del p
        return raws
        
    # JhonVanced/whisper-large-v3-japanese-4k-steps-ct2','zh-plus/faster-whisper-large-v2-japanese-5k-steps  
    def _faster(self):
        from faster_whisper import WhisperModel
        raws=self.cut_audio()
        model = WhisperModel(
                self.local_dir,
                device="cuda" if self.is_cuda else "auto"
        )
        for i,it in enumerate(raws):
            segments, info = model.transcribe(
                it['file'],
                beam_size=int(config.settings.get('beam_size',5)),
                best_of=int(config.settings.get('best_of',5)),
                no_speech_threshold=float(config.settings.get('no_speech_threshold',0.5)),
                condition_on_previous_text=bool(config.settings.get('condition_on_previous_text',False)),
                word_timestamps=False,
                vad_filter=False,   
                temperature=0,
                language=self.detect_language.split('-')[0] if self.detect_language and self.detect_language != 'auto' else None
            )
            del it['file']

            text=''
            for segment in segments:
                text+=segment.text
            if text:
                it['text']=text
                self._signal(text=f'{text}\n', type="subtitle")
                self._signal(text=f' Subtitles {len(raws) + 1} ')
        
        
        return raws
    
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



