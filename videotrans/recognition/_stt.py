# stt项目识别接口
import os
from dataclasses import dataclass
from typing import List, Union

import requests

from videotrans.configure.excepts import NO_RETRY_EXCEPT, StopRetry, SpeechToTextError,StopTask
from videotrans.configure.config import tr, params, logger, settings
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem
from videotrans.util import tools

"""
            请求发送：以二进制形式发送键名为 audio 的wav格式音频数据，采样率为16k、通道为1
            requests.post(api_url, files={"file": open(audio_file, 'rb')},data={language:2位语言代码,model:模型名})

            失败时返回
            res={
                "code":1,
                "msg":"错误原因"
            }

            成功时返回
            res={
                "code":0,
                "data":srt格式字符串
            }
"""

from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
import logging


@dataclass
class SttAPIRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()
        api_url = params.get('stt_url', '').strip().rstrip('/').lower()
        if not api_url:
            raise SpeechToTextError(tr("Custom api address must be filled in"))

        if not api_url.startswith('http'):
            api_url = f'http://{api_url}'
        self.api_url = f'{api_url}/api' if not api_url.endswith('/api') else api_url

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _exec(self) -> Union[List[SrtItem],None]:
        if self._exit(): return
        with open(self.audio_file, 'rb') as f:
            chunk = f.read()
        files = {"file": (os.path.basename(self.audio_file), chunk)}
        self.signal(
            text=tr("Recognition may take a while, please be patient"))

        data = {"language": self.detect_language[:2], "model": params.get('stt_model', 'tiny'),
                "response_format": "srt"}
        try:
            res = requests.post(f"{self.api_url}", files=files, data=data, timeout=7200)
        except requests.exceptions.ConnectionError as e:
            raise StopTask(f"[STT] {tr('This channel needs deployed and started before available')}") from e
        res.raise_for_status()
        res = res.json()
        if "code" not in res or res['code'] != 0:
            raise StopRetry(f'{res["msg"]}')
        if "data" not in res or len(res['data']) < 1:
            raise StopRetry(f'{res=}')
        self.signal(
            text=res['data'],
            type='replace_subtitle'
        )
        return tools.get_subtitle_from_srt(res['data'], is_file=False)
