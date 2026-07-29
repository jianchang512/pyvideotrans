import json
from dataclasses import dataclass
from pathlib import Path

from videotrans.configure._paths import REDUBB_STATUS_FILE, REDUBB_QUEUE_FILE
from videotrans.configure.contants import ZIPVOICE_URL_MS, ZIPVOICE_URL_HF
from videotrans.configure.excepts import DubbingSrtError
from videotrans.configure.config import ROOT_DIR, app_cfg, logger,settings
from videotrans.tts._base import BaseTTS
from videotrans.util.help_role import get_f5tts_role
import sherpa_onnx
import soundfile as sf
import librosa,time

from videotrans.util.help_misc import vail_file, is_connect_hf


@dataclass
class ZipVoice(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.speed = self.get_speed()
        self.device = "cpu"  # todo cuda
        self.roledict = get_f5tts_role()
        self.local_dir=f'{ROOT_DIR}/models/zipvoice'

    def _download(self):
        if not Path(f'{self.local_dir}/decoder.int8.onnx').exists():
            from videotrans.util.help_down import down_zip
            down_zip(f"{ROOT_DIR}/models",
                           ZIPVOICE_URL_MS if not is_connect_hf() else ZIPVOICE_URL_HF,
                           self._process_callback)
        return True

    
    def _create_tts(self):
        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                zipvoice=sherpa_onnx.OfflineTtsZipvoiceModelConfig(
                    tokens=f"{self.local_dir}/tokens.txt",
                    encoder=f"{self.local_dir}/encoder.int8.onnx",
                    decoder=f"{self.local_dir}/decoder.int8.onnx",
                    data_dir=f"{self.local_dir}/espeak-ng-data",
                    lexicon=f"{self.local_dir}/lexicon.txt",
                    vocoder=f"{self.local_dir}/vocos_24khz.onnx",
                ),
                debug=False,
                num_threads=int(settings.get('noise_separate_nums', 4)),
                provider=self.device,
            )
        )
        if not tts_config.validate():
            raise ValueError(
                "Please read the previous error messages and re-check your config"
            )

        return sherpa_onnx.OfflineTts(tts_config)

    def _exec(self):
        _model_obj = {}
        ok, err = 0, 0
        _except = None
        tts=self._create_tts()
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
                    reference_audio_file,reference_text=self.get_ref_wav(item)
                    if not Path(reference_audio_file).is_file():
                        raise ValueError(f"No Reference audio in {ROOT_DIR}/f5-tts")


                    reference_audio, sample_rate = librosa.load(reference_audio_file, sr=None)

                    gen_config = sherpa_onnx.GenerationConfig()
                    gen_config.reference_audio = reference_audio
                    gen_config.reference_sample_rate = sample_rate
                    gen_config.reference_text = reference_text
                    gen_config.num_steps = 4
                    gen_config.extra["min_char_in_sentence"] = "30"

                    audio = tts.generate(item['text'], gen_config)

                    if len(audio.samples) == 0:
                        logger.error(f"Error in generating audios. Please read previous error messages.{item}")
                        err+=1
                        continue

                    output_filename = item['filename'] + "-24k.wav"

                    sf.write(
                        output_filename,
                        audio.samples,
                        samplerate=audio.sample_rate,
                        subtype="PCM_16",
                    )

                    if not vail_file(output_filename):
                        err += 1
                        continue
                    ok += 1
                    self.convert_to_wav(output_filename, item['filename'])
                    self.signal(text=f"Dubbing {ok}")
                except Exception as e:
                    _except = e
                    logger.exception(f'zipvoice dubbing error:{e}', exc_info=True)
                    err += 1

            if self.is_redubb:
                time.sleep(0.5)
                continue
            break

        if ok == 0:
            raise _except if _except else DubbingSrtError('[zipvoice] dubbing error')

        msg = "dubbing ended"
        if err > 0 and ok > 0:
            msg = f'[{err}] errors, {ok} succeed'


        self.signal(text=msg)
        logger.debug(f'zipvoice 配音结束：{msg}')
