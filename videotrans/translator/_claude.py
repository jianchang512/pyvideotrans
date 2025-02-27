# -*- coding: utf-8 -*-
import re
from typing import Union, List

import anthropic
import httpx
from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools


class Claude(BaseTrans):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trans_thread=int(config.settings.get('aitrans_thread',50))
        self.api_url = self._get_url(config.params['claude_api'])
        if not config.params['claude_key']:
            raise Exception('必须在翻译设置 - Claude API 填写 SK' if config.defaulelang=='zh' else 'please input your sk password')
        
        # 是srt则获取srt的提示词
        self.prompt = tools.get_prompt(ainame='claude',is_srt=self.is_srt).replace('{lang}', self.target_language_name)
        self._check_proxy()
        self.model_name=config.params["claude_model"]


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
        if self.refine3:
            return self._item_task_refine3(data)
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
                max_tokens=2000,
                temperature=0.2,
                system="您是一名翻译助理，专门负责将 SRT 字幕内容从一种语言转换为另一种语言，同时保持原始格式和结构。" if config.defaulelang == 'zh' else 'You are a translation assistant specializing in converting SRT subtitle content from one language to another while maintaining the original format and structure.',
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


    def _item_task_refine3(self, data: Union[List[str], str]) -> str:
        prompt=self._refine3_prompt()
        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data
        prompt=prompt.replace('{lang}',self.target_language_name).replace('<INPUT></INPUT>',f'<INPUT>{text}</INPUT>')

        message = [
            {
                'role': 'user',
                'content': [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]

        config.logger.info(f"\n[chatGPT]发送请求数据:{message=}")

        client = anthropic.Anthropic(
            base_url=self._get_url(),
            api_key=config.params['claude_key'],
            proxies=self.proxies
        )
        try:
            response = client.messages.create(
                model=config.params['claude_model'],
                max_tokens=2000,
                temperature=0.2,
                system= "You are a translation assistant specializing in converting SRT subtitle content from one language to another while maintaining the original format and structure." if config.defaulelang != 'zh' else '您是一名翻译助理，专门负责将 SRT 字幕内容从一种语言转换为另一种语言，同时保持原始格式和结构。',
                messages=message
            )
        except anthropic.APIConnectionError as e:
            print("The server could not be reached")
            config.logger.exception(e, exc_info=True)
            raise Exception("The server could not be reached" if config.defaulelang != 'zh' else '服务器无法访问,请尝试使用代理')
        except anthropic.RateLimitError as e:
            config.logger.exception(e, exc_info=True)
            self.error_code = 429
            raise Exception(
                "Too many requests, please try again later" if config.defaulelang != 'zh' else '429,请求次数过多,请稍后再试或调大翻译后暂停秒数')
        except anthropic.APIStatusError as e:
            config.logger.exception(e, exc_info=True)
            raise Exception(f"{e}" if config.defaulelang != 'zh' else f'{e}')

        config.logger.info(f'[claude ai]返回响应:{response=}')

        if response.content:
            result = response.content[0].text.strip()
        else:
            config.logger.error(f'[claude]请求失败:{response=}')
            raise Exception(f"no content:{response=}")

        match = re.search(r'<step3_refined_translation>(.*?)</step3_refined_translation>', result,re.S)
        if not match:
            match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', re.sub(r'<think>(.*?)</think>','',result,re.S|re.I), re.S|re.I)
        if match:
            return match.group(1)
        return result.strip()
