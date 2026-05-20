import logging
import time
from dataclasses import dataclass
from typing import Union, Dict, List

from tenacity import retry_if_not_exception_type, stop_after_attempt, wait_fixed, before_log, after_log, retry

from videotrans.configure.excepts import StopTask, NO_RETRY_EXCEPT
from videotrans.configure.config import logger, params, settings
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
import requests
import json
import base64


@dataclass
class Doubao2TTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        speed = 100 * (self.get_speed() - 1)
        self.speed = min(max(-50.0, speed), 100.0)

        volume = 100 * (self.get_volume() - 1)
        self.volume = min(max(-50.0, volume), 100.0)

        self.appid = params.get('doubao2_appid', '')
        self.access_token = params.get('doubao2_access', '')
    def _save_pcm_to_wav(self, audio_data, output_filename: str,
                         channels: int = 1, sample_rate: int = 48000, sample_width: int = 2):
        import wave
        if not output_filename.lower().endswith('.wav'):
            output_filename += '.wav'

        try:
            with wave.open(output_filename, 'wb') as wf:
                wf.setnchannels(channels)  # 设置声道数
                wf.setsampwidth(sample_width)  # 设置采样宽度 (2 bytes = 16 bits)
                wf.setframerate(sample_rate)  # 设置采样率

                wf.writeframes(audio_data)

        except Exception as e:
            logger.exception(f"保存WAV文件时出错: {e}", exc_info=True)

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        # 角色为实际名字
        role = data_item.get('role','Vivi 2.0')
        role = tools.get_doubao2_rolelist(role_name=role, langcode=self.language[:2])
        headers = {
            "X-Api-App-Id": self.appid,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": 'seed-tts-2.0',
            "Content-Type": "application/json",
            "Connection": "keep-alive"
        }

        payload = {
            "user": {
                "uid": f"{time.time()}"
            },
            "req_params": {
                "text": data_item.get('text', ''),
                "speaker": role,
                "model": "seed-tts-2.0-standard",
                "audio_params": {
                    "format": "pcm",
                    "sample_rate": 48000,
                    "enable_timestamp": True,
                    "speech_rate": int(self.speed),
                    "loudness_rate": int(self.volume)
                },
                "additions": "{\"explicit_language\":\"crosslingual\",\"enable_language_detector\":\"true\",\"disable_markdown_filter\":true}"
            }
        }

        url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"

        response = requests.post(url, headers=headers, json=payload, stream=True)

        if response.status_code in [404, 402, 401, 400]:
            raise StopTask('请检查 appid 和 access token 参数是否正确')
        if response.status_code == 403:
            raise StopTask('该角色正式版可能需要在字节后台单独开通购买')

        response.raise_for_status()
        logger.debug(f"code: {response.status_code} header: {response.headers}")

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
                continue
            if data.get("code", 0) == 20000000:
                break
            if data.get("code", 0) > 0:
                return str(data)

        if audio_data:
            self._save_pcm_to_wav(audio_data, data_item['filename'])
        else:
            return "No audio data"
