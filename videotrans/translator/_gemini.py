# -*- coding: utf-8 -*-

import re
import socket
from typing import Union, List
import requests
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core.exceptions import ServerError,TooManyRequests,RetryError
from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

safetySettings = [
    {
        "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        "threshold": HarmBlockThreshold.BLOCK_NONE,
    },
]


# 代理修改  site-packages\google\ai\generativelanguage_v1beta\services\generative_service\transports\grpc_asyncio.py __init__方法的 options 添加 ("grpc.http_proxy",os.environ.get('http_proxy') or os.environ.get('https_proxy'))
class Gemini(BaseTrans):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trans_thread=int(config.settings.get('aitrans_thread',500))
        self._set_proxy(type='set')
        self.prompt = tools.get_prompt(ainame='gemini',is_srt=self.is_srt).replace('{lang}', self.target_language_name)
        self.model_name=config.params["gemini_model"]

        self.api_keys=config.params.get('gemini_key','').strip().split(',')
        
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self.refine3:
            return self._item_task_refine3(data)
        response = None
        try:
            message = self.prompt.replace('[TEXT]',"\n".join([i.strip() for i in data]) if isinstance(data, list) else data)
            api_key=self.api_keys.pop(0)
            self.api_keys.append(api_key)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(config.params['gemini_model'], safety_settings=safetySettings)
            response = model.generate_content(
                message,
                safety_settings=safetySettings
            )
            config.logger.info(f'[Gemini]请求发送:{message=}')

            result = response.text      
            config.logger.info(f'[Gemini]返回:{result=}')
            if not result:
                raise Exception("result is empty")
            match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', response.text,re.S)
            if match:
                return match.group(1)
            raise Exception('未获取到翻译结果，请尝试使用更智能的大模型或取消"发送完整字幕"选项' if config.defaulelang=='zh' else 'Translation not available, try using a smarter big model or uncheck the “Send full subtitles” option.')
        except TooManyRequests as e:
            raise Exception('429超过请求次数，请尝试更换其他Gemini模型后重试' if config.defaulelang=='zh' else 'Too many requests, use other model retry')
        except (ServerError,RetryError,socket.timeout) as e:
            error=str(e) if config.defaulelang !='zh' else '无法连接到Gemini,请尝试使用或更换代理或切换模型'
            raise requests.ConnectionError(error)
        except Exception as e:
            error = str(e)
            config.logger.error(f'[Gemini]请求失败:{error=}')
            if response and response.prompt_feedback.block_reason:
                raise Exception(self._get_error(response.prompt_feedback.block_reason, "forbid"))

            if error.find('User location is not supported') > -1 or error.find('time out') > -1:
                raise Exception("当前请求ip(或代理服务器)所在国家不在Gemini API允许范围")

            if response and len(response.candidates) > 0 and response.candidates[0].finish_reason not in [0, 1]:
                raise Exception(self._get_error(response.candidates[0].finish_reason))

            if response and len(response.candidates) > 0 and response.candidates[0].finish_reason == 1 and \
                    response.candidates[0].content and response.candidates[0].content.parts:
                result = response.text.replace('##', '').strip().replace('&#39;', '"').replace('&quot;', "'")
                return re.sub(r'\n{2,}', "\n", result)
            raise

    def _get_error(self, num=5, type='error'):
        REASON_CN = {
            2: "超出长度",
            3: "安全限制",
            4: "文字过度重复",
            5: "其他原因"
        }
        REASON_EN = {
            2: "The maximum number of tokens as specified",
            3: "The candidate content was flagged for safety",
            4: "The candidate content was flagged",
            5: "Unknown reason"
        }
        forbid_cn = {
            1: "被Gemini禁止翻译:出于安全考虑，提示已被屏蔽",
            2: "被Gemini禁止翻译:由于未知原因，提示已被屏蔽"
        }
        forbid_en = {
            1: "Translation banned by Gemini:for security reasons, the prompt has been blocked",
            2: "Translation banned by Gemini:prompt has been blocked for unknown reasons"
        }
        if config.defaulelang == 'zh':
            return REASON_CN[num] if type == 'error' else forbid_cn[num]
        return REASON_EN[num] if type == 'error' else forbid_en[num]

    def _item_task_refine3(self, data: Union[List[str], str]) -> str:
        prompt=self._refine3_prompt()
        text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data
        prompt=prompt.replace('{lang}',self.target_language_name).replace('<INPUT></INPUT>',f'<INPUT>{text}</INPUT>')

        response = None
        try:
            api_key=self.api_keys.pop(0)
            self.api_keys.append(api_key)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(config.params['gemini_model'], safety_settings=safetySettings)
            response = model.generate_content(
                prompt,
                safety_settings=safetySettings
            )
            config.logger.info(f'[Gemini]请求发送:{prompt=}')

            config.logger.info(f'[Gemini]返回:{response.text=}')
            match = re.search(r'<step3_refined_translation>(.*?)</step3_refined_translation>', response.text,re.S)
            if match:
                return match.group(1)
            raise Exception("result is empty")
        except TooManyRequests as e:
            raise Exception('429超过请求次数，请尝试更换其他Gemini模型后重试' if config.defaulelang=='zh' else 'Too many requests, use other model retry')
        except (ServerError,RetryError,socket.timeout) as e:
            error=str(e) if config.defaulelang !='zh' else '无法连接到Gemini,请尝试使用或更换代理'
            raise requests.ConnectionError(error)
        except Exception as e:
            error = str(e)
            config.logger.error(f'[Gemini]请求失败:{error=}')
            if response and response.prompt_feedback.block_reason:
                raise Exception(self._get_error(response.prompt_feedback.block_reason, "forbid"))

            if error.find('User location is not supported') > -1 or error.find('time out') > -1:
                raise Exception("当前请求ip(或代理服务器)所在国家不在Gemini API允许范围")

            if response and len(response.candidates) > 0 and response.candidates[0].finish_reason not in [0, 1]:
                raise Exception(self._get_error(response.candidates[0].finish_reason))

            if response and len(response.candidates) > 0 and response.candidates[0].finish_reason == 1 and response.candidates[0].content and response.candidates[0].content.parts:
                match = re.search(r'<step3_refined_translation>(.*?)</step3_refined_translation>', response.text, re.S)
                if match:
                    return match.group(1)

            raise