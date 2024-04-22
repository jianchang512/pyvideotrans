# 从日志队列获取日志
import requests
from PySide6.QtCore import QThread

import videotrans
from videotrans.util.tools import set_process, get_edge_rolelist, get_elevenlabs_role, get_clone_role
from videotrans.configure.config import transobj


class GetRoleWorker(QThread):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def run(self):
        try:
            get_edge_rolelist()
        except Exception as e:
            print(e)
        try:
            get_elevenlabs_role()
        except Exception as e:
            print(e)
        try:
            get_clone_role()
        except Exception as e:
            print(e)
