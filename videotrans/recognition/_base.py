import copy
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Union

import torch
import zhconv

from videotrans.configure import config
from videotrans.configure._base import BaseCon

from videotrans.util import tools


class BaseRecogn(BaseCon):

    def __init__(self, detect_language=None, audio_file=None, cache_folder=None,
                 model_name=None, inst=None, uuid=None, is_cuda=None,target_code=None,subtitle_type=0):
        super().__init__()
        # 需要判断当前是主界面任务还是单独任务，用于确定使用哪个字幕编辑区
        self.detect_language = detect_language
        self.audio_file = audio_file
        self.cache_folder = cache_folder
        self.model_name = model_name
        self.inst = inst
        self.uuid = uuid
        self.is_cuda = is_cuda
        self.subtitle_type=subtitle_type
        self.has_done = False
        self.error = ''
        self.device="cuda" if  torch.cuda.is_available() else 'cpu'


        self.api_url = ''
        self.proxies = None

        self.flag = [
            ",",
            
            ".",
            "?",
            "!",
            ";",
           
            "，",
            "。",
            "？",
            "；",      
            "！"
        ]
        
        self.join_word_flag = " "
        
        self.jianfan=False
        if self.detect_language[:2].lower() in ['zh', 'ja', 'ko']:
            self.maxlen = int(float(config.settings.get('cjk_len',20)))
            self.jianfan = True if self.detect_language[:2] == 'zh' and config.settings['zh_hant_s'] else False
        else:
            self.maxlen = int(float(config.settings.get('other_len',60)))
        
        if not tools.vail_file(self.audio_file):
            raise Exception(f'[error]not exists {self.audio_file}')

    # 出错时发送停止信号
    def run(self) -> Union[List[Dict], None]:
        self._signal(text="")
        try:
            if self.detect_language[:2].lower() in ['zh', 'ja', 'ko']:
                self.flag.append(" ")
                self.join_word_flag = ""
            return self._exec()
        except Exception as e:
            config.logger.exception(e, exc_info=True)
            msg = f'{str(e)}'
            if re.search(r'cudaErrorNoKernelImageForDevice', msg, re.I) is not None:
                msg=f'请升级显卡驱动并安装CUDA 12.x，如果已是该版本，可能你的显卡太旧不兼容pytorch2.5，请取消CUDA加速:{msg}' if config.defaulelang=='zh' else f'Please upgrade your graphics card driver and install CUDA 12.x, or cancel CUDA acceleration:{msg}'
            elif re.search(r'cub[a-zA-Z0-9_.-]+?\.dll', msg, re.I | re.M) is not None:
                msg = f'【缺少cuBLAS.dll】请点击菜单栏-帮助/支持-下载cublasxx.dll,或者切换为openai模型 {msg} ' if config.defaulelang == 'zh' else f'[missing cublasxx.dll] Open menubar Help&Support->Download cuBLASxx.dll or use openai model {msg}'
            elif re.search(r'out\s+?of.*?memory', msg, re.I):
                msg = f'显存不足，请使用较小模型，比如 tiny/base/small {msg}' if config.defaulelang == 'zh' else f'Insufficient video memory, use a smaller model such as tiny/base/small {msg}'
            elif re.search(r'cudnn', msg, re.I):
                msg = f'cuDNN错误，请尝试升级显卡驱动，重新安装CUDA12.x和cuDNN9 {msg}' if config.defaulelang == 'zh' else f'cuDNN error, please try upgrading the graphics card driver and reinstalling CUDA12.x and cuDNN9 {msg}'
            self._signal(text=msg, type="error")
            raise
        finally:
            if self.shound_del:
                self._set_proxy(type='del')

    def _exec(self) -> Union[List[Dict], None]:
        pass

    def re_segment_sentences(self,words,langcode=None):
        
        try:
            from videotrans.translator._chatgpt import ChatGPT
            ob=ChatGPT()
            if self.inst and self.inst.status_text:
                self.inst.status_text="正在重新断句..." if config.defaulelang=='zh' else "Re-segmenting..."
            return ob.llm_segment(words,self.inst)
        except json.decoder.JSONDecodeError as e:
            self.inst.status_text="使用LLM重新断句失败" if config.defaulelang=='zh' else "Re-segmenting Error"
            config.logger.error(f"使用ChatGPT重新断句失败[JSONDecodeError]，已恢复原样 {e}")
            raise
        except Exception as e:
            self.inst.status_text="使用LLM重新断句失败" if config.defaulelang=='zh' else "Re-segmenting Error"
            config.logger.error(f"使用ChatGPT重新断句失败[except]，已恢复原样 {e}")
            raise

    # True 退出
    def _exit(self) -> bool:
        if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
            return True
        return False
