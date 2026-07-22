from dataclasses import dataclass
from videotrans.configure.config import logger,ROOT_DIR,app_cfg,TEMP_DIR
from videotrans.util.help_misc import vail_file
from videotrans.tts._base import BaseTTS
from pathlib import Path
import json,time

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



    def _exec0(self):
        _model_obj = {}
        ok, err = 0, 0
        _except = None
        import torch
        from omnivoice import OmniVoice
        
        model = OmniVoice.from_pretrained(
            self.local_dir,
            device_map=self.device,
            dtype=torch.float32 if self.device == 'cpu' else torch.float16
        )
        speed = self.get_speed()
        
        for i,item in enumerate(self.queue_tts):
            if app_cfg.exit_soft: return
            self.signal(text=f"Dubbing {i+1}/{len(self.queue_tts)}")
            try:
                reference_audio_file,reference_text=self.get_ref_wav(item)
                if not Path(reference_audio_file).is_file():
                    raise ValueError(f"No reference audio_file in {ROOT_DIR}/f5-tts")
                output_filename=f'{item["filename"]}-24k.wav'

                wav = model.generate(
                    text=item['text'],
                    ref_audio=reference_audio_file,
                    ref_text=reference_text,
                    speed=speed
                )
                sf.write(output_filename, wav[0], 24000)
                if not vail_file(output_filename):
                    err += 1
                    continue
                ok += 1
                self.convert_to_wav(output_filename, item['filename'])
                self.signal(text=f"Dubbing {ok}")
            except Exception as e:
                _except = e
                logger.exception(f'OmniVoice dubbing error:{e}', exc_info=True)
                err += 1

        try:
            del model
        except Exception:
            pass
        if ok == 0:
            raise _except if _except else DubbingSrtError('[OmniVoice] dubbing error')

        msg = "dubbing ended"
        if err > 0 and ok > 0:
            msg = f'[{err}] errors, {ok} succeed'


        self.signal(text=msg)
        logger.debug(f'OmniVoice 配音结束：{msg}')
