from pathlib import Path

import ctranslate2
import sentencepiece as spm
from dataclasses import dataclass
from typing import List, Union
from videotrans.configure.config import ROOT_DIR, logger, settings
from videotrans.configure.contants import M2M100_URL_MS, M2M100_URL_HF,_LANGUAGE_M2M100
from videotrans.translator._base import BaseTrans
import torch

# Adapted from:
# https://gist.github.com/ymoslem/a414a0ead0d3e50f4d7ff7110b1d1c0d
# https://github.com/ymoslem/DesktopTranslator
from videotrans.util.help_down import down_zip
from videotrans.util.help_misc import is_connect_hf

# Refer to https://github.com/ymoslem/DesktopTranslator/blob/main/utils/m2m_languages.json
# other languages can be added as well

@dataclass
class M2M100Trans(BaseTrans):

    def __post_init__(self):
        super().__post_init__()
        if not self.source_code or self.source_code=='auto':
            self.from_lang='auto'
        else:
            self.from_lang=_LANGUAGE_M2M100.get(self.source_code.split('-')[0].lower(),'auto')
        self.to_lang=_LANGUAGE_M2M100.get(self.target_code.split('-')[0].lower())

    def _download(self):
        if not Path(f'{ROOT_DIR}/models/m2m100_12b/model.bin').exists():
            down_zip(f"{ROOT_DIR}/models", M2M100_URL_MS if not is_connect_hf() else M2M100_URL_HF,self._process_callback)
        device=settings.get('device_name','auto')
        if device=='auto':
            device="cpu" if not torch.cuda.is_available() else "cuda"
        self.model = ctranslate2.Translator(
            model_path=f'{ROOT_DIR}/models/m2m100_12b',
            device=device
        )
        self.model.load_model()
        self.sentence_piece_processor = spm.SentencePieceProcessor(f'{ROOT_DIR}/models/m2m100_12b/sentencepiece.model')
        return True

    def _unload(self):
        try:
            self.model.unload_model()
            del self.model
            del self.sentence_piece_processor
        except Exception as e:
            logger.warning(f'm2m100 unload error: {e}')

    def _item_task(self, data: Union[List[str], str]):
        queries = data if isinstance(data, list) else [data]
    
        queries_tokenized = self.tokenize(queries, self.from_lang)
        translated_tokenized = self.model.translate_batch(
            source=queries_tokenized,
            target_prefix=[[self.to_lang]] * len(queries),
            beam_size=5,
            max_batch_size=2048,
            return_alternatives=False,
            disable_unk=True,
            replace_unknowns=True,
            repetition_penalty=3,
        )
        translated = self.detokenize(list(map(lambda t: t[0]['tokens'], translated_tokenized)), self.to_lang)
        return "\n".join([it.strip() for it in translated])

    def tokenize(self, queries, lang=None):
        sp = self.sentence_piece_processor
        if isinstance(queries, list):
            return sp.encode(queries, out_type=str)
        else:
            return [sp.encode(queries, out_type=str)]

    def detokenize(self, queries, lang):
        sp = self.sentence_piece_processor
        translation = sp.decode(queries)
        prefix_len = len(lang) + 1
        translation = [''.join(query)[prefix_len:] for query in translation]
        return translation


