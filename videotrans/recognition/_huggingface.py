# zh_recogn 识别
import re, sys, os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union

from videotrans.configure import config
from videotrans.configure.config import ROOT_DIR, logger, settings, TEMP_DIR, defaulelang
from videotrans.process import faster_whisper, pipe_asr
from videotrans.util import tools
from videotrans.recognition._base import BaseRecogn
from pydub import AudioSegment
import json, shutil, requests
from huggingface_hub import snapshot_download


@dataclass
class HuggingfaceRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()
        self.local_dir = f'{ROOT_DIR}/models/models--' + self.model_name.replace('/', '--')
        self._signal(text=f"use {self.model_name}")
        self.audio_duration=len(AudioSegment.from_wav(self.audio_file))

    def _download(self):
        tools.check_and_down_hf(self.model_name,self.model_name,self.local_dir,callback=self._process_callback)

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit(): return
        self._signal(text=f"loading {self.model_name}")
        logger.debug(f'[HuggingfaceRecogn]_exec:{self.model_name=}')

        if self.model_name in ['JhonVanced/whisper-large-v3-japanese-4k-steps-ct2',
                               'zh-plus/faster-whisper-large-v2-japanese-5k-steps', 'Systran/faster-whisper-tiny']:
            if int(settings.get('batch_size', 4))>1:
                self._vad_split() 
            result = self._faster()
        else:
            # self.model_name in ['nvidia/parakeet-ctc-1.1b','biodatlab/whisper-th-medium','biodatlab/whisper-th-large-v3','kotoba-tech/kotoba-whisper-v2.0',,'suzii/vi-whisper-large-v3-turbo-v1','reazon-research/japanese-wav2vec2-large-rs35kh','jonatasgrosman/wav2vec2-large-xlsr-53-japanese']:
            result = self._pipe_asr()
        if result:
            return result
        raise RuntimeError(f'No recognition results found:{self.model_name}')

    def _pipe_asr(self):
        # 1. 准备数据

        title=f"load {self.model_name}"
        self._signal(text=title)
        logs_file = f'{TEMP_DIR}/{self.uuid}/huggingface-pipeasr-{self.detect_language}-{time.time()}.log'
        cut_audio_list_file = f'{TEMP_DIR}/{self.uuid}/cut_audio_list_{time.time()}.json'
        Path(cut_audio_list_file).write_text(json.dumps(self.cut_audio()),encoding='utf-8')
        kwargs = {
            "cut_audio_list": cut_audio_list_file,
            "prompt": settings.get(
                f'initial_prompt_{self.detect_language}') if self.detect_language != 'auto' else None,
            "detect_language": self.detect_language,
            "model_name": self.model_name,
            "logs_file": logs_file,
            "is_cuda": self.is_cuda,
            "audio_file": None,
            "local_dir": self.local_dir,
            "batch_size": int(settings.get('batch_size', 4)),
            "jianfan": self.jianfan
        }
        raws=self._new_process(callback=pipe_asr,title=title,is_cuda=self.is_cuda,kwargs=kwargs)
        return raws

    # JhonVanced/whisper-large-v3-japanese-4k-steps-ct2','zh-plus/faster-whisper-large-v2-japanese-5k-steps
    def _faster(self):
        title=f"load {self.model_name}"
        self._signal(text=title)
        logs_file = f'{TEMP_DIR}/{self.uuid}/huggingface-faster-{self.detect_language}-{time.time()}.log'
        speech_timestamps_file=None
        if self.speech_timestamps:
            speech_timestamps_file = f'{TEMP_DIR}/{self.uuid}/speech_timestamps_{time.time()}.json'
            Path(speech_timestamps_file).write_text(json.dumps(self.speech_timestamps),encoding='utf-8')
        kwargs = {
            "prompt": settings.get(
                f'initial_prompt_{self.detect_language}') if self.detect_language != 'auto' else None,
            "detect_language": self.detect_language,
            "model_name": self.model_name,
            "logs_file": logs_file,
            "is_cuda": self.is_cuda,
            "no_speech_threshold": float(settings.get('no_speech_threshold', 0.5)),
            "condition_on_previous_text": settings.get('condition_on_previous_text', False),
            "speech_timestamps": speech_timestamps_file,
            "audio_file": self.audio_file,
            "local_dir": self.local_dir,
            "compute_type": settings.get('cuda_com_type', 'default'),
            "batch_size": int(settings.get('batch_size', 4)),
            "beam_size": int(settings.get('beam_size', 5)),
            "best_of": int(settings.get('best_of', 5)),
            "jianfan": self.jianfan,
            "audio_duration":self.audio_duration,
            "temperature":settings.get('temperature'),
            "hotwords":settings.get('hotwords'),
            "repetition_penalty": float(settings.get('repetition_penalty', 1.0)),
            "compression_ratio_threshold": float(settings.get('compression_ratio_threshold', 2.2)),
        }
        raws=self._new_process(callback=faster_whisper,title=title,is_cuda=self.is_cuda,kwargs=kwargs)

        return raws

