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
        try:
            pwd=config.rootdir+f"/ffmpeg/yt{sys.platform}"
            proxy=self.proxy if self.proxy.startswith("http") or self.proxy.startswith('sock') else None
            proxy="" if not proxy else f' --proxy {proxy} '
            cmd=f'{pwd} -c -P {self.out}   {proxy} --windows-filenames --force-overwrites    --ignore-errors --merge-output-format mp4 {self.url}'
            print(f'{cmd=}')
            subprocess.run(cmd)

        except Exception as e:
            pass
