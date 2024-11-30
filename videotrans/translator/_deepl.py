# -*- coding: utf-8 -*-
import re
from typing import Union, List

import deepl
import requests

from videotrans.configure import config
from videotrans.translator._base import BaseTrans


class DeepL(BaseTrans):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_url = None if not config.params['deepl_api'] else config.params['deepl_api'].rstrip('/')
        self.aisendsrt=False

        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = {"https": pro, "http": pro}

    def _item_task(self, data: Union[List[str], str]) -> str:
        text=("\n".join(data)).strip()
        # text可能是中文 英文 日文 越南语等任何一种语言，也可能text全部由特殊符号组成，键盘上可以打出来的所有特殊符号，如果全是符号，则返回原text
        if not text or re.match(r'^[\s ~`!@#$%^&*()_+\-=\[\]{}\\|;,./?><:"\'，。、；‘’“”：《》？【】｛｝（）—！·￥…ー]+$', text):
            return text

        deepltranslator = deepl.Translator(config.params['deepl_authkey'], server_url=self.api_url, proxy=self.proxies)
        config.logger.info(f'[DeepL]请求数据:{text=},{config.params["deepl_gid"]=}')
        target_code=self.target_code.upper()
        if target_code=='EN':
            target_code='EN-US'
        elif target_code=='ZH-CN':
            target_code='ZH-HANS'
        elif target_code=='ZH-TW':
            target_code='ZH-HANT'
        sourcecode=self.source_code.upper()[:2] if self.source_code else None
        sourcecode=sourcecode if sourcecode!='AUTO' else None
        result = deepltranslator.translate_text(
                text,
                source_lang=sourcecode,
                target_lang=target_code,
                glossary=config.params['deepl_gid'] if config.params['deepl_gid'] else None
            )

        config.logger.info(f'[DeepL]返回:{result=}')
        return result.text
