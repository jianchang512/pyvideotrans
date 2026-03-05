import time, json, shutil
from pathlib import Path
from dataclasses import dataclass
from videotrans.configure.config import  settings, ROOT_DIR, TEMP_DIR
from videotrans.recognition._base import BaseRecogn

from videotrans.util import tools
from pydub import AudioSegment
from videotrans.process import openai_whisper, faster_whisper
from videotrans.util.contants import FASTER_MODELS_DICT

@dataclass
class FasterAll(BaseRecogn):
    def __post_init__(self):
        super().__post_init__()
        local_dir = f'{ROOT_DIR}/models/models--'
        if self.model_name in FASTER_MODELS_DICT:
            local_dir += FASTER_MODELS_DICT[self.model_name].replace('/', '--')
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
            if self.model_name in FASTER_MODELS_DICT:
                repo_id = FASTER_MODELS_DICT[self.model_name]
            else:
                repo_id = self.model_name
            tools.check_and_down_hf(self.model_name,repo_id,self.local_dir,callback=self._process_callback)
        # 批量时预先vad切分
        # 否则后断句处理
        if settings.get('whisper_prepare'):
            self._vad_split()
            self.speech_timestamps_file=f'{self.cache_folder}/speech_timestamps_{time.time()}.json'
            Path(self.speech_timestamps_file).write_text(json.dumps(self.speech_timestamps),encoding='utf-8')


    def _openai(self):
        title=f'STT use {self.model_name}'
        self._signal(text=title)
        # 起一个进程
        logs_file = f'{TEMP_DIR}/{self.uuid}/openai-{self.detect_language}-{time.time()}.log'
        kwargs = {
            "prompt": settings.get(
                f'initial_prompt_{self.detect_language}') if self.detect_language != 'auto' else None,
            "detect_language": self.detect_language,
            "model_name": self.model_name,
            "logs_file": logs_file,
            "is_cuda": self.is_cuda,
            "no_speech_threshold": float(settings.get('no_speech_threshold', 0.5)),
            "condition_on_previous_text": settings.get('condition_on_previous_text', False),
            "speech_timestamps": self.speech_timestamps_file,
            "audio_file": self.audio_file,
            "jianfan": self.jianfan,
            "audio_duration":self.audio_duration,
            "temperature":settings.get('temperature'),
            "compression_ratio_threshold":float(settings.get('compression_ratio_threshold',2.2)),
            "max_speech_ms":int(float(settings.get('max_speech_duration_s', 6)) * 1000)
        }
        raws=self._new_process(callback=openai_whisper,title=title,is_cuda=self.is_cuda,kwargs=kwargs)
        return raws


    def _faster(self):
        title=f"STT use {self.model_name}"
        self._signal(text=title)
        logs_file = f'{TEMP_DIR}/{self.uuid}/faster-{self.detect_language}-{time.time()}.log'

        kwargs = {
            "detect_language": self.detect_language,
            "model_name": self.model_name,
            "logs_file": logs_file,
            "is_cuda": self.is_cuda,
            "no_speech_threshold": float(settings.get('no_speech_threshold', 0.5)),
            "condition_on_previous_text": settings.get('condition_on_previous_text', False),
            "speech_timestamps": self.speech_timestamps_file,
            "audio_file": self.audio_file,
            "local_dir": self.local_dir,
            "compute_type": settings.get('cuda_com_type', 'default'),
            "jianfan": self.jianfan,
            "audio_duration":self.audio_duration,
            "hotwords":settings.get('hotwords'),
            "prompt": settings.get(f'initial_prompt_{self.detect_language}') if self.detect_language != 'auto' else None,
            "beam_size": int(settings.get('beam_size', 5)),
            "best_of": int(settings.get('best_of', 5)),
            "temperature":settings.get('temperature'),
            "repetition_penalty":float(settings.get('repetition_penalty',1.0)),
            "compression_ratio_threshold":float(settings.get('compression_ratio_threshold',2.2)),
            "max_speech_ms":int(float(settings.get('max_speech_duration_s', 6)) * 1000)
        }

        raws=self._new_process(callback=faster_whisper,title=title,is_cuda=self.is_cuda,kwargs=kwargs)
        return raws


