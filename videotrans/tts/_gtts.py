import copy
from typing import Union, Dict, List

import requests
from gtts import gTTS

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


# 线程池并发

class GTTS(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.copydata = copy.deepcopy(self.queue_tts)
        self.api_url='https://translate.google.com'
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies = {"https": pro, "http": pro}

    def _exec(self):
        self._local_mul_thread()

    def _item_task(self, data_item: Union[Dict, List, None]):
        if self._exit():
            return
        if not data_item or tools.vail_file(data_item['filename']):
            return
        try:
            text = data_item['text'].strip()
            if not text:
                return
            lans = self.language.split('-')
            if len(lans) > 1:
                self.language = f'{lans[0]}-{lans[1].upper()}'
            response = gTTS(text, lang=self.language, lang_check=False)
            response.save(data_item['filename'])

            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error = ''
            self.has_done += 1
        except requests.ConnectionError as e:
            self.error = str(e)
            config.logger.exception(e, exc_info=True)
        except Exception as e:
            self.error = str(e)
            config.logger.exception(e, exc_info=True)
        finally:
            if self.error:
                self._signal(text=self.error)
            else:
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
