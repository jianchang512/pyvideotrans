import copy
import os
import re
import time
from pathlib import Path


import requests

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class F5TTS(BaseTTS):
    v1_local: bool = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        self.copydata = copy.deepcopy(self.queue_tts)
        api_url = config.params['f5tts_url'].strip().rstrip('/').lower()
        self.api_url = f'http://{api_url}' if not api_url.startswith('http') else api_url
        self.v1_local = True
        sepflag = self.api_url.find('/', 9)
        if sepflag > -1:
            self.api_url = self.api_url[:sepflag]

        if not re.search(r'127.0.0.1|localhost', self.api_url):
            self.v1_local = False
        elif re.search(r'^https:', self.api_url):
            self._set_proxy(type='set')


    def _exec(self):
        self._local_mul_thread()

    def _item_task_v1(self, data_item: Union[Dict, List, None]):
        from gradio_client import Client, handle_file
        speed = 1.0
        try:
            speed = 1 + float(self.rate.replace('%', '')) / 100
        except:
            pass

        text = data_item['text'].strip()
        role = data_item['role']
        data = {'ref_text': '', 'ref_wav': ''}

        if role == 'clone':
            data['ref_wav'] = data_item['ref_wav']
            if not config.params.get('f5tts_is_whisper'):
                data['ref_text'] = data_item.get('ref_text').strip()
        else:
            roledict = tools.get_f5tts_role()
            if role in roledict:
                data['ref_text'] = roledict[role]['ref_text'] if not config.params.get('f5tts_is_whisper') else ''
                data['ref_wav'] = config.ROOT_DIR + f"/f5-tts/{role}"

        if not Path(data['ref_wav']).exists():
            self.error = f'{role} 角色不存在'
            return
        if data['ref_text'] and len(data['ref_text']) < 10:
            speed = 0.5
        client = Client(self.api_url, httpx_kwargs={"timeout": 7200}, ssl_verify=False)

        result = client.predict(
            ref_audio_input=handle_file(data['ref_wav']),
            ref_text_input=data['ref_text'],
            gen_text_input=text,
            remove_silence=True,

            speed_slider=speed,
            api_name='/basic_tts'
        )

        config.logger.info(f'result={result}')
        wav_file = result[0] if isinstance(result, (list, tuple)) else result
        if self.v1_local or (isinstance(wav_file, str) and Path(wav_file).is_file()):
            tools.wav2mp3(wav_file, data_item['filename'])
        else:
            resp = requests.get(self.api_url + f'/gradio_api/file=' + Path(wav_file).as_posix())
            resp.raise_for_status()
            with open(data_item['filename'] + ".wav", 'wb') as f:
                f.write(resp.content)
            time.sleep(1)
            if not os.path.exists(data_item['filename'] + ".wav"):
                self.error = f'F5-TTS合成声音失败-2:{text=}'
                return
            tools.wav2mp3(data_item['filename'] + ".wav", data_item['filename'])
        if self.inst and self.inst.precent < 80:
            self.inst.precent += 0.1
        self.error = ''
        self.has_done += 1
        self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

    def _item_task_spark(self, data_item: Union[Dict, List, None]):
        from gradio_client import Client, handle_file
        speed = 1.0
        try:
            speed = 1 + float(self.rate.replace('%', '')) / 100
        except:
            pass

        text = data_item['text'].strip()
        role = data_item['role']
        data = {'ref_text': '', 'ref_wav': ''}

        if role == 'clone':
            data['ref_wav'] = data_item['ref_wav']
            data['ref_text'] = data_item.get('ref_text', '')
        else:
            roledict = tools.get_f5tts_role()
            if role in roledict:
                data['ref_wav'] = config.ROOT_DIR + f"/f5-tts/{role}"

        if not Path(data['ref_wav']).exists():
            self.error = f'{role} 角色不存在'
            return

        client = Client(self.api_url, httpx_kwargs={"timeout": 7200}, ssl_verify=False)

        result = client.predict(
            text=text,
            prompt_text=data['ref_text'],
            prompt_wav_upload=handle_file(data['ref_wav']),
            prompt_wav_record=None,
            api_name='/voice_clone'
        )

        config.logger.info(f'result={result}')
        wav_file = result[0] if isinstance(result, (list, tuple)) else result
        if self.v1_local or (isinstance(wav_file, str) and Path(wav_file).is_file()):
            tools.wav2mp3(wav_file, data_item['filename'])
        else:
            resp = requests.get(self.api_url + f'/gradio_api/file=' + Path(wav_file).as_posix())
            resp.raise_for_status()
            with open(data_item['filename'] + ".wav", 'wb') as f:
                f.write(resp.content)
            time.sleep(1)
            if not os.path.exists(data_item['filename'] + ".wav"):
                self.error = f'Spark-TTS合成声音失败-2:{text=}'
                return
            tools.wav2mp3(data_item['filename'] + ".wav", data_item['filename'])
        if self.inst and self.inst.precent < 80:
            self.inst.precent += 0.1
        self.error = ''
        self.has_done += 1
        self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

    def _item_task_index(self, data_item: Union[Dict, List, None]):
        from gradio_client import Client, handle_file
        speed = 1.0
        try:
            speed = 1 + float(self.rate.replace('%', '')) / 100
        except:
            pass

        text = data_item['text'].strip()
        role = data_item['role']
        data = {'ref_wav': ''}

        if role == 'clone':
            data['ref_wav'] = data_item['ref_wav']
        else:
            roledict = tools.get_f5tts_role()
            if role in roledict:
                data['ref_wav'] = config.ROOT_DIR + f"/f5-tts/{role}"

        if not Path(data['ref_wav']).exists():
            self.error = f'{role} 角色不存在'
            return

        client = Client(self.api_url, httpx_kwargs={"timeout": 7200}, ssl_verify=False)

        result = client.predict(
            prompt=handle_file(data['ref_wav']),
            text=text,
            api_name='/gen_single'
        )

        config.logger.info(f'result={result}')
        wav_file = result[0] if isinstance(result, (list, tuple)) else result
        if isinstance(wav_file, dict) and "value" in wav_file:
            wav_file = wav_file['value']
        if self.v1_local or (isinstance(wav_file, str) and Path(wav_file).is_file()):
            tools.wav2mp3(wav_file, data_item['filename'])
        else:
            resp = requests.get(self.api_url + f'/gradio_api/file=' + Path(wav_file).as_posix())
            resp.raise_for_status()
            with open(data_item['filename'] + ".wav", 'wb') as f:
                f.write(resp.content)
            time.sleep(1)
            if not os.path.exists(data_item['filename'] + ".wav"):
                self.error = f'index-TTS合成声音失败-2:{text=}'
                return
            tools.wav2mp3(data_item['filename'] + ".wav", data_item['filename'])
        if self.inst and self.inst.precent < 80:
            self.inst.precent += 0.1
        self.error = ''
        self.has_done += 1
        self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

    def _item_task_dia(self, data_item: Union[Dict, List, None]):
        from gradio_client import Client, handle_file
        speed = 1.0
        try:
            speed = 1 + float(self.rate.replace('%', '')) / 100
        except:
            pass

        text = data_item['text'].strip()
        role = data_item['role']
        data = {'ref_wav': ''}

        if role == 'clone':
            data['ref_wav'] = data_item['ref_wav']
        else:
            roledict = tools.get_f5tts_role()
            if role in roledict:
                data['ref_wav'] = config.ROOT_DIR + f"/f5-tts/{role}"
                data['ref_text'] = roledict.get('ref_text', '')

        if not Path(data['ref_wav']).exists():
            self.error = f'{role} 角色不存在'
            return

        client = Client(self.api_url, httpx_kwargs={"timeout": 7200, "proxy": None}, ssl_verify=False)

        result = client.predict(
            text_input=text,
            audio_prompt_input=handle_file(data['ref_wav']),
            transcription_input=data.get('ref_text', ''),
            api_name='/generate_audio'
        )

        config.logger.info(f'result={result}')
        wav_file = result[0] if isinstance(result, (list, tuple)) else result
        if self.v1_local or (isinstance(wav_file, str) and Path(wav_file).is_file()):
            tools.wav2mp3(wav_file, data_item['filename'])
        else:
            resp = requests.get(self.api_url + f'/gradio_api/file=' + Path(wav_file).as_posix())
            resp.raise_for_status()
            with open(data_item['filename'] + ".wav", 'wb') as f:
                f.write(resp.content)
            time.sleep(1)
            if not os.path.exists(data_item['filename'] + ".wav"):
                self.error = f'Dia-TTS合成声音失败-2:{text=}'
                return
            tools.wav2mp3(data_item['filename'] + ".wav", data_item['filename'])
        if self.inst and self.inst.precent < 80:
            self.inst.precent += 0.1
        self.error = ''
        self.has_done += 1
        self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

    def _item_task(self, data_item: Union[Dict, List, None]):

        ttstype = config.params.get('f5tts_ttstype')
        # Spark-TTS','Index-TTS Dia-TTS
        for attempt in range(RETRY_NUMS):
            if self._exit():
                return
            try:
                if ttstype == 'Spark-TTS':
                    self._item_task_spark(data_item)
                elif ttstype == 'Index-TTS':
                    self._item_task_index(data_item)
                elif ttstype == 'Dia-TTS':
                    self._item_task_dia(data_item)
                else:
                    self._item_task_v1(data_item)
            except Exception as e:
                config.logger.exception(e,exc_info=True)
                self.error = str(e)
                self._signal(text=f"{data_item.get('line','')} retry {attempt}: "+self.error)
                time.sleep(RETRY_DELAY)
