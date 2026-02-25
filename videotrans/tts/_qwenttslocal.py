import os
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import requests,json
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log, \
    RetryError

from gradio_client import Client, handle_file, client

from videotrans import translator
from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT, StopRetry
from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
from videotrans.process import qwen3tts_fun

@dataclass
class QwenttsLocal(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        self.model_name="1.7B"
        _langnames = translator.LANG_CODE.get(self.language, [])
        if _langnames and len(_langnames) >= 10:
            self.target_language = _langnames[9]
        else:
            self.target_language = 'Auto'
        self.target_language=self.target_language.capitalize()

    
    def _download(self):
        if defaulelang == 'zh':
            tools.check_and_down_ms(f'Qwen/Qwen3-TTS-12Hz-{self.model_name}-Base',callback=self._process_callback,local_dir=f'{ROOT_DIR}/models/models--Qwen--Qwen3-TTS-12Hz-{self.model_name}-Base')
            tools.check_and_down_ms(f'Qwen/Qwen3-TTS-12Hz-{self.model_name}-CustomVoice',callback=self._process_callback,local_dir=f'{ROOT_DIR}/models/models--Qwen--Qwen3-TTS-12Hz-{self.model_name}-CustomVoice')
        else:
            tools.check_and_down_hf(model_id=f'Qwen3-TTS-12Hz-{self.model_name}-Base',repo_id=f'Qwen/Qwen3-TTS-12Hz-{self.model_name}-Base',local_dir=f'{ROOT_DIR}/models/models--Qwen--Qwen3-TTS-12Hz-{self.model_name}-Base',callback=self._process_callback)
            tools.check_and_down_hf(model_id=f'Qwen3-TTS-12Hz-{self.model_name}-CustomVoice',repo_id=f'Qwen/Qwen3-TTS-12Hz-{self.model_name}-CustomVoice',local_dir=f'{ROOT_DIR}/models/models--Qwen--Qwen3-TTS-12Hz-{self.model_name}-CustomVoice',callback=self._process_callback)


    def _exec(self):
        Path(f'{TEMP_DIR}/{self.uuid}').mkdir(parents=True,exist_ok=True)
        logs_file = f'{TEMP_DIR}/{self.uuid}/qwen3tts-{time.time()}.log'
        
        queue_tts_file = f'{TEMP_DIR}/{self.uuid}/queuetts-{time.time()}.json'
        Path(queue_tts_file).write_text(json.dumps(self.queue_tts),encoding='utf-8')
        title="Qwen3-TTS"
        kwargs = {            
            "queue_tts_file":queue_tts_file,
            "language": self.target_language,
            "logs_file": logs_file,
            "defaulelang": defaulelang,
            "is_cuda": self.is_cuda,
            "model_name":self.model_name,
            "roledict":tools.get_qwenttslocal_rolelist(),
            "prompt":params.get('qwenttslocal_prompt', '')
        }
        self._new_process(callback=qwen3tts_fun,title=title,is_cuda=self.is_cuda,kwargs=kwargs)
    
        self._signal(text=f'convert wav')
        all_task = []
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(4,len(self.queue_tts),os.cpu_count())) as pool:
            for item in self.queue_tts:
                filename=item.get('filename','')+"-qwen3tts.wav"
                if tools.vail_file(filename):
                    all_task.append(pool.submit(self.convert_to_wav, filename,item['filename']))
            if len(all_task) > 0:
                _ = [i.result() for i in all_task]

    def _item_task(self, data_item):
        pass
