# -*- coding: utf-8 -*-
import deepl

from videotrans.configure import config
from videotrans.util  import tools
deepltranslator=None

def deepltrans(text,to_lang):
    global deepltranslator
    if deepltranslator is None:
        deepltranslator = deepl.Translator(config.video['deepl_authkey'])
    try:
        result=deepltranslator.translate_text(text, target_lang=to_lang)
        return result.text.strip()
    except Exception as e:
        res=f"[error]DeepL翻译出错:"+str(e)
        tools.set_process(res)
        return res