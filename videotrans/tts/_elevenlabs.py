import copy
import json
import os
import re
import time

import httpx
from elevenlabs import ElevenLabs,VoiceSettings


from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


# 单个线程执行，防止远端限制

class ElevenLabsC(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.copydata = copy.deepcopy(self.queue_tts)
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = pro

    # 强制单个线程执行，防止频繁并发失败
    def _exec(self):
        prev_text = None
        speed=1.0
        if self.rate and self.rate !='+0%':
            speed+=float(self.rate.replace('%',''))

        while len(self.copydata) > 0:
            if self._exit():
                return
            try:
                data_item = self.copydata.pop(0)
                if tools.vail_file(data_item['filename']):
                    prev_text = data_item['text']
                    continue
            except:
                return

            text = data_item['text'].strip()
            role = data_item['role']
            if not text:
                prev_text = None
                continue
            try:
                with open(os.path.join(config.ROOT_DIR, 'elevenlabs.json'), 'r', encoding="utf-8") as f:
                    jsondata = json.loads(f.read())

                client = ElevenLabs(
                    api_key=config.params['elevenlabstts_key'],
                    httpx_client=httpx.Client(proxy=self.proxies) if self.proxies else None
                )

                response = client.text_to_speech.convert(
                    text=text,
                    voice_id=jsondata[role]['voice_id'],
                    model_id=config.params.get("elevenlabstts_models"),
                    previous_text=prev_text,
                    output_format="mp3_44100_128",
                    next_text=self.copydata[0]['text'] if len(self.copydata) > 0 else None,
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
                prev_text = text
            except Exception as e:
                error = str(e)
                print(error)
                config.logger.error(error)
                self.error = error
                if error and re.search(r'rate|limit', error, re.I) is not None:
                    self._signal(
                        text='超过频率限制，等待60s后重试' if config.defaulelang == 'zh' else 'Frequency limit exceeded, wait 60s and retry')
                    self.copydata.append(data_item)
                    time.sleep(60)
                    continue
            finally:
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
                time.sleep(self.wait_sec)


class ElevenLabsClone():

    def __init__(self, input_file_path, output_file_path, source_language, target_language):
        self.input_file_path = input_file_path
        self.output_file_path = output_file_path
        self.source_language = source_language
        self.target_language = target_language
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies =  pro
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
            return True
        raise Exception('Dubbing Timeout ')

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
