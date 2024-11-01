# zh_recogn 识别
import os
import time
from typing import Union, List, Dict

import requests

from videotrans.configure import config

from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools


class DoubaoRecogn(BaseRecogn):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raws = []

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return

        base_url = 'https://openspeech.bytedance.com/api/v1/vc'
        appid = config.params['doubao_appid']
        access_token = config.params['doubao_access']
        if not appid or not access_token:
            raise Exception('必须填写豆包应用APP ID和 Access Token')

        # 尺寸大于190MB，转为 mp3
        if os.path.getsize(self.audio_file) > 199229440:
            tools.runffmpeg(
                ['-y', '-i', self.audio_file, '-ac', '1', '-ar', '16000', self.cache_folder + '/doubao-tmp.mp3'])
            self.audio_file = self.cache_folder + '/doubao-tmp.mp3'
        with open(self.audio_file, 'rb') as f:
            files = f.read()

        self._signal(text=f"识别可能较久，请耐心等待")

        languagelist = {"zh": "zh-CN", "en": "en-US", "ja": "ja-JP", "ko": "ko-KR", "es": "es-MX", "ru": "ru-RU", "fr": "fr-FR"}
        langcode = self.detect_language[:2].lower()
        if langcode not in languagelist:
            raise Exception(f'不支持的语言代码:{langcode=}')
        language = languagelist[langcode]
        try:
            res = requests.post(
                f'{base_url}/submit',
                data=files,
                proxies={"http": "", "https": ""},
                params=dict(
                    appid=appid,
                    language=language,
                    use_itn='True',
                    caption_type='speech',
                    max_lines=1  # 每条字幕只允许一行文字
                    # words_per_line=15,#每行文字最多15个字符
                ),
                headers={
                    'Content-Type': 'audio/wav',
                    'Authorization': 'Bearer; {}'.format(access_token)
                },
                timeout=3600
            )
            if res.status_code != 200:
                raise Exception(f'请求失败:{res.text=},{res.status_code=},{base_url=}')
            res = res.json()
            if res['code'] != 0:
                raise Exception(f'请求失败:{res["message"]}')

            job_id = res['id']
            delay = 0
            while 1:
                if self._exit():
                    return
                delay += 1
                # 获取进度
                response = requests.get(
                    '{base_url}/query'.format(base_url=base_url),
                    params=dict(
                        appid=appid,
                        id=job_id,
                        blocking=0
                    ),
                    proxies={"http": "", "https": ""},
                    headers={
                        'Authorization': 'Bearer; {}'.format(access_token)
                    }
                )

                result = response.json()
                if result['code'] == 2000:
                    self._signal(text=f"任务处理中，请等待 {delay}s..")
                    time.sleep(1)
                elif result['code'] > 0:
                    raise Exception(result['message'])
                else:
                    break

            for i, it in enumerate(result['utterances']):
                if self._exit():
                    return
                srt = {
                    "line": i + 1,
                    "start_time": it['start_time'],
                    "end_time": it['end_time'],
                    "endraw": tools.ms_to_time_string(ms=it["end_time"]),
                    "startraw": tools.ms_to_time_string(ms=it["start_time"]),
                    "text": it['text']
                }
                srt['time'] = f'{srt["startraw"]} --> {srt["endraw"]}'
                self._signal(
                    text=f'{srt["line"]}\n{srt["time"]}\n{srt["text"]}\n\n',
                    type='subtitle'
                )
                self.raws.append(srt)
            return self.raws
        except Exception as e:
            raise
