import requests
import sys
from PySide6.QtCore import QThread

import videotrans
from videotrans.configure.config import transobj
from videotrans.util import tools
from videotrans.util.tools import set_process


class CheckUpdateWorker(QThread):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def get(self):
        try:
            url = f"https://pyvideotrans.com/version.json?version={videotrans.VERSION}&os={sys.platform}"
            res = requests.get(url)
            if res.status_code == 200:
                d = res.json()
                if d['version_num'] > videotrans.VERSION_NUM:
                    msg = f"{transobj['newversion']}:{d['version']}"
                    set_process(text=msg, type="check_soft_update")
        except Exception as e:
            pass
        return False

    def run(self):
        self.get()
