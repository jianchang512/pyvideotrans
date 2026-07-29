from dataclasses import dataclass

from videotrans.configure.config import tr, params, app_cfg
from videotrans.mainwin._actions_base import WinActionBase


from ._actions_check import WinActionCheckMixin
from ._actions_config import WinActionConfigMixin
from ._actions_task import WinActionTaskMixin


@dataclass
class WinAction(WinActionCheckMixin, WinActionConfigMixin, WinActionTaskMixin, WinActionBase):

    def _reset(self):
        self.obj_list = []
        self.queue_mp4=[]
        self.retry_queue_mp4=[]
        self.main.source_mp4.setText(tr("No select videos"))

    def delete_process(self):
        def _del_item(wd):
            if wd.widget():
                try:
                    wd.widget().deleteLater()
                except Exception:
                    pass
            elif wd.layout():
                layout=wd.layout()
                for j in range(layout.count()):
                    return _del_item(layout.itemAt(j))

        for i in range(self.main.processlayout.count()):
            _del_item(self.main.processlayout.itemAt(i))
        self.processbtns = {}
        self.delbtns = {}

    def set_djs_timeout(self):
        app_cfg.set_countdown(-1)
        if self.had_click_btn:
            return

