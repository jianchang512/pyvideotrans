import copy
import re
import time

import httpx,requests
from openai import OpenAI

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


# 强制单线程 防止远端限制出错

class OPENAITTS(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.copydata = copy.deepcopy(self.queue_tts)
        self.api_url = self._get_url(config.params['openaitts_api'])
        self.pro=None
        if not re.search('localhost', self.api_url) and not re.match(r'^https?://(\d+\.){3}\d+(:\d+)?', self.api_url):
            pro = self._set_proxy(type='set')
            if pro:
                self.proxies = {"https://": pro, "http://": pro}
                self.pro = {"https": pro, "http": pro}

    # 强制单个线程执行，防止频繁并发失败
    def _exec(self):
        if not config.params['openaitts_key']:
            raise Exception('必须在TTS设置 - OpenAI TTS 中填写 SK' if config.defaulelang=='zh' else 'please input your OpenAI TTS SK')
        if self.api_url:
            te=requests.get(self.api_url,proxies=self.pro)
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
            speed = 1.0
            if self.rate:
                rate = float(self.rate.replace('%', '')) / 100
                speed += rate
            try:
                client = OpenAI(api_key=config.params['openaitts_key'], base_url=self.api_url,
                                http_client=httpx.Client(proxies=self.proxies))
                response = client.audio.speech.create(
                    model=config.params['openaitts_model'],
                    voice=role,
                    input=text,
                    speed=speed
                )
                response.stream_to_file(data_item['filename'])
                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.1
                self.error = ''
                self.has_done += 1
            except Exception as e:
                config.logger.exception(e, exc_info=True)
                error = str(e)
                self.error = error
                if error and re.search(r'Rate limit', error, re.I) is not None:
                    self._signal(
                        text='超过频率限制，等待60s后重试' if config.defaulelang == 'zh' else 'Frequency limit exceeded, wait 60s and retry')
                    time.sleep(60)
                    self.copydata.append(data_item)
            finally:
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')

    def _get_url(self, url=""):
        if not url:
            return "https://api.openai.com/v1"
        if not url.startswith('http'):
            url = 'http://' + url
            # 删除末尾 /
        url = url.rstrip('/').lower()
        if url.find(".openai.com") > -1:
            return "https://api.openai.com/v1"
        # 存在 /v1/xx的，改为 /v1
        if re.match(r'.*/v1/.*$', url):
            return re.sub(r'/v1.*$', '/v1', url)
        # 不是/v1结尾的改为 /v1
        if url.find('/v1') == -1:
            return url + "/v1"
        return url
