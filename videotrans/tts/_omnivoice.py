from dataclasses import dataclass
from videotrans.configure.config import logger,ROOT_DIR,app_cfg
from videotrans.configure.excepts import DubbingSrtError
from videotrans.util import tools,gpus
from videotrans.tts._base import BaseTTS
import soundfile as sf
from pathlib import Path

@dataclass
class OmniVoice(BaseTTS):
    localdir:str=None
    def __post_init__(self):
        super().__post_init__()
        # 语言代码 对应语言名称
        lang_code= {
            "zh-cn": "Chinese",
            "zh-tw": "Min Nan Chinese",
            "zh": "Chinese",
            "yue": "Cantonese",
            "en": "English",
            "fr": "French",
            "de": "German",
            "ja": "Japanese",
            "ko": "Korean",
            "ru": "Russian",
            "es": "Spanish",
            "th": "Thai",
            "it": "Italian",
            "pt": "Portuguese",
            "vi": "Vietnamese",
            "ar": "Standard Arabic",
            "tr": "Turkish",
            "hi": "Hindi",
            "hu": "Hungarian",
            "uk": "Ukrainian",
            "id": "Indonesian",
            "ms": "Malay",
            "kk": "Kazakh",
            "cs": "Czech",
            "pl": "Polish",
            "nl": "Dutch",
            "sv": "Swedish",
            "he": "Hebrew",
            "bn": "Bengali",
            "fil": "Filipino",

            "af": "Afrikaans",
            "sq": "Albanian",
            "am": "Amharic",
            "az": "Azerbaijani",
            "bs": "Bosnian",
            "bg": "Bulgarian",
            "my": "Burmese",
            "ca": "Catalan",
            "hr": "Croatian",
            "da": "Danish",
            "et": "Estonian",
            "fi": "Finnish",
            "gl": "Galician",
            "ka": "Georgian",
            "el": "Greek",
            "gu": "Gujarati",
            "is": "Icelandic",
            "iu": "Inuktitut",
            "ga": "Irish",
            "jv": "Javanese",
            "kn": "Kannada",
            "km": "Khmer",
            "lo": "Lao",
            "lv": "Latvian",
            "lt": "Lithuanian",
            "mk": "Macedonian",
            "ml": "Malayalam",
            "mt": "Maltese",
            "mr": "Marathi",
            "mn": "Mongolian",
            "ne": "Nepali",
            "nb": "Norwegian Bokmål",
            "ps": "Pashto",
            "fa": "Persian",

            "ro": "Romanian",
            "sr": "Serbian",
            "si": "Sinhala",
            "sk": "Slovak",
            "sl": "Slovenian",
            "so": "Somali",
            "su": "Sudanese Arabic",
            "sw": "Swahili",
            "ta": "Tamil",
            "te": "Telugu",
            "ur": "Urdu",
            "uz": "Uzbek",
            "cy": "Welsh",
            "zu": "Zulu"
        }
        self.roledict = tools.get_f5tts_role()
        self.device='cuda' if self.is_cuda else  gpus.mps_or_cpu()
        self.lang=lang_code.get(self.language,'Auto') if self.language else 'Auto'
        self.localdir=f'{ROOT_DIR}/models/models--k2-fsa--OmniVoice'

    def _download(self):
        tools.check_and_down_hf(
                "OmniVoice",
                'k2-fsa/OmniVoice',
                self.localdir,
                callback=self._process_callback,
                #allow_list=[self.cfg['model_name'],self.cfg['vocab_name']]
        )        
        return True

    def _exec(self):
        _model_obj = {}
        ok, err = 0, 0
        _except = None
        import torch
        from omnivoice import OmniVoice
        
        model = OmniVoice.from_pretrained(
            self.localdir,
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
                if not tools.vail_file(output_filename):
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
