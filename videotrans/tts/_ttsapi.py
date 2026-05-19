import logging
import sys
from dataclasses import dataclass
from typing import List, Dict
from typing import Union
import requests

from videotrans.configure.excepts import StopTask, NO_RETRY_EXCEPT
from videotrans.configure.config import tr, params, logger, settings
from videotrans.tts._base import BaseTTS
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log


@dataclass
class TTSAPI(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.speed=self.get_speed()

        api_url = params.get('ttsapi_url','').strip().rstrip('/').lower()
        if len(api_url)<4:
            raise StopTask(f'API URL is error: {api_url}')
        if not api_url.startswith('http'):
            self.api_url = 'http://' + api_url
        else:
            self.api_url = api_url

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        data = {"text": data_item.get('text','').strip(),
                "language": self.language[:2] if self.language else "",
                "extra": params.get('ttsapi_extra',''),
                "voice": data_item['role'].strip(),
                "ostype": sys.platform,
                "rate": self.speed}
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        }
        logger.debug(f'发送数据 {data=}')
        resraw = requests.post(f"{self.api_url}", data=data, verify=False, headers=headers)
        if resraw.status_code in [401,403,404,405,415,422]:
            raise StopTask(resraw.text)
        resraw.raise_for_status()
        res=resraw.json()
        logger.debug(f'返回数据 {res["code"]=}')
        if "code" not in res or "msg" not in res or res['code'] != 0:
            return f'TTS-API:{res["msg"]}'

        if 'data' not in res or not res['data']:
            return  tr("No valid audio address returned")
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
            return tr("No valid audio address or base64 audio data returned")
        self.convert_to_wav(tmp_filename, data_item['filename'])


