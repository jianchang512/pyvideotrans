# -*- coding: utf-8 -*-
import re



import requests
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

@dataclass
class HuoShan(BaseTrans):
    prompt: str = field(init=False)
    def __post_init__(self):
        super().__post_init__()

        self.trans_thread = int(config.settings.get('aitrans_thread', 50))
        self.proxies = {"http": "", "https": ""}
        self.model_name = config.params["zijiehuoshan_model"]

        self.prompt = tools.get_prompt(ainame='zijie', is_srt=self.is_srt).replace('{lang}', self.target_language_name)

    def _item_task(self, data: Union[List[str], str]) -> str:
        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data
        message = [
            {'role': 'system',
             'content': "You are a top-notch subtitle translation engine." if config.defaulelang != 'zh' else '您是一名顶级的字幕翻译引擎。'},
            {'role': 'user',
             'content': self.prompt.replace('<INPUT></INPUT>',f'<INPUT>{text}</INPUT>')},
        ]
        config.logger.info(f"\n[字节火山引擎]发送请求数据:{message=}\n接入点名称:{config.params['zijiehuoshan_model']}")

        try:
            req = {
                "model": config.params['zijiehuoshan_model'],
                "messages": message
            }
            resp = requests.post("https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                                 proxies=self.proxies, json=req, headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {config.params['zijiehuoshan_key']}"
                })
            if resp.status_code!=200:
                raise Exception(f'字节火山引擎请求失败: status_code={resp.status_code} {resp.reason}')
            config.logger.info(f'[字节火山引擎]响应:{resp.text=}')
            data = resp.json()
            if 'choices' not in data or len(data['choices']) < 1:
                raise Exception(f'字节火山翻译失败:{resp.text=}')
            result = data['choices'][0]['message']['content'].strip()
            match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', result,re.S)
            if match:
                return match.group(1)
            return result.strip()
        except Exception as e:
            raise Exception(f'字节火山翻译失败:{e}')


