import copy
import os
from typing import Union, Dict, List

import requests
from gtts import gTTS

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

# 线程池并发

class GTTS(BaseTTS):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.copydata=copy.deepcopy(self.queue_tts)

    def _exec(self):
        self._set_proxy(type='set')
        self._local_mul_thread()


    def _item_task(self,data_item:Union[Dict,List,None]):
        try:
            data_item=self.copydata.pop(0)
            if tools.vail_file(data_item['filename']):
                return True
        except:
            return True
        try:
            text = data_item['text'].strip()
            if not text:
                return True
            lans = self.language.split('-')
            if len(lans) > 1:
                self.language = f'{lans[0]}-{lans[1].upper()}'
            response = gTTS(text, lang=self.language, lang_check=False)
            response.save(data_item['filename'])

            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error=''
            self.has_done+=1
            return True
        except requests.ConnectionError as e:
            self.error=str(e)
            config.logger.exception(e,exc_info=True)
        except Exception as e:
            self.error = str(e)
            config.logger.exception(e,exc_info=True)
        finally:
            if self.error:
                tools.set_process(self.error, uuid=self.uuid)
            else:
                tools.set_process(f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}', uuid=self.uuid)
        return False
