# 从日志队列获取日志
import time

import requests
from PyQt5.QtCore import QThread

import videotrans
from videotrans.util.tools import set_proxy, set_process
from videotrans.configure.config import transobj


class CheckUpdateWorker(QThread):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def run(self):
        time.sleep(15)
        try:
            proxy=None
            pro=set_proxy()
            if pro:
                proxy={
                    "http":"http://"+pro.replace('http://',''),
                    "https":"http://"+pro.replace('http://',''),
                }
            res=requests.get("https://raw.githubusercontent.com/jianchang512/pyvideotrans/main/version.json",proxies=proxy)
            print(f"{res.status_code=}")
            print(f"{res=}")
            if res.status_code==200:
                d=res.json()
                print(f"{d=}")
                if d['version_num']>videotrans.VERSION_NUM:
                    set_process(f"{transobj['newversion']}:{d['version']}","check_soft_update")
        except Exception as e:
            print(e)
            # pass