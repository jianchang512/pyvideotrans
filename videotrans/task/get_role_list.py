# 从日志队列获取日志
from PySide6.QtCore import QThread



class GetRoleWorker(QThread):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def run(self):        
        try:
            from videotrans.util.tools import get_elevenlabs_role
            get_elevenlabs_role()
        except Exception as e:
            print(e)