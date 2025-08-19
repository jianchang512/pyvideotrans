import sys
import logging
import sys
import time
from dataclasses import dataclass
from typing import List, Dict
from typing import Union

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log

from videotrans.configure import config
from videotrans.configure._except import RetryRaise
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class TTSAPI(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        api_url = config.params['ttsapi_url'].strip().rstrip('/').lower()
        if not api_url.startswith('http'):
            self.api_url = 'http://' + api_url
        else:
            self.api_url = api_url

    def _exec(self) -> None:
        self._local_mul_thread()

    def _item_task(self, data_item: Union[Dict, List, None]):
        @retry(retry=retry_if_not_exception_type(RetryRaise.NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO), retry_error_callback=RetryRaise._raise)
        def _run():
            role = data_item['role'].strip()

            speed = 1.0
            if self.rate:
                speed += float(self.rate.replace('%', '')) / 100
            volume = 1.0
            if self.volume:
                volume += float(self.volume.replace('%', '')) / 100
            pitch = 0
            if self.pitch:
                pitch += int(self.pitch.replace('Hz', ''))
            pitch = min(max(-12, pitch), 12)
            if self._exit() or tools.vail_file(data_item['filename']):
                return

            if '/t2a_v2' in self.api_url and 'minimax' in self.api_url:
                res = self._302aiMinimax(data_item['text'], role, speed, volume, pitch)
                config.logger.info(f'返回数据 {res["base_resp"]=}')
                if res['base_resp']['status_code'] != 0:
                    self.error = res['base_resp']['status_msg']
                    time.sleep(RETRY_DELAY)
                    raise RuntimeError(self.error)
            else:
                res = self._apirequests(data_item['text'], role, speed, volume, pitch)
                config.logger.info(f'返回数据 {res["code"]=}')
                if "code" not in res or "msg" not in res or res['code'] != 0:
                    self.error = f'TTS-API:{res["msg"]}'
                    time.sleep(RETRY_DELAY)
                    raise RuntimeError(self.error)

            if 'data' not in res or not res['data']:
                self.error = '未返回有效音频地址' if config.defaulelang == 'zh' else 'No valid audio address returned'
                time.sleep(RETRY_DELAY)
                raise RuntimeError(self.error)
            # 返回的是音频url地址
            tmp_filename = data_item['filename'] + ".mp3"
            if isinstance(res['data'], str) and res['data'].startswith('http'):
                url = res['data']
                res = requests.get(url)
                res.raise_for_status()
                with open(tmp_filename, 'wb') as f:
                    f.write(res.content)
            elif isinstance(res['data'], str) and res['data'].startswith('data:audio'):
                # 返回 base64数据
                self._base64_to_audio(res['data'], tmp_filename)
            elif isinstance(res['data'], dict) and 'audio' in res['data']:
                with open(tmp_filename, 'wb') as f:
                    f.write(bytes.fromhex(res['data']['audio']))
            else:
                self.error = '未返回有效音频地址或音频base64数据' if config.defaulelang == 'zh' else 'No valid audio address or base64 audio data returned'
                time.sleep(RETRY_DELAY)
                raise RuntimeError(self.error)
            self.convert_to_wav(tmp_filename, data_item['filename'])

            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error = ''
            self.has_done += 1
            self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

        _run()

    def _apirequests(self, text, role, speed=1.0, volume=1.0, pitch=0):
        data = {"text": text.strip(),
                "language": self.language[:2] if self.language else "",
                "extra": config.params['ttsapi_extra'],
                "voice": role,
                "ostype": sys.platform,
                "rate": speed}
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        }
        config.logger.info(f'发送数据 {data=}')
        resraw = requests.post(f"{self.api_url}", data=data, verify=False, headers=headers, proxies=None)
        resraw.raise_for_status()
        return resraw.json()

    """
青涩青年音色:male-qn-qingse,
精英青年音色:male-qn-jingying,
霸道青年音色:male-qn-badao,
青年大学生音色:male-qn-daxuesheng,
少女音色:female-shaonv,
御姐音色:female-yujie,
成熟女性音色:female-chengshu,
甜美女性音色:female-tianmei,
男性主持人:presenter_male,
女性主持人:presenter_female,
男性有声书1:audiobook_male_1,
男性有声书2:audiobook_male_2,
女性有声书1:audiobook_female_1,
女性有声书2:audiobook_female_2,
青涩青年音色-beta:male-qn-qingse-jingpin,
精英青年音色-beta:male-qn-jingying-jingpin,
霸道青年音色-beta:male-qn-badao-jingpin,
青年大学生音色-beta:male-qn-daxuesheng-jingpin,
少女音色-beta:female-shaonv-jingpin,
御姐音色-beta:female-yujie-jingpin,
成熟女性音色-beta:female-chengshu-jingpin,
甜美女性音色-beta:female-tianmei-jingpin,
聪明男童:clever_boy,
可爱男童:cute_boy,
萌萌女童:lovely_girl,
卡通猪小琪:cartoon_pig,
病娇弟弟:bingjiao_didi,
俊朗男友:junlang_nanyou,
纯真学弟:chunzhen_xuedi,
冷淡学长:lengdan_xiongzhang,
霸道少爷:badao_shaoye,
甜心小玲:tianxin_xiaoling,
俏皮萌妹:qiaopi_mengmei,
妩媚御姐:wumei_yujie,
嗲嗲学妹:diadia_xuemei,
淡雅学姐:danya_xuejie,
Santa Claus:Santa_Claus,
Grinch:Grinch,
Rudolph:Rudolph,
Arnold:Arnold,
Charming Santa:Charming_Santa,
Charming Lady:Charming_Lady,
Sweet Girl:Sweet_Girl,
Cute Elf:Cute_Elf,
Attractive Girl:Attractive_Girl,
Serene Woman:Serene_Woman    
    """

    def _302aiMinimax(self, text, role, speed=1.0, volume=1.0, pitch=0.0):
        import json
        payload = json.dumps({
            "model": "speech-01-turbo",
            "text": text,
            "stream": False,
            "voice_setting": {
                "voice_id": role.split(':')[-1],
                "speed": speed,
                "vol": volume,
                "pitch": pitch
            },
            "emotion": config.params.get('ttsapi_emotion', 'happy'),
            "language_boost": config.params.get('ttsapi_language_boost', 'auto'),
            "audio_setting": {
                "audio_sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1
            }
        }, ensure_ascii=False)
        print(payload)
        headers = {
            'Authorization': f"Bearer {config.params['ttsapi_extra']}",
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", self.api_url, headers=headers, data=payload)
        response.raise_for_status()
        return response.json()
