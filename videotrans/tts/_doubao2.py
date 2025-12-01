import base64
import datetime
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, ClassVar

import requests

from videotrans.configure import config
from videotrans.configure.config import logs
from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


import requests
import json
import base64
import os

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class Doubao2TTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.stop_next_all=False
        #self.dub_nums = 1
        # 语音合成模型2.0专属角色 
        self.model2=[
            "zh_female_vv_uranus_bigtts",
            "zh_male_dayi_saturn_bigtts",
            "zh_female_mizai_saturn_bigtts",
            "zh_female_jitangnv_saturn_bigtts",
            "zh_female_meilinvyou_saturn_bigtts",
            "zh_female_santongyongns_saturn_bigtts",
            "zh_male_ruyayichen_saturn_bigtts",
            "saturn_zh_female_keainvsheng_tob",
            "saturn_zh_female_tiaopigongzhu_tob",
            "saturn_zh_male_shuanglangshaonian_tob",
            "saturn_zh_male_tiancaitongzhuo_tob",
            "saturn_zh_female_cancan_tob",
        ]

    def _exec(self):
        # 并发限制为1，防止限流
        self._local_mul_thread()
    

    def _save_pcm_to_wav(self,audio_data, output_filename: str, 
                        channels: int = 2, sample_rate: int = 48000, sample_width: int = 2):
        import wave
        import struct
        import math
        """
        将原始PCM数据（bytearray）保存为WAV文件。

        Args:
            audio_data (bytearray): 包含原始PCM音频数据的字节数组。
            output_filename (str): 要保存的WAV文件的路径和名称。
            channels (int): 声道数。默认为1（单声道）。
            sample_rate (int): 采样率（Hz）。默认为44100。
            sample_width (int): 采样宽度（字节）。默认为2（16-bit）。
                                 1 表示 8-bit, 2 表示 16-bit, 3 表示 24-bit。
        """
        if not output_filename.lower().endswith('.wav'):
            output_filename += '.wav'

        try:
            with wave.open(output_filename, 'wb') as wf:
                wf.setnchannels(channels)        # 设置声道数
                wf.setsampwidth(sample_width)    # 设置采样宽度 (2 bytes = 16 bits)
                wf.setframerate(sample_rate)     # 设置采样率

                wf.writeframes(audio_data)

        except Exception as e:
            logs(f"保存WAV文件时出错: {e}",'except')

    
    def _item_task(self, data_item: dict = None):
        if self.stop_next_all or self._exit() or not data_item.get('text','').strip():
            return

        if tools.vail_file(data_item['filename']):
            return
        appid = config.params.get('doubao2_appid','')
        access_token = config.params.get('doubao2_access','')
        speed = 1.0
        if self.rate:
            speed += float(self.rate.replace('%', '')) / 100
        speed=max(-50,min(100,100*(speed-1.0)))
        volume = 1.0
        if self.volume:
            volume += float(self.volume.replace('%', '')) / 100
        volume=max(-50,min(100,100*(volume-1.0)))

        # 角色为实际名字
        role = data_item['role']
        role=tools.get_doubao2_rolelist(role_name=role,langcode=self.language[:2])
        headers = {
            "X-Api-App-Id": appid,
            "X-Api-Access-Key": access_token,
            "X-Api-Resource-Id": 'seed-tts-2.0' if role in self.model2 else 'seed-tts-1.0',
            "Content-Type": "application/json",
            "Connection": "keep-alive"
        }

        payload = {
            "user": {
                "uid": "123123"
            },
            "req_params":{
                "text": data_item.get('text',''),
                "speaker": role,
                "model":"seed-tts-1.1",
                "audio_params": {
                    "format": "pcm",
                    "sample_rate": 48000,
                    "enable_timestamp": True,
                    "speech_rate":int(speed),
                    "loudness_rate":int(volume)
                },
                "additions": "{\"explicit_language\":\"crosslingual\",\"enable_language_detector\":\"true\",\"disable_markdown_filter\":true}\"}"
            }
        }
 
        url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
        
        session = requests.Session()
        response=None
        try:
            
            response = session.post(url, headers=headers, json=payload, stream=True)
            
            if response.status_code in [404,402,401,400]:
                self.stop_next_all=True
                raise RuntimeError('请检查 appid 和 access token 参数是否正确')
            if response.status_code == 403:
                self.stop_next_all=True
                raise RuntimeError('该角色正式版可能需要在字节后台单独开通购买')
            
            
            
            response.raise_for_status()
            logs(f"code: {response.status_code} header: {response.headers}")

            # 用于存储音频数据
            audio_data = bytearray()
            total_audio_size = 0
            for chunk in response.iter_lines(decode_unicode=True):
                if not chunk:
                    continue
                data = json.loads(chunk)

                if data.get("code", 0) == 0 and "data" in data and data["data"]:
                    chunk_audio = base64.b64decode(data["data"])
                    audio_size = len(chunk_audio)
                    total_audio_size += audio_size
                    audio_data.extend(chunk_audio)
                    continue
                if data.get("code", 0) == 0 and "sentence" in data and data["sentence"]:
                    print("sentence_data:", data)
                    continue
                if data.get("code", 0) == 20000000:
                    break
                if data.get("code", 0) > 0:
                    
                    raise RuntimeError(str(data))

            if audio_data:
                self._save_pcm_to_wav(audio_data,data_item['filename'])

        except Exception as e:
            logs(e,'except')
            raise
        finally:
            if response:
                response.close()
            session.close()


