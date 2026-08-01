import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Union, Dict, List

from videotrans.configure._paths import REDUBB_QUEUE_FILE, REDUBB_STATUS_FILE
from videotrans.configure.config import ROOT_DIR, logger, app_cfg
from videotrans.configure.excepts import DubbingSrtError
from videotrans.tts._base import BaseTTS
import soundfile as sf

from videotrans.util.help_misc import vail_file, is_connect_hf
from videotrans.util.helper_supertonic import load_text_to_speech, load_voice_style


@dataclass
class SupertonicTTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        self.model_name='Supertone/supertonic-3'
        self.local_dir=f'{ROOT_DIR}/models/models--Supertone--supertonic-3'
        self.speed=self.get_speed()

    def _download(self):
        from videotrans.util.help_down import check_and_down_hf,check_and_down_ms
        if  Path(f'{self.local_dir}/onnx/vector_estimator.onnx').exists():
            return
        check_and_down_hf(self.model_name,self.model_name, self.local_dir,
                                callback=self._process_callback)


    def _exec(self):
        text_to_speech = load_text_to_speech(f"{self.local_dir}/onnx", False)
        ok, err = 0, 0
        _except = None
        queue_tts=self.queue_tts
        # 循环，用于轮询重新配音数据，非重新配音时，第一轮直接返回
        while 1:
            if self.is_redubb and Path(REDUBB_STATUS_FILE).exists():
                return True
            if self.is_redubb:
                try:
                    queue_tts=json.loads(Path(REDUBB_QUEUE_FILE).read_text(encoding='utf-8'))
                except (OSError,json.JSONDecodeError) as e:
                    logger.exception(f'supertonic-3: {e}',exc_info=True)
                    raise


            for i,item in enumerate(queue_tts):
                if app_cfg.exit_soft or (self.is_redubb and Path(REDUBB_STATUS_FILE).exists()):
                    return True
                try:
                    if vail_file(item['filename']):
                        ok+=1
                        continue
                    role=item.get('role','F1')
                    style = load_voice_style([f"{self.local_dir}/voice_styles/{role}.json"], verbose=False)
                    wav, duration = text_to_speech(
                                   item.get('text'), self.language[:2], style, 10, self.speed
                                )
                    w = wav[0, : int(text_to_speech.sample_rate * duration.item())]  # [T_trim]
                    filename=item['filename']+'-tmp.wav'
                    sf.write(filename, w, text_to_speech.sample_rate)
                    if not vail_file(filename):
                        err += 1
                        continue
                    ok += 1
                    self.convert_to_wav(filename, item['filename'])
                    self.signal(text=f"Dubbinged {i}/{self.len}")
                except Exception as e:
                    _except = e
                    logger.exception(f'supertonic-3 dubbing error:{e}', exc_info=True)
                    err += 1
            if self.is_redubb:
                time.sleep(0.5)
                continue
            break


        if ok == 0:
            raise _except if _except else DubbingSrtError('supertonic-3 dubbing error')

        msg = "dubbing ended"
        if err > 0 and ok > 0:
            msg = f'[{err}] errors, {ok} succeed'

        self.signal(text=msg)
        logger.debug(f'supertonic-3 配音结束：{msg}')


    def _run0(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        role=data_item.get('role','F1')
        text_to_speech = load_text_to_speech(f"{self.local_dir}/onnx", False)
        style = load_voice_style([f"{self.local_dir}/voice_styles/{role}.json"], verbose=False)
        wav, duration = text_to_speech(
                       data_item.get('text'), self.language[:2], style, 10, self.speed
                    )
        w = wav[0, : int(text_to_speech.sample_rate * duration.item())]  # [T_trim]
        sf.write(data_item['filename']+'-tmp.wav', w, text_to_speech.sample_rate)
        self.convert_to_wav(data_item['filename'] +'-tmp.wav', data_item['filename'])