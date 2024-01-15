# 从日志队列获取日志
import subprocess
import sys
from PyQt5.QtCore import QThread

from videotrans.util.tools import  set_process


class Download(QThread):

    def __init__(self, cmd=[],parent=None):
        super().__init__(parent=parent)
        self.cmd=cmd

    def run(self):
        p = subprocess.Popen(self.cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             shell=True,
                             creationflags=0 if sys.platform != 'win32' else subprocess.CREATE_NO_WINDOW
                             )

        while True:
            try:
                # 等待0.1未结束则异常
                outs, errs = p.communicate(timeout=0.5)
                errs = str(errs)
                if errs:
                    errs = errs.replace('\\\\', '\\').replace('\r', ' ').replace('\n', ' ')

                # 如果结束从此开始执行
                if p.returncode==0:
                    # 成功
                    set_process('ok','update_download')
                    break
                # 失败
                set_process(str(errs),'update_download')
            except subprocess.TimeoutExpired as e:
                # 如果前台要求停止
                set_process("downing...",'update_download')

            except Exception as e:
                # 出错异常
                set_process(str(e),'update_download')
