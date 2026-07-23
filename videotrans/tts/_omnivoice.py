from dataclasses import dataclass
from videotrans.configure.config import logger,ROOT_DIR,app_cfg,TEMP_DIR
from videotrans.util.help_misc import vail_file
from videotrans.tts._base import BaseTTS
from pathlib import Path
import json,time,os
from concurrent.futures import ThreadPoolExecutor

@dataclass
class OmniVoice(BaseTTS):

    def __post_init__(self):
        super().__post_init__()

    def _download(self):
        from videotrans.util import help_down
        help_down.check_and_down_hf(
                "OmniVoice",
                'k2-fsa/OmniVoice',
                f'{ROOT_DIR}/models/models--k2-fsa--OmniVoice',
                callback=self._process_callback,
        )        
        return True
        
    def _exec(self):
        logs_file = f'{TEMP_DIR}/{self.uuid}/omnivoice-{time.time()}.log'
        queue_tts_file = f'{TEMP_DIR}/{self.uuid}/omnivoice-{time.time()}.json'
        Path(queue_tts_file).write_text(json.dumps(self.queue_tts),encoding='utf-8')
        title="OmniVoice-TTS dubbing..."
        kwargs = {
            "queue_tts_file":queue_tts_file,
            "logs_file": logs_file,
            "is_cuda": self.is_cuda,
            "speed":self.get_speed()
        }
        from videotrans.process.omnivoice_tts import omnivoice_fun
        self._new_process(callback=omnivoice_fun,title=title,is_cuda=self.is_cuda,kwargs=kwargs)

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
