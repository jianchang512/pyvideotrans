from dataclasses import dataclass
from pathlib import Path

from videotrans.configure.excepts import DubbingSrtError
from videotrans.configure.config import ROOT_DIR, app_cfg, logger
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
import sherpa_onnx
import soundfile as sf
import librosa,time

@dataclass
class ZipVoice(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.speed = self.get_speed()
        self.device = "cpu"  # todo cuda
        self.roledict = tools.get_f5tts_role()
        self.local_dir=f'{ROOT_DIR}/models/zipvoice'

    def _download(self):
        if not Path(f'{self.local_dir}/decoder.int8.onnx').exists():
            tools.down_zip(f"{ROOT_DIR}/models",
                           'https://modelscope.cn/models/himyworld/videotrans/resolve/master/zipvoice-tts.zip',
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
                num_threads=4,
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
        
        for item in self.queue_tts:
            if app_cfg.exit_soft: return
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

                if not tools.vail_file(output_filename):
                    err += 1
                    continue
                ok += 1
                self.convert_to_wav(output_filename, item['filename'])
                self.signal(text=f"Dubbing {ok}")
            except Exception as e:
                _except = e
                logger.exception(f'zipvoice dubbing error:{e}', exc_info=True)
                err += 1

        try:
            del tts
        except Exception:
            pass
        if ok == 0:
            raise _except if _except else DubbingSrtError('[zipvoice] dubbing error')

        msg = "dubbing ended"
        if err > 0 and ok > 0:
            msg = f'[{err}] errors, {ok} succeed'


        self.signal(text=msg)
        logger.debug(f'zipvoice 配音结束：{msg}')
