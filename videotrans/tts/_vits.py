import logging
import re,os
import time
from dataclasses import dataclass, field
from pathlib import Path

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
import sherpa_onnx
import soundfile as sf

_model_obj={}
#用于多进程
def _t(role,device='cpu'):
    sid=0
    tts_config=None
    if role=='en_female':# matcha english
        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
               matcha=sherpa_onnx.OfflineTtsMatchaModelConfig(
                    acoustic_model=f'{config.ROOT_DIR}/models/vits/{role}/model.onnx' ,
                    vocoder=f'{config.ROOT_DIR}/models/vits/{role}/vocos-22khz-univ.onnx',
                    tokens=f'{config.ROOT_DIR}/models/vits/{role}/tokens.txt',
                    data_dir=f'{config.ROOT_DIR}/models/vits/{role}/espeak-ng-data',
                ),
                provider=device,
                debug=False,
                num_threads=2,
            ),
            rule_fsts="",
            max_num_sentences=1,
        )
    elif role=='zh_female': # matcha chinese
        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
               matcha=sherpa_onnx.OfflineTtsMatchaModelConfig(
                    acoustic_model=f'{config.ROOT_DIR}/models/vits/{role}/model.onnx',
                    vocoder=f'{config.ROOT_DIR}/models/vits/{role}/vocos-22khz-univ.onnx',
                    lexicon=f'{config.ROOT_DIR}/models/vits/{role}/lexicon.txt',
                    tokens=f'{config.ROOT_DIR}/models/vits/{role}/tokens.txt',
                ),
                provider=device,
                debug=False,
                num_threads=2,
            ),
            rule_fsts=f"{config.ROOT_DIR}/models/vits/{role}/date.fst,{config.ROOT_DIR}/models/vits/{role}/number.fst,{config.ROOT_DIR}/models/vits/{role}/phone.fst",
            max_num_sentences=1,
        )
    elif role=='zh_en':#zh+en vits
        sid=0
        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                   vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                        model= f'{config.ROOT_DIR}/models/vits/{role}/model.onnx',
                        tokens=f'{config.ROOT_DIR}/models/vits/{role}/tokens.txt',
                        lexicon=f'{config.ROOT_DIR}/models/vits/{role}/lexicon.txt',
                    ),
                    provider=device,
                    debug=False,
                    num_threads=2,
                ),
            rule_fsts=f"{config.ROOT_DIR}/models/vits/{role}/date.fst,{config.ROOT_DIR}/models/vits/{role}/number.fst,{config.ROOT_DIR}/models/vits/{role}/phone.fst,{config.ROOT_DIR}/models/vits/{role}/new_heteronym.fst",
            max_num_sentences=1,
        )
    elif role.startswith('en_'):#en vits 109 speakers
        sid=int(role.split('_')[-1])
        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
               vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model= f'{config.ROOT_DIR}/models/vits/en_vctk/model.onnx',
                    tokens=f'{config.ROOT_DIR}/models/vits/en_vctk/tokens.txt',
                    lexicon=f'{config.ROOT_DIR}/models/vits/en_vctk/lexicon.txt',
                ),
                provider=device,
                debug=False,
                num_threads=2,
            ),
            rule_fsts="",
            max_num_sentences=1,
        )

    elif role.startswith('zh_'):#zh vits   174 speakers
        sid=int(role.split('_')[-1])        
        tts_config = sherpa_onnx.OfflineTtsConfig(
                model=sherpa_onnx.OfflineTtsModelConfig(
                   vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                        model= f'{config.ROOT_DIR}/models/vits/zh_aishell/model.onnx',
                        tokens=f'{config.ROOT_DIR}/models/vits/zh_aishell/tokens.txt',
                        lexicon=f'{config.ROOT_DIR}/models/vits/zh_aishell/lexicon.txt',
                    ),
                    provider=device,
                    debug=False,
                    num_threads=2,
                ),
                rule_fsts=f"{config.ROOT_DIR}/models/vits/zh_aishell/date.fst,{config.ROOT_DIR}/models/vits/zh_aishell/number.fst,{config.ROOT_DIR}/models/vits/zh_aishell/phone.fst,{config.ROOT_DIR}/models/vits/zh_aishell/new_heteronym.fst",
                max_num_sentences=1,
            )
    if not tts_config or not tts_config.validate():
        raise ValueError("Please check your config")

    tts = sherpa_onnx.OfflineTts(tts_config)
    return tts,sid





@dataclass
class VitsCNEN(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.rate=1+float(self.rate.replace('%',''))/100
        self.device="cpu" #todo cuda


    def _download(self):
        if not Path(f'{config.ROOT_DIR}/models/vits/zh_en/model.onnx').exists():
            tools.down_zip(f"{config.ROOT_DIR}/models",'https://modelscope.cn/models/himyworld/videotrans/resolve/master/vits-tts.zip',self._process_callback)
        return True

    def _process_callback(self,msg):
        self._signal(text=msg)

    def _exec(self):
        _model_obj={}
        ok, err = 0, 0
        for item in self.queue_tts:
            if config.exit_soft:return
            try:
                _key=f'{item["role"]}-{self.device}'
                if _key in _model_obj:
                    _tts,sid=_model_obj.get(_key)
                else:
                    _tts,sid=_t(item['role'],self.device)
                    _model_obj[_key]=(_tts,sid)

                audio = _tts.generate(item['text'], sid=sid, speed=float(self.rate))
                if len(audio.samples) == 0:
                    config.logger.error("Error in generating audios. Please read previous error messages.")
                    err+=1
                    continue
                sf.write(
                    item['filename']+"-24k.wav",
                    audio.samples,
                    samplerate=audio.sample_rate,
                    subtype="PCM_16",
                )
                if not tools.vail_file(item['filename']+'-24k.wav'):
                    err+=1
                    continue
                ok+=1
                self.convert_to_wav(item['filename']+'-24k.wav',item['filename'])
            except Exception as e:
                config.logger.exception(f'vits dubbing error:{e}',exc_info=True)
                err+=1

        if err > 0:
            msg=f'[{err}] errors, {ok} succeed'
            self._signal(text=msg)
            config.logger.debug(f'vits配音结束：{msg}')

        try:
            del _model_obj
            import gc
            gc.collect()
        except:
            pass
