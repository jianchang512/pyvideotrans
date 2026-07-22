import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
import json
from videotrans import translator
from videotrans.configure.config import ROOT_DIR,params,defaulelang,TEMP_DIR
from videotrans.tts._base import BaseTTS
from videotrans.util.help_misc import vail_file


@dataclass
class QwenttsLocal(BaseTTS):
    target_language: str = None
    
    def __post_init__(self):
        super().__post_init__()
        self.model_name="0.6B"
        _langnames = translator.LANG_CODE.get(self.language, [])
        self.target_language = _langnames[9].capitalize() if _langnames and len(_langnames) >= 10 else 'Auto'

    
    def _download(self):
        from videotrans.util import help_down
        if defaulelang == 'zh':
            self.local_dir=f'{ROOT_DIR}/models/models--Qwen--Qwen3-TTS-12Hz-{self.model_name}-Base'
            help_down.check_and_down_ms(f'Qwen/Qwen3-TTS-12Hz-{self.model_name}-Base',callback=self._process_callback,local_dir=self.local_dir)
            
            self.local_dir=f'{ROOT_DIR}/models/models--Qwen--Qwen3-TTS-12Hz-{self.model_name}-CustomVoice'
            help_down.check_and_down_ms(f'Qwen/Qwen3-TTS-12Hz-{self.model_name}-CustomVoice',callback=self._process_callback,local_dir=self.local_dir)
        else:
            self.local_dir=f'{ROOT_DIR}/models/models--Qwen--Qwen3-TTS-12Hz-{self.model_name}-Base'
            help_down.check_and_down_hf(model_id=f'Qwen3-TTS-12Hz-{self.model_name}-Base',repo_id=f'Qwen/Qwen3-TTS-12Hz-{self.model_name}-Base',local_dir=self.local_dir,callback=self._process_callback)
            
            self.local_dir=f'{ROOT_DIR}/models/models--Qwen--Qwen3-TTS-12Hz-{self.model_name}-CustomVoice'
            help_down.check_and_down_hf(model_id=f'Qwen3-TTS-12Hz-{self.model_name}-CustomVoice',repo_id=f'Qwen/Qwen3-TTS-12Hz-{self.model_name}-CustomVoice',local_dir=self.local_dir,callback=self._process_callback)


    def _exec(self):
        logs_file = f'{TEMP_DIR}/{self.uuid}/qwen3tts-{time.time()}.log'
        queue_tts_file = f'{TEMP_DIR}/{self.uuid}/queuetts-{time.time()}.json'
        Path(queue_tts_file).write_text(json.dumps(self.queue_tts),encoding='utf-8')
        title="Qwen3-TTS dubbing..."
        kwargs = {
            "queue_tts_file":queue_tts_file,
            "language": self.target_language,
            "logs_file": logs_file,
            "is_cuda": self.is_cuda,
            "model_name":self.model_name,
            "prompt":params.get('qwenttslocal_prompt', '')
        }
        from videotrans.process.qwen_tts import qwen3tts_fun
        self._new_process(callback=qwen3tts_fun,title=title,is_cuda=self.is_cuda,kwargs=kwargs)
        self.signal(text=f'convert wav')
        all_task = []

        with ThreadPoolExecutor(max_workers=min(4,len(self.queue_tts),os.cpu_count())) as pool:
            for item in self.queue_tts:
                filename=item.get('filename','')+"-24k.wav"
                if vail_file(filename):
                    all_task.append(pool.submit(self.convert_to_wav, filename,item['filename']))
            if len(all_task) > 0:
                _ = [i.result() for i in all_task]
            else:
                self.error="No dubbing audio generate, view logs"


