import json,time,os
from dataclasses import dataclass
from typing import Union, Dict, List
from videotrans.tts._base import BaseTTS
from videotrans.configure.config import settings, logger,tr,ROOT_DIR,app_cfg,TEMP_DIR
from videotrans.util.help_misc import vail_file
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

@dataclass
class ConfuciusTTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()

            
    def _download(self):
        from videotrans.util import help_down
        self.local_dir=f"{ROOT_DIR}/models/models--netease-youdao--Confucius4-TTS"
        help_down.check_and_down_hf('', 'netease-youdao/Confucius4-TTS', local_dir=self.local_dir,callback=self._process_callback)
        self.local_dir=f"{ROOT_DIR}/models/models--facebook--w2v-bert-2.0"
        help_down.check_and_down_hf('', 'facebook/w2v-bert-2.0', local_dir=self.local_dir,callback=self._process_callback)
        self.local_dir=f"{ROOT_DIR}/models/models--nvidia--bigvgan_v2_22khz_80band_256x"
        help_down.check_and_down_hf('', 'nvidia/bigvgan_v2_22khz_80band_256x', local_dir=self.local_dir,callback=self._process_callback)
        self.local_dir=f"{ROOT_DIR}/models/models--funasr--campplus"
        help_down.check_and_down_hf('', 'funasr/campplus', local_dir=self.local_dir,callback=self._process_callback,allow_list=["campplus_cn_common.bin"])
        return True
        
    def _exec(self):
        logs_file = f'{TEMP_DIR}/{self.uuid}/confuciustts-{time.time()}.log'
        queue_tts_file = f'{TEMP_DIR}/{self.uuid}/confuciustts-{time.time()}.json'
        Path(queue_tts_file).write_text(json.dumps(self.queue_tts),encoding='utf-8')
        title="Confucius-TTS dubbing..."
        kwargs = {
            "queue_tts_file":queue_tts_file,
            "language": self.language.split('-')[0],
            "logs_file": logs_file,
            "is_cuda": self.is_cuda,
        }
        from videotrans.process.confucius_tts import confucius_fun
        self._new_process(callback=confucius_fun,title=title,is_cuda=self.is_cuda,kwargs=kwargs)

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



    def _exec0(self):
        ok, err = 0, 0
        _except = None
        
        import torchaudio
        from videotrans.confuciustts.cli.inference import ConfuciusTTS
        self.signal(text=f"Load Confucius-TTS model...")
        model = ConfuciusTTS(
            device=self.device,
        )
        lang=self.language.split('-')[0]
        for i,item in enumerate(self.queue_tts):
            if app_cfg.exit_soft: return
            try:
                self.signal(text=f"Dubbing {i+1}/{len(self.queue_tts)}")
                reference_audio_file,reference_text=self.get_ref_wav(item)
                if not Path(reference_audio_file).is_file():
                    raise ValueError(f"No reference audio_file in {ROOT_DIR}/f5-tts")
                output_filename=f'{item["filename"]}-24k.wav'

                audio = model.generate(item['text'],lang ,reference_audio_file, verbose=False)
                torchaudio.save(output_filename, audio.cpu(), model.sample_rate)
                if not vail_file(output_filename):
                    err += 1
                    continue
                ok += 1
                self.convert_to_wav(output_filename, item['filename'])
                self.signal(text=f"Dubbed {i+1}")
            except Exception as e:
                _except = e
                logger.exception(f'Confucius-TTS dubbing error:{e}', exc_info=True)
                err += 1

        try:
            del model
        except Exception:
            pass
        if ok == 0:
            raise _except if _except else DubbingSrtError('[Confucius-TTS] dubbing error')

        msg = "dubbing ended"
        if err > 0 and ok > 0:
            msg = f'[{err}] errors, {ok} succeed'


        self.signal(text=msg)
        logger.debug(f'Confucius-TTS 配音结束：{msg}')


    
    
    