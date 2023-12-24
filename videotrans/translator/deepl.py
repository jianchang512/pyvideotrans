# -*- coding: utf-8 -*-
import deepl

from videotrans.configure import config
from videotrans.util import tools

deepltranslator = None


def deepltrans(text, to_lang, *, set_p=True):
    global deepltranslator
    if deepltranslator is None:
        deepltranslator = deepl.Translator(config.params['deepl_authkey'])
    try:
        result = deepltranslator.translate_text(text, target_lang="ZH" if to_lang.startswith('zh') else to_lang)
        return result.text.strip()
    except Exception as e:
        res = f"[error]DeepL error:" + str(e)
        if set_p:
            tools.set_process(res)
        return res
