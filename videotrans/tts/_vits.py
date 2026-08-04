import json
import time
from dataclasses import dataclass
from pathlib import Path

from videotrans.configure._i18n import tr
from videotrans.configure._paths import REDUBB_STATUS_FILE, REDUBB_QUEUE_FILE
from videotrans.configure.contants import VITS_URL_MS, VITS_URL_HF
from videotrans.configure.excepts import DubbingSrtError
from videotrans.configure.config import ROOT_DIR, app_cfg, logger,settings
from videotrans.tts._base import BaseTTS
import sherpa_onnx
import soundfile as sf
from videotrans.util.help_misc import vail_file, is_connect_hf

# https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/vits.html#id25


_model_obj = {}


# 用于多进程
def _t(role, device='cpu'):
    sid = 0
    tts_config = None
    if role == 'en_female':  # matcha english
        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                matcha=sherpa_onnx.OfflineTtsMatchaModelConfig(
                    acoustic_model=f'{ROOT_DIR}/models/vits/{role}/model.onnx',
                    vocoder=f'{ROOT_DIR}/models/vits/{role}/vocos-22khz-univ.onnx',
                    tokens=f'{ROOT_DIR}/models/vits/{role}/tokens.txt',
                    data_dir=f'{ROOT_DIR}/models/vits/{role}/espeak-ng-data',
                ),
                provider=device,
                debug=False,
                num_threads=int(settings.get('noise_separate_nums', 4)),
            ),
            rule_fsts="",
            max_num_sentences=1,
        )
    elif role == 'zh_female':  # matcha chinese
        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                matcha=sherpa_onnx.OfflineTtsMatchaModelConfig(
                    acoustic_model=f'{ROOT_DIR}/models/vits/{role}/model.onnx',
                    vocoder=f'{ROOT_DIR}/models/vits/{role}/vocos-22khz-univ.onnx',
                    lexicon=f'{ROOT_DIR}/models/vits/{role}/lexicon.txt',
                    tokens=f'{ROOT_DIR}/models/vits/{role}/tokens.txt',
                ),
                provider=device,
                debug=False,
                num_threads=int(settings.get('noise_separate_nums', 4)),
            ),
            rule_fsts=f"{ROOT_DIR}/models/vits/{role}/date.fst,{ROOT_DIR}/models/vits/{role}/number.fst,{ROOT_DIR}/models/vits/{role}/phone.fst",
            max_num_sentences=1,
        )
    elif role == 'zh_en':  # zh+en vits
        sid = 0
        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=f'{ROOT_DIR}/models/vits/{role}/model.onnx',
                    tokens=f'{ROOT_DIR}/models/vits/{role}/tokens.txt',
                    lexicon=f'{ROOT_DIR}/models/vits/{role}/lexicon.txt',
                ),
                provider=device,
                debug=False,
                num_threads=int(settings.get('noise_separate_nums', 4)),
            ),
            rule_fsts=f"{ROOT_DIR}/models/vits/{role}/date.fst,{ROOT_DIR}/models/vits/{role}/number.fst,{ROOT_DIR}/models/vits/{role}/phone.fst,{ROOT_DIR}/models/vits/{role}/new_heteronym.fst",
            max_num_sentences=1,
        )
    elif role.startswith('en_'):  # en vits 109 speakers
        sid = int(role.split('_')[-1])
        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=f'{ROOT_DIR}/models/vits/en_vctk/model.onnx',
                    tokens=f'{ROOT_DIR}/models/vits/en_vctk/tokens.txt',
                    lexicon=f'{ROOT_DIR}/models/vits/en_vctk/lexicon.txt',
                ),
                provider=device,
                debug=False,
                num_threads=int(settings.get('noise_separate_nums', 4)),
            ),
            rule_fsts="",
            max_num_sentences=1,
        )

    elif role.startswith('zh_'):  # zh vits   174 speakers
        sid = int(role.split('_')[-1])
        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=f'{ROOT_DIR}/models/vits/zh_aishell/model.onnx',
                    tokens=f'{ROOT_DIR}/models/vits/zh_aishell/tokens.txt',
                    lexicon=f'{ROOT_DIR}/models/vits/zh_aishell/lexicon.txt',
                ),
                provider=device,
                debug=False,
                num_threads=int(settings.get('noise_separate_nums', 4)),
            ),
            rule_fsts=f"{ROOT_DIR}/models/vits/zh_aishell/date.fst,{ROOT_DIR}/models/vits/zh_aishell/number.fst,{ROOT_DIR}/models/vits/zh_aishell/phone.fst,{ROOT_DIR}/models/vits/zh_aishell/new_heteronym.fst",
            max_num_sentences=1,
        )
    if not tts_config or not tts_config.validate():
        raise ValueError("Please check your config")

    tts = sherpa_onnx.OfflineTts(tts_config)
    return tts, sid


@dataclass
class VitsCNEN(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.speed = self.get_speed()
        self.device = "cpu"  # todo cuda
        self.local_dir=f'{ROOT_DIR}/models/vits'

    def _download(self):
        if not Path(f'{self.local_dir}/zh_en/model.onnx').exists():
            from videotrans.util.help_down import down_zip
            down_zip(f"{ROOT_DIR}/models",
                           VITS_URL_MS  if not is_connect_hf() else VITS_URL_HF,
                           self._process_callback)
        return True

    def _exec(self):
        _model_obj = {}
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
                    return
                if vail_file(item['filename']):
                    ok+=1
                    continue
                try:
                    _key = f'{item["role"]}-{self.device}'
                    if _key in _model_obj:
                        _tts, sid = _model_obj.get(_key)
                    else:
                        _tts, sid = _t(item['role'], self.device)
                        _model_obj[_key] = (_tts, sid)

                    audio = _tts.generate(item['text'], sid=sid, speed=self.speed)
                    if len(audio.samples) == 0:
                        logger.error("Error in generating audios. Please read previous error messages.")
                        err += 1
                        continue
                    sf.write(
                        item['filename'] + "-24k.wav",
                        audio.samples,
                        samplerate=audio.sample_rate,
                        subtype="PCM_16",
                    )
                    if not vail_file(item['filename'] + '-24k.wav'):
                        err += 1
                        continue
                    ok += 1
                    self.convert_to_wav(item['filename'] + '-24k.wav', item['filename'])
                    self.signal(text=f"{tr('Dubbing')} {ok}")
                except Exception as e:
                    _except = e
                    logger.exception(f'vits dubbing error:{e}', exc_info=True)
                    err += 1

            if self.is_redubb:
                time.sleep(0.5)
                continue
            break

        if ok == 0:
            raise _except if _except else DubbingSrtError('vits dubbing error')

        msg = f"{tr('Dubbing')} ended"
        if err > 0 and ok > 0:
            msg = f'[{err}] errors, {ok} succeed'


        self.signal(text=msg)
        logger.debug(f'vits配音结束：{msg}')
