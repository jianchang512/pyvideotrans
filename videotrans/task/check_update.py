import requests
import sys
from PySide6.QtCore import QThread

from videotrans.configure.config import tr,settings,params,app_cfg,logger


class CheckUpdateWorker(QThread):

    def __init__(self, parent=None):
        super().__init__(parent=parent)


    def run(self):
        from videotrans.util.tools import set_process
        import videotrans
        try:
            url = f"https://pyvideotrans.com/version.json?version={videotrans.VERSION}&os={sys.platform}"
            res = requests.get(url)
            res.raise_for_status()
            d = res.json()
            if d['version_num'] > videotrans.VERSION_NUM:
                msg = f"{tr('newversion')}:{d['version']}"
                set_process(text=msg, type="check_soft_update")
        except Exception as e:
            pass
        return False
