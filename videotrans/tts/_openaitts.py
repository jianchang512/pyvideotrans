import logging
import re
from dataclasses import dataclass

import httpx

from openai import OpenAI,AuthenticationError, PermissionDeniedError, NotFoundError, BadRequestError

from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log, \
    RetryError

from videotrans.configure import config
from videotrans.configure.config import logs
from videotrans.configure._except import NO_RETRY_EXCEPT
from videotrans.tts._base import BaseTTS
from videotrans.util import tools



RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class OPENAITTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        self.stop_next_all=False
        self.api_url = self._get_url(config.params.get('openaitts_api',''))
        self._add_internal_host_noproxy(self.api_url)


    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: dict = None):
        if self.stop_next_all or self._exit() or not data_item.get('text','').strip():
            return
        @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO))
        def _run():
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            role = data_item['role']

            speed = 1.0
            if self.rate:
                rate = float(self.rate.replace('%', '')) / 100
                speed += rate
            if self._exit() or tools.vail_file(data_item['filename']):
                return
            try:
                client = OpenAI(api_key=config.params.get('openaitts_key', ''), base_url=self.api_url,
                                http_client=httpx.Client(proxy=self.proxy_str))
                with client.audio.speech.with_streaming_response.create(
                        model=config.params.get('openaitts_model',''),
                        voice=role,
                        input=data_item['text'],
                        speed=speed,
                        response_format="wav",
                        instructions=config.params.get('openaitts_instructions', '')
                ) as response:
                    with open(data_item['filename'] + ".wav", 'wb') as f:
                        for chunk in response.iter_bytes():
                            f.write(chunk)
            except (AuthenticationError, PermissionDeniedError, NotFoundError, BadRequestError):
                self.stop_next_all=True
                raise
            self.convert_to_wav(data_item['filename'] + ".wav", data_item['filename'])

        try:
            _run()
        except RetryError as e:
            self.error= e.last_attempt.exception()
        except Exception as e:
            self.error = e

    def _get_url(self, url=""):
        if not url:
            return "https://api.openai.com/v1"
        if not url.startswith('http'):
            url = 'http://' + url
            # 删除末尾 /
        url = url.rstrip('/').lower()
        if url.find(".openai.com") > -1:
            return "https://api.openai.com/v1"

        if url.endswith('/v1'):
            return url
        # 存在 /v1/xx的，改为 /v1
        if url.find('/v1/chat/') > -1:
            return re.sub(r'/v1.*$', '/v1', url,flags=re.I | re.S)

        if re.match(r'^https?://[a-zA-Z0-9_\.-]+$', url):
            return url + "/v1"

        return url
