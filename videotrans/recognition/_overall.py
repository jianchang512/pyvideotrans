import threading
import time, json, shutil
import os
from pathlib import Path
from dataclasses import dataclass
from videotrans.configure import config

from videotrans.recognition._base import BaseRecogn

import requests
from videotrans.util import tools
from pydub import AudioSegment
from videotrans.process import openai_whisper, faster_whisper

"""
faster-whisper
内置的本地大模型不重试
"""
_MODELS= {
    "tiny.en": "Systran/faster-whisper-tiny.en",
    "tiny": "Systran/faster-whisper-tiny",
    "base.en": "Systran/faster-whisper-base.en",
    "base": "Systran/faster-whisper-base",
    "small.en": "Systran/faster-whisper-small.en",
    "small": "Systran/faster-whisper-small",
    "medium.en": "Systran/faster-whisper-medium.en",
    "medium": "Systran/faster-whisper-medium",
    "large-v1": "Systran/faster-whisper-large-v1",
    "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3",
    "large": "Systran/faster-whisper-large-v3",
    "distil-large-v2": "Systran/faster-distil-whisper-large-v2",
    "distil-medium.en": "Systran/faster-distil-whisper-medium.en",
    "distil-small.en": "Systran/faster-distil-whisper-small.en",
    "distil-large-v3": "Systran/faster-distil-whisper-large-v3",
    "distil-large-v3.5": "distil-whisper/distil-large-v3.5-ct2",
    "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    "turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
}


@dataclass
class FasterAll(BaseRecogn):
    def __post_init__(self):
        super().__post_init__()
        local_dir = f'{config.ROOT_DIR}/models/models--'
        if self.model_name in _MODELS:
            local_dir += _MODELS[self.model_name].replace('/', '--')
        else:
            local_dir += self.model_name.replace('/', '--')
        self.local_dir = local_dir
        self.audio_duration=len(AudioSegment.from_wav(self.audio_file))
        self.speech_timestamps_file=None

    def _exec(self):
        if self._exit():
            return
        self.error = ''
        self._signal(text="STT starting, hold on...")
        if self.recogn_type == 1:  # openai-whisper
            raws = self._openai()
        else:
            raws = self._faster()
        return raws

    def _download(self):
        if self.recogn_type == 0:
            if self.model_name in _MODELS:
                repo_id = _MODELS[self.model_name]
            else:
                repo_id = self.model_name
            tools.check_and_down_hf(self.model_name,repo_id,self.local_dir,callback=self._progress_callback)
        # 批量时预先vad切分
        # batch_size==1 时不切分
        if int(config.settings.get('batch_size', 4))>1:
            self._vad_split()
            self.speech_timestamps_file=f'{self.cache_folder}/speech_timestamps_{time.time()}.json'
            Path(self.speech_timestamps_file).write_text(json.dumps(self.speech_timestamps),encoding='utf-8')


    def _openai(self):
        title=f'STT use {self.model_name}'
        self._signal(text=title)
        # 起一个进程
        logs_file = f'{config.TEMP_DIR}/{self.uuid}/openai-{self.detect_language}-{time.time()}.log'
        kwargs = {
            "prompt": config.settings.get(
                f'initial_prompt_{self.detect_language}') if self.detect_language != 'auto' else None,
            "detect_language": self.detect_language,
            "model_name": self.model_name,
            "ROOT_DIR": config.ROOT_DIR,
            "logs_file": logs_file,
            "defaulelang": config.defaulelang,
            "is_cuda": self.is_cuda,
            "no_speech_threshold": float(config.settings.get('no_speech_threshold', 0.5)),
            "condition_on_previous_text": config.settings.get('condition_on_previous_text', False),
            "speech_timestamps": self.speech_timestamps_file,
            "audio_file": self.audio_file,
            "TEMP_ROOT": config.TEMP_ROOT,
            "jianfan": self.jianfan,
            "batch_size":int(config.settings.get('batch_size', 8)),
            "audio_duration":self.audio_duration,
            "temperature":config.settings.get('temperature'),
            "compression_ratio_threshold":float(config.settings.get('compression_ratio_threshold',2.2)),
        }
        raws=self._new_process(callback=openai_whisper,title=title,is_cuda=self.is_cuda,kwargs=kwargs)
        return raws


    def _faster(self):
        title=f"STT use {self.model_name}"
        self._signal(text=title)
        logs_file = f'{config.TEMP_DIR}/{self.uuid}/faster-{self.detect_language}-{time.time()}.log'

        kwargs = {
            "detect_language": self.detect_language,
            "model_name": self.model_name,
            "ROOT_DIR": config.ROOT_DIR,
            "logs_file": logs_file,
            "defaulelang": config.defaulelang,
            "is_cuda": self.is_cuda,
            "no_speech_threshold": float(config.settings.get('no_speech_threshold', 0.5)),
            "condition_on_previous_text": config.settings.get('condition_on_previous_text', False),
            "speech_timestamps": self.speech_timestamps_file,
            "audio_file": self.audio_file,
            "TEMP_ROOT": config.TEMP_ROOT,
            "local_dir": self.local_dir,
            "compute_type": config.settings.get('cuda_com_type', 'default'),
            "batch_size": int(config.settings.get('batch_size', 4)),
            "jianfan": self.jianfan,
            "audio_duration":self.audio_duration,
            "hotwords":config.settings.get('hotwords'),
            "prompt": config.settings.get(f'initial_prompt_{self.detect_language}') if self.detect_language != 'auto' else None,
            "beam_size": int(config.settings.get('beam_size', 5)),
            "best_of": int(config.settings.get('best_of', 5)),
            "temperature":config.settings.get('temperature'),
            "repetition_penalty":float(config.settings.get('repetition_penalty',1.0)),
            "compression_ratio_threshold":float(config.settings.get('compression_ratio_threshold',2.2)),

        }

        raws=self._new_process(callback=faster_whisper,title=title,is_cuda=self.is_cuda,kwargs=kwargs)
        return raws

    # data={type,percent,filename,current,total}
    def _progress_callback(self, data):
        msg_type = data.get("type")
        try:
            percent = float(data.get("percent",'0'))
        except:
            percent=1
            
        filename = data.get("filename")

        if msg_type == "file":

            # 标签显示当前文件名
            self._signal(text=f"{config.tr('Downloading please wait')} {filename} {percent:.2f}%")

        else:
            # === 情况 B：这是总文件计数 (Fetching 4 files) ===
            # 不要更新进度条！否则会由 100% 突然跳回 25%
            # 建议只在某个副标签显示总进度，或者干脆忽略
            current_file_idx = data.get("current")
            total_files = data.get("total")

            self._signal(text=f"{config.tr('Downloading please wait')}{self.model_name} {current_file_idx}/{total_files}")



