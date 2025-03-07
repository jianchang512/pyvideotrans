# zh_recogn 识别
import socket
import time,os,re
from typing import Union, List, Dict

from pydub import AudioSegment
from pydub.silence import split_on_silence
from pathlib import Path

import requests

from videotrans.configure import config
from videotrans.util import tools
from videotrans.recognition._base import BaseRecogn
from videotrans.translator import LANGNAME_DICT
import google
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core.exceptions import ServerError, TooManyRequests, RetryError, DeadlineExceeded, GatewayTimeout

safetySettings = {
    'HATE': 'BLOCK_NONE',
    'HARASSMENT': 'BLOCK_NONE',
    'SEXUAL' : 'BLOCK_NONE',
    'DANGEROUS' : 'BLOCK_NONE'
}


class GeminiRecogn(BaseRecogn):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raws = []
        pro = self._set_proxy(type='set')
        self.target_code=kwargs.get('target_code',None)
        if self.target_code:
            self.target_code=LANGNAME_DICT.get(self.target_code)
        self.api_keys=config.params.get('gemini_key','').strip().split(',')

 
 
    def _exec(self):
        seg_list=self.cut_audio()
        nums=10
        seg_list=[seg_list[i:i + nums] for i in  range(0, len(seg_list), nums)]
        if len(seg_list)<1:
            raise Exception(f'VAD error')
        srt_str_list=[]
        generation_config = {
                  "temperature": 1,
                  "top_p": 0.95,
                  "top_k": 40,
                  "response_mime_type": "text/plain",
                  "max_output_tokens": 8192
        }
        prompt= config.params['gemini_srtprompt']

        for seg_group in seg_list:
            api_key=self.api_keys.pop(0)
            self.api_keys.append(api_key)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
              model_name='gemini-2.0-flash',
              generation_config=generation_config,
              safety_settings=safetySettings,
            )
            retry=0          


            try:
                response=None
                files=[]
                for f in seg_group:
                    files.append(
                        {
                            "mime_type": "audio/wav",
                            "data": Path(f['file']).read_bytes()
                        }
                    )
                
                chat_session = model.start_chat(
                    history=[
                        {
                            "role": "user",
                            "parts": files,
                        }
                    ]
                )
                config.logger.info(f'发送音频到Gemini:prompt={prompt},{seg_group=}')
                response = chat_session.send_message(prompt,request_options={"timeout":600})
                config.logger.info(f'gemini返回结果:{response.text=}')
                m=re.findall(r'<audio_text>(.*?)<\/audio_text>',response.text.strip(),re.I)
                if len(m)<1:
                    continue
                str_s=[]
                for i,f in enumerate(seg_group):
                    if i < len(m):
                        startraw=tools.ms_to_time_string(ms=f['start_time'])
                        endraw=tools.ms_to_time_string(ms=f['end_time'])
                        srt={
                            "line":len(srt_str_list)+1,
                            "start_time":f['start_time'],
                            "end_time":f['end_time'],
                            "startraw":startraw,
                            "endraw":endraw,
                            "text":m[i]
                        }
                        srt_str_list.append(srt)
                        str_s.append(f'{srt["line"]}\n{startraw} --> {endraw}\n{srt["text"]}')
                self._signal(
                    text=('\n\n'.join(str_s))+"\n\n",
                    type='subtitle'
                )
            except TooManyRequests as e:               
                
                err=f'429 请求太快或超出Gemini每日限制 [{retry}]' if config.defaulelang=='zh' else f'429 Request too more or out of limit'
                raise Exception(err)
            
            except (RetryError,socket.timeout,ServerError) as e:
                error=str(e) if config.defaulelang !='zh' else '无法连接到Gemini,请尝试使用或更换代理'
                raise requests.ConnectionError(error)
            except google.api_core.exceptions.PermissionDenied:
                raise Exception(f'您无权访问所请求的资源或模型' if config.defaulelang =='zh' else 'You donot have permission for the requested resource')
            except google.api_core.exceptions.ResourceExhausted:                
                raise Exception(f'您的配额已用尽。请稍等片刻，然后重试,若仍如此，请查看Google账号 ' if config.defaulelang =='zh' else 'Your quota is exhausted. Please wait a bit and try again')
            except google.auth.exceptions.DefaultCredentialsError:                
                raise Exception(f'验证失败，可能 Gemini API Key 不正确 ' if config.defaulelang =='zh' else 'Authentication fails. Please double-check your API key and try again')
            except google.api_core.exceptions.InvalidArgument as e:                
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

        if len(srt_str_list)<1:
            raise Exception('No result')
        return srt_str_list
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
    
    
    # 根据 时间开始结束点，切割音频片段,并保存为wav到临时目录，记录每个wav的绝对路径到list，然后返回该list
    def cut_audio(self):
        
        sampling_rate=16000
        from faster_whisper.audio import decode_audio
        from faster_whisper.vad import (
            VadOptions,
            get_speech_timestamps
        )

        def convert_to_milliseconds(timestamps):
            milliseconds_timestamps = []
            for timestamp in timestamps:
                milliseconds_timestamps.append(
                    {
                        "start": int(round(timestamp["start"] / sampling_rate * 1000)),
                        "end": int(round(timestamp["end"] / sampling_rate * 1000)),
                    }
                )

            return milliseconds_timestamps
        vad_p={
            "threshold":float(config.settings['threshold']),
            "min_speech_duration_ms":int(config.settings['min_speech_duration_ms']),
            "max_speech_duration_s":float(config.settings['max_speech_duration_s']) if float(config.settings['max_speech_duration_s'])>0 else float('inf'),
            "min_silence_duration_ms":int(config.settings['min_silence_duration_ms']),
            "speech_pad_ms":int(config.settings['speech_pad_ms'])
        }
        speech_chunks=get_speech_timestamps(decode_audio(self.audio_file, sampling_rate=sampling_rate),vad_options=VadOptions(**vad_p))
        speech_chunks=convert_to_milliseconds(speech_chunks)
        
        # 在config.TEMP_DIR下创建一个以当前时间戳为名的文件夹，用于保存切割后的音频片段
        dir_name = f"{config.TEMP_DIR}/{time.time()}"
        Path(dir_name).mkdir(parents=True, exist_ok=True)
        print(f"Saving segments to {dir_name}")
        data=[]
        audio = AudioSegment.from_wav(self.audio_file)
        for it in speech_chunks:
            start_ms, end_ms=it['start'],it['end']
            chunk = audio[start_ms:end_ms]
            file_name=f"{dir_name}/{start_ms}_{end_ms}.wav"
            chunk.export(file_name, format="wav")
            data.append({"start_time":start_ms,"end_time":end_ms,"file":file_name})

        return data