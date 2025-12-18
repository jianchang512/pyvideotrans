# zh_recogn 识别
import json,os,requests,shutil
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union


from videotrans.configure import config
from videotrans.util import tools
from videotrans.recognition._base import BaseRecogn
from transformers import pipeline



@dataclass
class HuggingfaceRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()
        # 完整模型名称，目前只有 nvidia和UsefulSensors
        if self.model_name.startswith('parakeet'):
            self.model_name=f'nvidia/{self.model_name}'
        else:
            self.model_name=f'UsefulSensors/{self.model_name}'
        self.local_dir=f'{config.ROOT_DIR}/models/models--'+self.model_name.replace('/','--')

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit(): return
        # 检测设置hf镜像
        self.ensure_model_exists()
        result=[]
        p = pipeline(
            task="automatic-speech-recognition",
            model=self.local_dir,
            device_map="auto",
        )
        raws = self.cut_audio()
        for i, it in enumerate(raws):
            try:
                self._signal(text=f"{i+1}/{len(raws)}...")
                res=p(it['file'])
                if res.get('text'):
                    it['text']=res['text']
                    result.append(it)
            except Exception as e:
                config.logger.exception(e,exc_info=True)
        if result:
            return result
        raise RuntimeError(f'No recognition results found:{self.model_name}')

    
    def ensure_model_exists(self):
        """
        下载模型到指定目录，保持干净的文件结构。
        """
        if not Path(self.local_dir+"/model.safetensors").is_file() and not Path(self.local_dir+"/pytorch_model.bin").is_file():
            Path(self.local_dir).mkdir(exist_ok=True, parents=True)
        else:
            self._signal(text=f"{self.model_name} has exists")
            print('已存在模型')
            return
        from huggingface_hub import snapshot_download
        self.check_huggingface_connect()
        self._signal(text=f"Downloading {self.model_name} ...")
        try:
            snapshot_download(
                repo_id=self.model_name,
                local_dir=self.local_dir,
                local_dir_use_symlinks=False,
                ignore_patterns=["*.msgpack", "*.h5", ".git*", "*.bin","*.nemo"]
            )
        except Exception as e:
            raise RuntimeError(config.tr('downloading model.safetensors and all .json files',self.local_dir)+f'\n[https://huggingface.co/{self.model_name}/tree/main]\n\n')

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


    def check_huggingface_connect(self):
        proxy=config.proxy
        if proxy:
            os.environ['HTTPS_PROXY'] = proxy
            os.environ['HTTP_PROXY'] = proxy
        try:
            requests.head('https://huggingface.co', proxies=None if not proxy else {"http": proxy, "https": proxy}, timeout=5)
        except Exception as e:
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            os.environ["HF_HUB_DISABLE_XET"] = "1"
        else:
            os.environ['HF_ENDPOINT'] = 'https://huggingface.co'
            if os.environ.get("HF_HUB_DISABLE_XET"):
                os.environ.pop("HF_HUB_DISABLE_XET")

        with open(f'{config.ROOT_DIR}/logs/test-huggingface.log', "a", encoding='utf-8') as f:
            f.write(
                f"{proxy=},{os.environ.get('HTTPS_PROXY')=},{os.environ.get('HF_ENDPOINT')=},{os.environ.get('HF_HUB_DISABLE_XET')=}\n")
