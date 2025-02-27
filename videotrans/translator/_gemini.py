# -*- coding: utf-8 -*-

import re
import socket
from typing import Union, List
import requests
import google
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core.exceptions import ServerError,TooManyRequests,RetryError
from videotrans.configure import config
from videotrans.translator._base import BaseTrans
from videotrans.util import tools

safetySettings = {
    'HATE': 'BLOCK_NONE',
    'HARASSMENT': 'BLOCK_NONE',
    'SEXUAL' : 'BLOCK_NONE',
    'DANGEROUS' : 'BLOCK_NONE'
}


# 代理修改  site-packages\google\ai\generativelanguage_v1beta\services\generative_service\transports\grpc_asyncio.py __init__方法的 options 添加 ("grpc.http_proxy",os.environ.get('http_proxy') or os.environ.get('https_proxy'))
class Gemini(BaseTrans):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trans_thread=int(config.settings.get('aitrans_thread',50))
        self._set_proxy(type='set')
        self.prompt = tools.get_prompt(ainame='gemini',is_srt=self.is_srt).replace('{lang}', self.target_language_name)
        self.model_name=config.params["gemini_model"]

        self.api_keys=config.params.get('gemini_key','').strip().split(',')
        
    def _item_task(self, data: Union[List[str], str]) -> str:
        if self.refine3:
            return self._item_task_refine3(data)
        try:
            response = None
            text="\n".join([i.strip() for i in data]) if isinstance(data,list) else data
            message = self.prompt.replace('<INPUT></INPUT>',f'<INPUT>{text}</INPUT>')
            api_key=self.api_keys.pop(0)
            self.api_keys.append(api_key)
            config.logger.info(f'[Gemini]请求发送:{api_key=},{config.params["gemini_model"]=}')
            genai.configure(api_key=api_key)
            
            model = genai.GenerativeModel(model_name=config.params['gemini_model'],generation_config={"max_output_tokens": 8192},system_instruction="You are a translation assistant specializing in converting SRT subtitle content from one language to another while maintaining the original format and structure." if config.defaulelang != 'zh' else '您是一名翻译助理，专门负责将 SRT 字幕内容从一种语言转换为另一种语言，同时保持原始格式和结构。')
            response = model.generate_content(
                message,
                safety_settings=safetySettings
            )

            result = response.text      
            config.logger.info(f'[Gemini]返回:{result=}')
            if not result:
                raise Exception("result is empty")
            match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', response.text,re.S)
            if match:
                return match.group(1)
            return response.text.strip()
        except TooManyRequests as e:
            raise Exception('429超过请求次数，请尝试更换其他Gemini模型后重试' if config.defaulelang=='zh' else 'Too many requests, use other model retry')
        except (ServerError,RetryError,socket.timeout) as e:
            error=str(e) if config.defaulelang !='zh' else '无法连接到Gemini,请尝试使用或更换代理或切换模型'
            raise requests.ConnectionError(error)
        except google.api_core.exceptions.PermissionDenied:
            raise Exception('您无权访问所请求的资源或模型' if config.defaulelang =='zh' else 'You donot have permission for the requested resource')
        except google.api_core.exceptions.ResourceExhausted:                
            raise Exception(f'您的配额已用尽。请稍等片刻，然后重试,若仍如此，请查看Google账号 ' if config.defaulelang =='zh' else 'Your quota is exhausted. Please wait a bit and try again')
        except google.auth.exceptions.DefaultCredentialsError:                
            raise Exception(f'验证失败，可能 Gemini API Key 不正确 ' if config.defaulelang =='zh' else 'Authentication fails. Please double-check your API key and try again')
        except google.api_core.exceptions.InvalidArgument as e:
            config.logger.exception(e, exc_info=True)
            raise Exception(f'文件过大或 Gemini API Key 不正确 {e}' if config.defaulelang =='zh' else f'Invalid argument. One example is the file is too large and exceeds the payload size limit. Another is providing an invalid API key {e}')
        except google.api_core.exceptions.RetryError:            
            raise Exception('无法连接到Gemini，请尝试使用或更换代理' if config.defaulelang=='zh' else 'Can be caused when using a proxy that does not support gRPC.')
        except genai.types.BlockedPromptException as e:
            raise Exception(self._get_error(e.args[0].finish_reason))
        except genai.types.StopCandidateException as e:
            config.logger.exception(e, exc_info=True)
            if int(e.args[0].finish_reason>1):
                raise Exception(self._get_error(e.args[0].finish_reason))
        except Exception as e:
            error = str(e)
            config.logger.error(f'[Gemini]请求失败:{error=}')
            if error.find('User location is not supported') > -1:
                raise Exception("当前请求ip(或代理服务器)所在国家不在Gemini API允许范围")
            raise

    def _get_error(self, num=5, type='error'):
        REASON_CN = {
            2: "已达到请求中指定的最大令牌数量",
            3: "Gemini安全限制:候选响应内容被标记",
            4:"Gemini安全限制:候选响应内容因背诵原因被标记",
            5:"Gemini安全限制:原因不明",
            6:"Gemini安全限制:候选回应内容因使用不支持的语言而被标记",
            7:"Gemini安全限制:由于内容包含禁用术语，令牌生成停止",
            8:"Gemini安全限制:令牌生成因可能包含违禁内容而停止",
            9: "Gemini安全限制:令牌生成停止，因为内容可能包含敏感的个人身份信息",
            10: "模型生成的函数调用无效",
        }
        REASON_EN = {
            2: "The maximum number of tokens as specified in the request was reached",
            3: "The response candidate content was flagged for safety reasons",
            4: "The response candidate content was flagged  for recitation reasons",
            5: "Unknown reason",
            6:"The response candidate content was flagged for using an unsupported language",
            7:"Token generation stopped because the content contains forbidden terms",
            8:"Token generation stopped for potentially containing prohibited content",
            9:"Token generation stopped because the content potentially contains  Sensitive Personally Identifiable Information",
            10:"The function call generated by the model is invalid",
        }
        forbid_cn = {
            0: "Gemini安全限制::安全考虑",
            1: "Gemini安全限制::出于安全考虑，提示已被屏蔽",
            2: "Gemini安全限制:提示因未知原因被屏蔽了",
            3: "Gemini安全限制:提示因术语屏蔽名单中包含的字词而被屏蔽",
            4: "Gemini安全限制:系统屏蔽了此提示，因为其中包含禁止的内容。",
        }
        forbid_en = {
            0: "Prompt was blocked by gemini",
            1: "Prompt was blocked due to safety reasons",
            2: "Prompt was blocked due to unknown reasons",
            3:"Prompt was blocked due to the terms which are included from the terminology blocklist",
            4:"Prompt was blocked due to prohibited content."
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
            if not match:
                match = re.search(r'<TRANSLATE_TEXT>(.*?)</TRANSLATE_TEXT>', re.sub(r'<think>(.*?)</think>','',response.text,re.S|re.I), re.S|re.I)
            if match:
                return match.group(1)
            return response.text.strip()
        except TooManyRequests as e:
            raise Exception('429超过请求次数，请尝试更换其他Gemini模型后重试' if config.defaulelang=='zh' else 'Too many requests, use other model retry')
        except (ServerError,RetryError,socket.timeout) as e:
            error=str(e) if config.defaulelang !='zh' else '无法连接到Gemini,请尝试使用或更换代理'
            raise requests.ConnectionError(error)
        except google.api_core.exceptions.PermissionDenied:
            raise Exception('您无权访问所请求的资源或模型' if config.defaulelang =='zh' else 'You donot have permission for the requested resource')
        except google.api_core.exceptions.ResourceExhausted:                
            raise Exception(f'您的配额已用尽。请稍等片刻，然后重试,若仍如此，请查看Google账号 ' if config.defaulelang =='zh' else 'Your quota is exhausted. Please wait a bit and try again')
        except google.auth.exceptions.DefaultCredentialsError:                
            raise Exception(f'验证失败，可能 Gemini API Key 不正确 ' if config.defaulelang =='zh' else 'Authentication fails. Please double-check your API key and try again')
        except google.api_core.exceptions.InvalidArgument:                
            raise Exception(f'文件过大或 Gemini API Key 不正确 ' if config.defaulelang =='zh' else 'Invalid argument. One example is the file is too large and exceeds the payload size limit. Another is providing an invalid API key')
        except google.api_core.exceptions.RetryError:
            raise Exception('无法连接到Gemini，请尝试使用或更换代理' if config.defaulelang=='zh' else 'Can be caused when using a proxy that does not support gRPC.')
        except genai.types.BlockedPromptException as e:
            raise Exception(self._get_error(e.args[0].finish_reason))
        except genai.types.StopCandidateException as e:
            if int(e.args[0].finish_reason>1):
                raise Exception(self._get_error(e.args[0].finish_reason))
        
        except Exception as e:
            error = str(e)
            config.logger.error(f'[Gemini]请求失败:{error=}')
            if error.find('User location is not supported') > -1:
                raise Exception("当前请求ip(或代理服务器)所在国家不在Gemini API允许范围")
            raise