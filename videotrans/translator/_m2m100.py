import os
from pathlib import Path

import ctranslate2
import sentencepiece as spm
from typing import List

import logging
from dataclasses import dataclass
from typing import List, Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.configure.config import ROOT_DIR
from videotrans.translator._base import BaseTrans
import torch

# Adapted from:
# https://gist.github.com/ymoslem/a414a0ead0d3e50f4d7ff7110b1d1c0d
# https://github.com/ymoslem/DesktopTranslator
from videotrans.util import tools

_LANGUAGE_CODE_MAP = {
        "en": "__en__",
        "zh": "__zh__",
        "fr": "__fr__",
        "de": "__de__",
        "ja": "__ja__",
        "ko": "__ko__",
        "ru": "__ru__",
        "es": "__es__",
        "th": "__th__",
        "it": "__it__",
        "pt": "__pt__",
        "vi": "__vi__",
        "ar": "__ar__",
        "tr": "__tr__",
        "hi": "__hi__",
        "hu": "__hu__",
        "uk": "__uk__",
        "id": "__id__",
        "ms": "__ms__",
        "kk": "__kk__",
        "cs": "__cs__",
        "pl": "__pl__",
        "nl": "__nl__",
        "sv": "__sv__",
        "he": "__he__",
        "bn": "__bn__",
        "fa": "__fa__",
        "fi": "__tl__",
        "ur": "__ur__",
        "yu": "__zh__"
}

# Refer to https://github.com/ymoslem/DesktopTranslator/blob/main/utils/m2m_languages.json
# other languages can be added as well

@dataclass
class M2M100Trans(BaseTrans):

    def __post_init__(self):
        super().__post_init__()
        self.aisendsrt = False
        if not self.source_code or self.source_code=='auto':
            self.from_lang='auto'
        else:
            self.from_lang=_LANGUAGE_CODE_MAP.get(self.source_code[:2].lower(),'auto')
        self.to_lang=_LANGUAGE_CODE_MAP.get(self.target_code[:2].lower())

    def _download(self):
        if not Path(f'{ROOT_DIR}/models/m2m100_12b/model.bin').exists():
            tools.down_zip(f"{ROOT_DIR}/models", 'https://modelscope.cn/models/himyworld/videotrans/resolve/master/m2m100_12b_model.zip',self._process_callback)
        self.model = ctranslate2.Translator(
            model_path=f'{ROOT_DIR}/models/m2m100_12b',
            device="cpu" if not torch.cuda.is_available() else "cuda",
            device_index=0,
        )
        self.model.load_model()
        self.sentence_piece_processor = spm.SentencePieceProcessor(model_file=f'{ROOT_DIR}/models/m2m100_12b/sentencepiece.model')
        return True

    def _process_callback(self,msg):
        self._signal(text=msg)

    def _unload(self):
        try:
            self.model.unload_model()
            del self.model
            del self.sentence_piece_processor
        except:
            pass

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
        print(f'{translated=}')
        return "\n".join([it.strip() for it in translated])

    def tokenize(self, queries, lang):
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


