import copy
import json
import os
import re
import time

from elevenlabs import generate, Voice, set_api_key

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


# 单个线程执行，防止远端限制

class ElevenLabs(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.copydata = copy.deepcopy(self.queue_tts)
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = {"https": pro, "http": pro}

    # 强制单个线程执行，防止频繁并发失败
    def _exec(self):
        while len(self.copydata) > 0:
            if self._exit():
                return
            try:
                data_item = self.copydata.pop(0)
                if tools.vail_file(data_item['filename']):
                    continue
            except:
                return

            text = data_item['text'].strip()
            role = data_item['role']
            if not text:
                continue
            try:
                with open(os.path.join(config.ROOT_DIR, 'elevenlabs.json'), 'r', encoding="utf-8") as f:
                    jsondata = json.loads(f.read())
                if config.params['elevenlabstts_key']:
                    set_api_key(config.params['elevenlabstts_key'])
                audio = generate(
                    text=text,
                    voice=Voice(voice_id=jsondata[role]['voice_id']),
                    model="eleven_multilingual_v2"
                )
                with open(data_item['filename'], 'wb') as f:
                    f.write(audio)
                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.1
                self.error = ''
                self.has_done += 1
            except Exception as e:
                error = str(e)
                self.error = error
                if error and re.search(r'rate|limit', error, re.I) is not None:
                    self._signal(
                        text='超过频率限制，等待60s后重试' if config.defaulelang == 'zh' else 'Frequency limit exceeded, wait 60s and retry')
                    self.copydata.append(data_item)
                    time.sleep(60)
            finally:
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
                time.sleep(self.wait_sec)
