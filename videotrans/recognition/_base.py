import os
from typing import List, Dict, Union

from videotrans.configure import config
from videotrans.configure._except import LogExcept
from videotrans.util import tools


class BaseRecogn:

    def __init__(self, *,
                 type="all",
                 detect_language=None,
                 audio_file=None,
                 cache_folder=None,
                 model_name=None,
                 inst=None,
                 uuid=None,
                 model_type: int = 0,
                 is_cuda=None):
        self.type = type
        self.detect_language = detect_language
        self.audio_file = audio_file
        self.cache_folder = cache_folder
        self.model_name = model_name
        self.inst = inst
        self.uuid = uuid
        self.model_type = model_type
        self.is_cuda = is_cuda

        self.shound_del = False
        self.api_url = ''
        self.proxies = None

        self.flag = [
            ",",
            ":",
            "'",
            "\"",
            ".",
            "?",
            "!",
            ";",
            ")",
            "]",
            "}",
            ">",
            "，",
            "。",
            "？",
            "；",
            "’",
            "”",
            "》",
            "】",
            "｝",
            "！"
        ]
        if not tools.vail_file(self.audio_file):
            raise LogExcept(f'[error]not exists {self.audio_file}')
    # 出错时发送停止信号
    def run(self) -> Union[List[Dict], None]:
        try:
            return self._exec()
        except Exception as e:
            self._signal(text=str(e),type="error")
            raise LogExcept(f'{self.__class__.__name__}:{e}')
        finally:
            if self.shound_del:
                self._set_proxy(type='del')

    def _exec(self) -> Union[List[Dict], None]:
        pass

    def _signal(self,text="",type="logs",nologs=False):
        tools.set_process(text=text,type=type,uuid=self.uuid,nologs=nologs)

    def _set_proxy(self, type='set'):
        if type == 'del' and self.shound_del:
            del os.environ['http_proxy']
            del os.environ['https_proxy']
            del os.environ['all_proxy']
            self.shound_del = False
        elif type == 'set':
            raw_proxy = os.environ.get('http_proxy')
            if not raw_proxy:
                proxy = tools.set_proxy()
                if proxy:
                    self.shound_del = True
                    os.environ['http_proxy'] = proxy
                    os.environ['https_proxy'] = proxy
                    os.environ['all_proxy'] = proxy

    # True 退出
    def _exit(self) -> bool:
        if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
            return True
        return False
