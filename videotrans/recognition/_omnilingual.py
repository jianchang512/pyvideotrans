from dataclasses import dataclass
from pathlib import Path
from typing import List, Union
import time
from videotrans.configure.config import params, logger, settings,ROOT_DIR
from videotrans.configure.excepts import SpeechToTextError, StopTask
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem
import sherpa_onnx
import soundfile as sf

# https://k2-fsa.github.io/sherpa/onnx/Dolphin/index.html
# 1B int8
@dataclass
class OmnilingualRecogn(BaseRecogn):
    def __post_init__(self):
        super().__post_init__()
        self.local_dir=f"{ROOT_DIR}/models/omnilingual"

    def _create_recognizer(self):
        model = f"{self.local_dir}/model.int8.onnx"
        tokens = f"{self.local_dir}/tokens.txt"

        return  sherpa_onnx.OfflineRecognizer.from_omnilingual_asr_ctc(
                model=model,
                tokens=tokens,
                debug=False,
                num_threads=int(settings.get('noise_separate_nums', 4))
            )
            
    def _download(self):
        if not Path(f'{self.local_dir}/model.int8.onnx').exists():
            from videotrans.util import help_down
            help_down.down_zip(f"{ROOT_DIR}/models",
                           'https://modelscope.cn/models/himyworld/videotrans/resolve/master/omnilingual.zip',
                           self._process_callback)
        return True
        
    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return
        # 发送请求
        raws = self.cut_audio()
        err=''
        ok_nums=0
        recognizer = self._create_recognizer()
        for i, it in enumerate(raws):
            try:
                audio, sample_rate = sf.read(it['filename'], dtype="float32", always_2d=True)
                audio = audio[:, 0]
                stream = recognizer.create_stream()
                stream.accept_waveform(sample_rate, audio)
                recognizer.decode_stream(stream)
                text=stream.result.text
                it['text']=text
                self.signal(text=f"{i+1}/{len(raws)}")
                self.signal(text=f'{text}\n',type='subtitle')
                ok_nums+=1
            except Exception as e:
                logger.exception(f'{e}:{it=}',exc_info=True)
                err=e

        if ok_nums<1:
            raise SpeechToTextError(err)
        return raws