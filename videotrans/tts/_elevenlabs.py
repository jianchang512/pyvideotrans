import copy
import json
import os
import time

import elevenlabs
import httpx
from elevenlabs import ElevenLabs, VoiceSettings
from elevenlabs.core import ApiError

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

RETRY_NUMS = 2
RETRY_DELAY = 5

@dataclass
class ElevenLabsC(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = pro

    def _item_task(self, data_item: dict = None):
        role = data_item['role']

        speed = 1.0
        if self.rate and self.rate != '+0%':
            speed += float(self.rate.replace('%', ''))
        for attempt in range(RETRY_NUMS):
            try:
                with open(os.path.join(config.ROOT_DIR, 'elevenlabs.json'), 'r', encoding="utf-8") as f:
                    jsondata = json.loads(f.read())

                client = ElevenLabs(
                    api_key=config.params['elevenlabstts_key'],
                    httpx_client=httpx.Client(proxy=self.proxies) if self.proxies else None
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
                with open(data_item['filename'], 'wb') as f:
                    for chunk in response:
                        if chunk:
                            f.write(chunk)
                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.1
                self.error = ''
                self.has_done += 1

                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
                return
            except ApiError as e:
                config.logger.exception(e,exc_info=True)
                self.error = str(e.body['detail']['message'])
                self._signal(text=f"{data_item.get('line','')} retry {attempt}: "+self.error)
                if e.status_code in [401,403,404,422,425]:
                    return
                time.sleep(RETRY_DELAY)
            except Exception as e:
                config.logger.exception(e,exc_info=True)
                self.error = str(e)
                self._signal(text=f"{data_item.get('line','')} retry {attempt}: "+self.error)
                time.sleep(60)
    # 强制单个线程执行，防止频繁并发失败
    def _exec(self):
        self.dub_nums = 1
        self._local_mul_thread()



class ElevenLabsClone():

    def __init__(self, input_file_path, output_file_path, source_language, target_language):
        self.input_file_path = input_file_path
        self.output_file_path = output_file_path
        self.source_language = source_language
        self.target_language = target_language
        self.error = ''
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = pro
        self.client = ElevenLabs(
            api_key=config.params['elevenlabstts_key'],
            httpx_client=httpx.Client(proxy=self.proxies) if pro else None
        )

    def _set_proxy(self, type='set'):
        if type == 'del' and self.shound_del:
            try:
                del os.environ['http_proxy']
                del os.environ['https_proxy']
                del os.environ['all_proxy']
            except:
                pass
            self.shound_del = False
            return

        if type == 'set':
            raw_proxy = os.environ.get('http_proxy') or os.environ.get('https_proxy')
            if raw_proxy:
                return raw_proxy
            if not raw_proxy:
                proxy = tools.set_proxy()
                if proxy:
                    self.shound_del = True
                    os.environ['http_proxy'] = proxy
                    os.environ['https_proxy'] = proxy
                    os.environ['all_proxy'] = proxy
                return proxy
        return None

    # 强制单个线程执行，防止频繁并发失败
    def run(self):
        # 转为mp3发送
        mp3_audio = config.TEMP_DIR + f'/elevlabs-clone-{time.time()}.mp3'
        tools.runffmpeg(['-y', '-i', self.input_file_path, mp3_audio])
        for attempt in range(RETRY_NUMS):
            try:
                with open(mp3_audio, "rb") as audio_file:
                    response = self.client.dubbing.dub_a_video_or_an_audio_file(
                        file=(os.path.basename(mp3_audio), audio_file, "audio/mpeg"),
                        target_lang=self.target_language[:2],
                        source_lang='auto' if self.source_language == 'auto' else self.source_language[:2],
                        num_speakers=0,
                        watermark=False  # reduces the characters used if enabled, only works for videos not audio
                    )

                dubbing_id = response.dubbing_id
                if self.wait_for_dubbing_completion(dubbing_id):
                    # 返回为mp3数据，转为 原m4a格式
                    with open(self.output_file_path + ".mp3", "wb") as file:
                        for chunk in self.client.dubbing.get_dubbed_file(dubbing_id, self.target_language):
                            file.write(chunk)
                    tools.runffmpeg(['-y', '-i', self.output_file_path + ".mp3", self.output_file_path])
                    self.error = ""
                    return True
            except Exception as e:
                config.logger.exception(e,exc_info=True)
                self.error = str(e)
                time.sleep(RETRY_DELAY)

        if self.error:
            raise RuntimeError(self.error)

    def wait_for_dubbing_completion(self, dubbing_id: str) -> bool:
        MAX_ATTEMPTS = 120
        CHECK_INTERVAL = 10  # In seconds
        for _ in range(MAX_ATTEMPTS):
            metadata = self.client.dubbing.get_dubbing_project_metadata(dubbing_id)
            if metadata.status == "dubbed":
                return True
            elif metadata.status == "dubbing":
                print(
                    "Dubbing in progress... Will check status again in",
                    CHECK_INTERVAL,
                    "seconds.",
                )
                time.sleep(CHECK_INTERVAL)
            else:
                raise Exception("Dubbing failed:", metadata.error_message)

        raise Exception("Dubbing timed out")
