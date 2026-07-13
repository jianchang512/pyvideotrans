import logging
from dataclasses import dataclass
from typing import Union, Dict, List

from videotrans.tts._base import BaseTTS

from videotrans.configure.config import settings, logger,tr,ROOT_DIR,app_cfg
from videotrans.util import tools
from videotrans.configure.excepts import DubbingSrtError
from pathlib import Path

@dataclass
class ConfuciusTTS(BaseTTS):
    localdir:str=None
    def __post_init__(self):
        super().__post_init__()
        self.roledict = tools.get_f5tts_role()
        self.device='cuda' if self.is_cuda else 'cpu'
            
    def _download(self):
        from videotrans.util import help_down

        help_down.check_and_down_hf('', 'netease-youdao/Confucius4-TTS', local_dir=f"{ROOT_DIR}/models/models--netease-youdao--Confucius4-TTS")
        help_down.check_and_down_hf('', 'facebook/w2v-bert-2.0', local_dir=f"{ROOT_DIR}/models/models--facebook--w2v-bert-2.0")
        help_down.check_and_down_hf('', 'nvidia/bigvgan_v2_22khz_80band_256x', local_dir=f"{ROOT_DIR}/models/models--nvidia--bigvgan_v2_22khz_80band_256x")
        help_down.check_and_down_hf('', 'funasr/campplus', local_dir=f"{ROOT_DIR}/models/models--funasr--campplus",allow_list=["campplus_cn_common.bin"])
        return True

    def _exec(self):
        ok, err = 0, 0
        _except = None
        
        speed = self.get_speed()
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
                if not tools.vail_file(output_filename):
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


    
    
    