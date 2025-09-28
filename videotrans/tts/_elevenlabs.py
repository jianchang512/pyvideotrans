import json
import io
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Iterator

import httpx
from elevenlabs import ElevenLabs, VoiceSettings
from elevenlabs.core import ApiError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log, \
    RetryError

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class ElevenLabsC(BaseTTS):
    def __post_init__(self):
        super().__post_init__()

    def _item_task(self, data_item: dict = None):
        if self._exit() or not data_item.get('text','').strip():
            return
        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO))
        def _run():
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            role = data_item['role']

            speed = 1.0
            if self.rate and self.rate != '+0%':
                speed += float(self.rate.replace('%', ''))

            with open(config.ROOT_DIR+'/videotrans/voicejson/elevenlabs.json','r',encoding='utf-8') as f:
                jsondata=json.loads(f.read())

            client = ElevenLabs(
                api_key=config.params['elevenlabstts_key'],
                httpx_client=httpx.Client(proxy=self.proxy_str)
            )

            response = client.text_to_speech.convert(
                text=data_item['text'],
                voice_id=jsondata[role]['voice_id'],
                model_id=config.params.get("elevenlabstts_models"),

                output_format="mp3_44100_128",

                apply_text_normalization='auto',
                voice_settings=VoiceSettings(
                    speed=speed,
                    stability=0,
                    similarity_boost=0,
                    style=0,
                    use_speaker_boost=True
                )
            )
            with open(data_item['filename'] + ".mp3", 'wb') as f:
                for chunk in response:
                    if chunk:
                        f.write(chunk)
            self.convert_to_wav(data_item['filename'] + ".mp3", data_item['filename'])
            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.has_done += 1

            self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

        try:
            _run()
        except RetryError as e:
            raise e.last_attempt.exception()
        except Exception as e:
            self.error = e

    # 强制单个线程执行，防止频繁并发失败
    def _exec(self):
        self.dub_nums = 1
        self._local_mul_thread()


class ElevenLabsClone():

    def __init__(self, input_file_path, output_file_path, source_language, target_language,proxy_str=None):
        self.input_file_path = input_file_path
        self.output_file_path = output_file_path
        self.source_language = source_language
        self.target_language = target_language
        self.client = ElevenLabs(
            api_key=config.params['elevenlabstts_key'],
            httpx_client=httpx.Client(proxy=proxy_str)
        )


    def run(self):
        # 转为mp3发送
        mp3_audio = config.TEMP_DIR + f'/elevlabs-clone-{time.time()}.mp3'
        tools.runffmpeg(['-y', '-i', self.input_file_path, mp3_audio])

        try:
            with open(mp3_audio, "rb") as f:
                file_content_bytes = f.read()

            audio_data = io.BytesIO(file_content_bytes)
            audio_data.name = os.path.basename(mp3_audio)
            # Start dubbing
            dubbed = self.client.dubbing.create(
                file=audio_data, target_lang=self.target_language[:2]
            )

            while True:
                status = self.client.dubbing.get(dubbed.dubbing_id).status
                if status == "dubbed":
                    dubbed_file = self.client.dubbing.audio.get(dubbed.dubbing_id)
                    if isinstance(dubbed_file, Iterator):
                        dubbed_file = b"".join(dubbed_file)
                    with open(self.output_file_path + ".mp3", "wb") as file:
                        f.write(dubbed_file)
                    tools.runffmpeg(
                        ['-y', '-i', self.output_file_path + ".mp3", "-ar", "44100", "-ac", "2", "-b:a", "128k",
                         self.output_file_path])
                    return True
                time.sleep(5)

        except Exception as e:
            self.error = e
            raise
