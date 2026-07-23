from dataclasses import dataclass,field
from typing import List, Dict, Union,Any
import sys,json,time,os
from videotrans.tts._base import BaseTTS
from videotrans.configure.config import ROOT_DIR, app_cfg, logger,tr,TEMP_DIR
from videotrans.configure.excepts import DubbingSrtError
from videotrans.util.help_misc import vail_file
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

@dataclass
class F5TTSBuilt(BaseTTS):
    def __post_init__(self):
        super().__post_init__()

    
    def _download(self):
        language = self.language.split('-')[0]
        cfg=json.loads(Path(f'{ROOT_DIR}/videotrans/voicejson/f5ttscfg.json').read_text(encoding='utf-8'))
        if language not in cfg or not Path(f'{ROOT_DIR}/videotrans/voicejson/f5ttscfg/{language}.yaml').is_file():
            raise DubbingSrtError(f"[F5-TTS]{tr('may not support')}{tr(language)}")
        cfg=cfg[language]
        
        from videotrans.util import help_down
        self.local_dir=f'{ROOT_DIR}/models/models--'+cfg['repid'].replace('/','--')
        help_down.check_and_down_hf(
                "",
                cfg['repid'],
                self.local_dir,
                callback=self._process_callback,
                allow_list=[cfg['model_name'],cfg['vocab_name']]
        )
        
        if not Path(f'{ROOT_DIR}/models/models--charactr--vocos-mel-24khz/pytorch_model.bin').is_file():
            try:
                help_down.check_and_down_hf("",
                'charactr/vocos-mel-24khz',
                f'{ROOT_DIR}/models/models--charactr--vocos-mel-24khz',
                callback=self._process_callback,
                allow_list=['pytorch_model.bin','config.yaml'])
            except Exception:
                self.local_dir=f'{ROOT_DIR}/models/models--charactr--vocos-mel-24khz'
                raise
        return True
        
    def _exec(self):
        logs_file = f'{TEMP_DIR}/{self.uuid}/f5tts-{time.time()}.log'
        queue_tts_file = f'{TEMP_DIR}/{self.uuid}/f5tts-{time.time()}.json'
        Path(queue_tts_file).write_text(json.dumps(self.queue_tts),encoding='utf-8')
        title="F5-TTS dubbing..."
        kwargs = {
            "queue_tts_file":queue_tts_file,
            "language": self.language.split('-')[0],
            "logs_file": logs_file,
            "is_cuda": self.is_cuda,
            "speed":self.get_speed(),
        }
        
        from videotrans.process.f5_tts import f5tts_fun
        self._new_process(callback=f5tts_fun,title=title,is_cuda=self.is_cuda,kwargs=kwargs)

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
