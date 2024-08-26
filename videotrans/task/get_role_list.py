# 从日志队列获取日志
from PySide6.QtCore import QThread

from videotrans.util.tools import get_edge_rolelist, get_elevenlabs_role, get_clone_role


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
