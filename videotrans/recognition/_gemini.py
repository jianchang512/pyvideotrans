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
        self.target_code=kwargs.get('target_code',None)
        if self.target_code:
            self.target_code=LANGNAME_DICT.get(self.target_code)


 

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return
        pro = self._set_proxy(type='set')

        self._signal(
            text=f"识别可能较久，请耐心等待" if config.defaulelang == 'zh' else 'Recognition may take a while, please be patient')
        if config.params.get('gemini_cut_audio'):
            return self._exec_by_segment()
        response = None
        # 尺寸大于190MB，转为 mp3
        mime='audio/wav'
        if os.path.getsize(self.audio_file) > 31457280:
            tools.runffmpeg(
                ['-y', '-i', self.audio_file, '-ac', '1', '-ar', '16000', self.cache_folder + '/gemini-tmp.mp3'])
            self.audio_file = self.cache_folder + '/gemini-tmp.mp3'
            mime='audio/mpeg'
        retry=0
        prompt= config.params['gemini_srtprompt']
        if self.target_code:
            if config.defaulelang=='zh':
                prompt=prompt.replace('</SOURCE_SRT>','</SOURCE_SRT>\n<TRANSLATE_SRT>{转录的SRT字幕内容翻译为'+self.target_code+'后的内容}</TRANSLATE_SRT>')
            else:
                prompt=prompt.replace('</SOURCE_SRT>','</SOURCE_SRT>\n<TRANSLATE_SRT>{Transcribed SRT subtitle content after translation into '+self.target_code+'}</TRANSLATE_SRT>')
        while 1:
            retry+=1
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
                  safety_settings=safetySettings
                )
                files = [
                      genai.upload_file(self.audio_file, mime_type=mime),
                    ]
                chat_session = model.start_chat(
                    history=[
                        {
                            "role": "user",
                            "parts": [prompt],
                        }
                    ]
                )
                config.logger.info(f'发送音频到Gemini:prompt={prompt},{self.audio_file=}')
                response = chat_session.send_message(files[0],request_options={"timeout":600})
            except TooManyRequests as e:
                if retry>2:
                    raise Exception('429超过请求次数，请尝试更换其他Gemini模型后重试' if config.defaulelang=='zh' else 'Too many requests, use other model retry')
                err=f'429 请求太快，暂停30s [{retry}]' if config.defaulelang=='zh' else f'429 Request too fast, pause for 30s [{retry}]'
                self._signal(text=err)
                time.sleep(30)
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
                source_srt=re.findall(r'<SOURCE_SRT>(.*?)</SOURCE_SRT>',raw,re.S|re.I)
                if len(source_srt)<1 or not source_srt[0].strip():
                    raise Exception('Gemini transcribe error')
                if not self.target_code:                    
                    return  tools.get_subtitle_from_srt(source_srt[0].strip(), is_file=False)

                target_srt=re.findall(r'<TRANSLATE_SRT>(.*?)</TRANSLATE_SRT>',raw,re.S|re.I)
                if len(target_srt)<1 or not target_srt[0].strip():
                    return  tools.get_subtitle_from_srt(source_srt[0].strip(), is_file=False)
                
                return  (tools.get_subtitle_from_srt(source_srt[0].strip(), is_file=False),tools.get_subtitle_from_srt(target_srt[0].strip(), is_file=False))


    def _exec_by_segment(self):
        seg_list=self.cut_audio()
        srt_str_list=[]
        generation_config = {
                  "temperature": 1,
                  "top_p": 0.95,
                  "top_k": 40,
                  "response_mime_type": "text/plain",
        }
        model = genai.GenerativeModel(
          model_name=config.params['gemini_model'],
          safety_settings=safetySettings
        )
        prompt=config.params.get('gemini_srtprompt_cut','Please transcribe the audio that was sent to you into text, then return the transcribed text without any explanations, hints, instructions or any other superfluous information attached to the returned text.')
        for f in seg_list:
            retry=0
            startraw=tools.ms_to_time_string(ms=f['start_time'])
            endraw=tools.ms_to_time_string(ms=f['end_time'])
            while 1:
                retry+=1                    
                try:
                    files = [
                          genai.upload_file(f['file'], mime_type='audio/wav'),
                    ]
                    chat_session = model.start_chat(
                        history=[
                            {
                                "role": "user",
                                "parts": [prompt],
                            }
                        ]
                    )
                    config.logger.info(f'发送音频到Gemini:prompt={prompt},{f["file"]=}')
                    response = chat_session.send_message(files[0],request_options={"timeout":600})
                except TooManyRequests as e:
                    if retry>=2:
                        srt_str_list.append({
                            "line":len(srt_str_list)+1,
                            "start_time":f['start_time'],
                            "end_time":f['end_time'],
                            "startraw":startraw,
                            "endraw":endraw,
                            "text":f'Error:{str(e)[:90]}'
                        })
                        break
                    err=f'429 请求太快，暂停30s [{retry}]' if config.defaulelang=='zh' else f'429 Request too fast, pause for 30s [{retry}]'
                    self._signal(text=err)
                    time.sleep(30)
                    continue
                
                except (RetryError,socket.timeout,ServerError) as e:
                    error=str(e) if config.defaulelang !='zh' else '无法连接到Gemini,请尝试使用或更换代理'
                    raise requests.ConnectionError(error)
                except Exception as e:
                    error = str(e)
                    config.logger.exception(f'[Gemini]请求失败:{error=}', exc_info=True)
                    if error.find('User location is not supported') > -1 or error.find('time out') > -1:
                        raise Exception("当前请求ip(或代理服务器)所在国家不在Gemini API允许范围")
                    srt_str_list.append({
                        "line":len(srt_str_list)+1,
                        "start_time":f['start_time'],
                        "end_time":f['end_time'],
                        "startraw":startraw,
                        "endraw":endraw,
                        "text":'Error:'+error[:90]
                    })
                    break
                else:
                    srt={
                        "line":len(srt_str_list)+1,
                        "start_time":f['start_time'],
                        "end_time":f['end_time'],
                        "startraw":startraw,
                        "endraw":endraw,
                        "text":response.text.strip()
                    }
                    srt_str_list.append(srt)
                    self._signal(
                        text=f'{srt["line"]}\n{startraw} --> {endraw}\n{srt["text"]}\n\n',
                        type='subtitle'
                    )
                    break
        return srt_str_list
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
            "threshold":  float(config.params.get('gemini_onset',0.5)),
            "neg_threshold": float(config.params.get('gemini_offset',0.35)),
            "min_speech_duration_ms":  0,
            "max_speech_duration_s":  float("inf"),
            "min_silence_duration_ms": int(config.params.get('gemini_min_silence_duration_ms',250)),
            "speech_pad_ms": int(config.params.get('gemini_speech_pad_ms',200))
        }
        speech_chunks=get_speech_timestamps(decode_audio(self.audio_file, sampling_rate=sampling_rate),vad_options=VadOptions(**vad_p))
        speech_chunks=convert_to_milliseconds(speech_chunks)
        
        print(speech_chunks)
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