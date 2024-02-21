# 从日志队列获取日志
import time

import requests
from PySide6.QtCore import QThread

import videotrans
from videotrans.util.tools import  set_process
from videotrans.configure.config import transobj


class CheckUpdateWorker(QThread):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def get(self):
        try:
            res=requests.get("https://pyvideotrans.com/version.json")
            if res.status_code==200:
                d=res.json()
                if d['version_num']>videotrans.VERSION_NUM:
                    msg = f"{transobj['newversion']}:{d['version']}"
                    length = len(msg)
                    while 1:
                        tmp=""
                        for i in range(length):
                            if i == 0:
                                tmp=msg
                            elif i == length - 1:
                                tmp=msg
                            else:
                                tmp=msg[i:] + msg[:i]
                            set_process(tmp,"check_soft_update")
                            time.sleep(0.2)
                        time.sleep(5)
                return True
        except Exception as e:
            pass
        return False

    def run(self):
        while not self.get():
            time.sleep(60)
