# -*- coding: utf-8 -*-
import deepl

from ..configure import config
deepltranslator=None

def deepltrans(text,to_lang):
    global deepltranslator
    if deepltranslator is None:
        deepltranslator = deepl.Translator(config.video['deepl_authkey'])
    return deepltranslator.translate_text(text, target_lang=to_lang).text.strip()

