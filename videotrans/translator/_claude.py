# -*- coding: utf-8 -*-
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
import anthropic
import httpx
from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

@dataclass
class Claude(BaseTrans):
    prompt: str = field(init=False)


    # ==================================================================
    # 2. 将 __init__ 的所有逻辑移到 __post_init__ 方法中。
    # ==================================================================
    def __post_init__(self):
        super().__post_init__()

        # 覆盖父类属性
        self.trans_thread = int(config.settings.get('aitrans_thread', 50))
        self.api_url = self._get_url(config.params['claude_api'])
        self.model_name = config.params["claude_model"]


        self.prompt = tools.get_prompt(ainame='claude', is_srt=self.is_srt).replace('{lang}', self.target_language_name)


        self._check_proxy()


    def _check_proxy(self):
        if re.search('localhost', self.api_url) or re.match(r'^https?://(\d+\.){3}\d+(:\d+)?', self.api_url):
            return

        pro = self._set_proxy(type='set')
        if pro:
            self.proxies =  pro

    def _get_url(self, url=""):
        if not url:
            return "https://api.anthropic.com"
        if not url.startswith('http'):
            url = 'http://' + url
            # 删除末尾 /
        url = url.rstrip('/').lower()
        if url.endswith('/v1'):
            return url[:-3]

        return url

    def _item_task(self, data: Union[List[str], str]) -> str:
        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data
        message = [
            {
                'role': 'user',
                'content':[
                    {
                        "type":"text",
                        "text":self.prompt.replace('<INPUT></INPUT>',f'<INPUT>{text}</INPUT>')
                     }
                ]
            }
        ]

        config.logger.info(f"\n[chatGPT]发送请求数据:{message=}")

        client = anthropic.Anthropic(
            base_url=self._get_url(),
            api_key=config.params['claude_key'],
            http_client=httpx.Client(proxy=self.proxies)
        )
        try:
            response = client.messages.create(
                model=config.params['claude_model'],
                max_tokens=8096,
                system="You are a top-notch subtitle translation engine." if config.defaulelang != 'zh' else '您是一名顶级的字幕翻译引擎。',
                messages=message
            )
        except anthropic.APIConnectionError as e:
            print("The server could not be reached")
            config.logger.exception(e,exc_info=True)
            raise Exception("The server could not be reached" if config.defaulelang!='zh' else '服务器无法访问,请尝试使用代理')
        except anthropic.RateLimitError as e:
            config.logger.exception(e,exc_info=True)
            self.error_code=429
            raise Exception("Too many requests, please try again later" if config.defaulelang!='zh' else '429,请求次数过多,请稍后再试或调大翻译后暂停秒数')
        except anthropic.APIStatusError as e:
            config.logger.exception(e,exc_info=True)
            raise Exception(f"{e}" if config.defaulelang!='zh' else f'{e}')


        config.logger.info(f'[claude ai]返回响应:{response=}')
        result=''
        if response.content:
            result = response.content[0].text.strip()
        else:
            config.logger.error(f'[claude]请求失败:{response=}')
            raise Exception(f"no content:{response=}")
        
        match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', result,re.S)
        if match:
            return match.group(1)
        return result.strip()


