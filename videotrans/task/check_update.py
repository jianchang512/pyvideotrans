# 从日志队列获取日志
import time

import requests
from PySide6.QtCore import QThread

import videotrans
from videotrans.configure import config
from videotrans.util import tools
from videotrans.util.tools import  set_process
from videotrans.configure.config import transobj


class CheckUpdateWorker(QThread):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def get(self):
        try:
            proxies=None
            proxy=tools.set_proxy()
            if proxy:
                proxies={"http":proxy,"https":proxy}

            res=requests.get("https://pyvideotrans.com/version.json",proxies=proxies)
            if res.status_code==200:
                d=res.json()
                if d['version_num']>videotrans.VERSION_NUM:
                    msg = f"{transobj['newversion']}:{d['version']}"
                    set_process(msg,type="check_soft_update")
        except Exception as e:
            pass
        return False

    def run(self):
        self.get()