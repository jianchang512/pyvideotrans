# 从日志队列获取日志
import subprocess
import sys
from PySide6.QtCore import QThread

from videotrans.configure import config
from videotrans.util.tools import  set_process


class Download(QThread):

    def __init__(self, *,url=None,proxy=None,out=None,parent=None):
        super().__init__(parent=parent)
        self.url=url
        self.proxy=proxy
        self.out=out

    def run(self):
        set_process(config.transobj["downing..."],'update_download')
        from you_get.extractors import  youtube
        try:
            youtube.download(self.url,
                output_dir=self.out,
                merge=True,
                extractor_proxy=self.proxy if self.proxy.startswith("http") or self.proxy.startswith('sock') else None
            )
        except Exception as e:
            set_process("[error]"+str(e),'update_download')

            return
        set_process('ok','update_download')
