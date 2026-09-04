import logging
import re
from dataclasses import dataclass
from typing import List, Union
import dashscope
import httpx
from tenacity import retry, retry_if_not_exception_type, wait_fixed, stop_after_attempt, before_log, after_log
from videotrans.configure.excepts import TranslateSrtError, NO_RETRY_EXCEPT
from videotrans.configure.config import params, logger, settings,ROOT_DIR
from videotrans.translator._base import BaseTrans
from videotrans.util.help_misc import qwenmt_glossary, get_prompt
from pathlib import Path
import os
from openai import OpenAI, APIError


@dataclass
class QwenMT(BaseTrans):
    lang_prompt:str=''
    def __post_init__(self):
        super().__post_init__()
        spaceid=params.get('qwenmt_spaceid', '')
        self.lang_prompt=''
        lang_prompt_file=f'{ROOT_DIR}/videotrans/prompts/language_prompts/{self.target_language_name}.txt'
        if Path(lang_prompt_file).exists():
            self.lang_prompt=Path(lang_prompt_file).read_text(encoding='utf-8')

        if spaceid and  not spaceid.startswith('http'):
            self.api_url = f'https://{spaceid}.cn-beijing.maas.aliyuncs.com/api/v1'
        elif spaceid and spaceid.startswith('http'):
            self.api_url = spaceid.strip().strip('/')
        dashscope.base_http_api_url = self.api_url
    

    def _item_task(self, data: Union[List[str], str]) -> str:
        if self._exit(): return
        text = "\n".join([i.strip() for i in data]) if isinstance(data, list) else data
        model_name=params.get('qwenmt_model', 'qwen-mt-turbo')
        if model_name=='qwen-turbo':
            model_name='qwen-mt-turbo'
        if not model_name.startswith('qwen-mt'):
            return self._openai(model_name, text)
        messages = [
            {
                "role": "user",
                "content":text
            }
        ]
        logger.debug(f'qwen-mt请求:{model_name=}')

        translation_options = {
            "source_lang": "auto" if not self.source_code else self.source_code.split('-')[0],
            "target_lang": self.target_code.split('-')[0]#self.target_language_name
        }
        # 术语表
        term=qwenmt_glossary()
        if term:
            translation_options['terms']=term
        if params.get("qwenmt_domains"):
            translation_options['domains']=params.get("qwenmt_domains")


        response = dashscope.Generation.call(
            # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx",
            api_key=params.get('qwenmt_key',''),
            model=model_name,
            messages=messages,
            result_format='message',
            translation_options=translation_options
        )
        if response.code or not response.output:
            raise TranslateSrtError(response.message)
        if not response.output.choices:
            raise TranslateSrtError(f'qwen-mt returned empty choices')
        logger.debug(f'qwen-mt返回响应:{response.output.choices[0].message.content}')
        return response.output.choices[0].message.content

    def _openai(self,model_name,text):
        if self.api_url.endswith('/api/v1'):
            self.api_url=self.api_url.replace('/api/v1','/compatible-mode/v1')
        elif not self.api_url.endswith('/v1'):
            self.api_url=self.api_url+'/compatible-mode/v1'

        self.prompt = get_prompt(ainame='bailian',aisendsrt=self.aisendsrt).replace('{lang}', self.target_language_name).replace('{lang_prompt}',self.lang_prompt)
        message = [
            {
                'role': 'system',
                'content':'You are a top-tier Subtitle Translation Engine.'},
            {
                'role': 'user',
                'content': self.prompt.replace('{batch_input}', f'{text}')
                },
        ]
        try:
            client = OpenAI(
                # 各地域的API Key不同。获取API Key：https://www.alibabacloud.com/help/zh/model-studio/get-api-key
                # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx",
                api_key=params.get('qwenmt_key',''),
                # 以下为新加坡地域URL，调用时请将{WorkspaceId}替换为真实的业务空间ID，各地域的URL不同。
                base_url=self.api_url,
                http_client=httpx.Client(proxy=None)
            )

            response = client.chat.completions.create(
                model=model_name,
                messages=message,
            )
            if not response or not response.choices or not response.choices[0] or not response.choices[0].message.content:
                raise TranslateSrtError(f'qwen-mt returned empty choices {response}')

            result = response.choices[0].message.content
            match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', result, re.S)
            if match:
                return match.group(1)
            return result
        except Exception as e:
            logger.exception(e,exc_info=True)
            raise

