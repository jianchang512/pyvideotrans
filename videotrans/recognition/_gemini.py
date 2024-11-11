# zh_recogn 识别
import socket
import time,os
from typing import Union, List, Dict

import requests

from videotrans.configure import config
from videotrans.util import tools
from videotrans.recognition._base import BaseRecogn
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core.exceptions import ServerError, TooManyRequests, RetryError, DeadlineExceeded, GatewayTimeout

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

class GeminiRecogn(BaseRecogn):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raws = []
        pro = self._set_proxy(type='set')
        genai.configure(api_key=config.params['gemini_key'])


 

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return
        pro = self._set_proxy(type='set')

        self._signal(
            text=f"识别可能较久，请耐心等待" if config.defaulelang == 'zh' else 'Recognition may take a while, please be patient')
        response = None
        # 尺寸大于190MB，转为 mp3
        mime='audio/wav'
        if os.path.getsize(self.audio_file) > 31457280:
            tools.runffmpeg(
                ['-y', '-i', self.audio_file, '-ac', '1', '-ar', '16000', self.cache_folder + '/gemini-tmp.mp3'])
            self.audio_file = self.cache_folder + '/gemini-tmp.mp3'
            mime='audio/mpeg'
        while 1:
            try:
                # Create the model
                generation_config = {
                  "temperature": 1,
                  "top_p": 0.95,
                  "top_k": 40,
                  "response_mime_type": "text/plain",
                }
                model = genai.GenerativeModel(
                  model_name=config.params['gemini_model'],
                  generation_config=generation_config,
                  safety_settings=safetySettings
                )
                files = [
                      genai.upload_file(self.audio_file, mime_type=mime),
                    ]
                chat_session = model.start_chat(
                    history=[
                        {
                            "role": "user",
                            "parts": [config.params['gemini_srtprompt']],
                        }
                    ]
                )
                config.logger.info(f'发送音频到Gemini:prompt={config.params["gemini_srtprompt"]},{self.audio_file=}')
                response = chat_session.send_message(files[0],request_options={"timeout":600})
            except TooManyRequests as e:
                self._signal(
                    text='429频率限制，暂停60s后重试' if config.defaulelang=='zh' else 'Too many requests, pause for 60s and retry',
                    type='replace_subtitle'
                )
                time.sleep(60)
                continue
            except ServerError as e:
                error=str(e) if config.defaulelang !='zh' else '连接Gemini服务超时，请尝试更换代理'
                raise requests.ConnectionError(error)
            except (RetryError,socket.timeout) as e:
                error=str(e) if config.defaulelang !='zh' else '无法连接到Gemini,请尝试使用或更换代理'
                raise requests.ConnectionError(error)
            except Exception as e:
                error = str(e)
                config.logger.exception(f'[Gemini]请求失败:{error=}', exc_info=True)
                if response and response.prompt_feedback.block_reason:
                    raise Exception(self._get_error(response.prompt_feedback.block_reason, "forbid"))

                if error.find('User location is not supported') > -1 or error.find('time out') > -1:
                    raise Exception("当前请求ip(或代理服务器)所在国家不在Gemini API允许范围")

                if response and len(response.candidates) > 0 and response.candidates[0].finish_reason not in [0, 1]:
                    raise Exception(self._get_error(response.candidates[0].finish_reason))
                raise
            else:
                raw=response.text.strip()
                self._signal(
                    text=raw,
                    type='replace_subtitle'
                )
                return  tools.get_subtitle_from_srt(response.text.strip(), is_file=False)
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