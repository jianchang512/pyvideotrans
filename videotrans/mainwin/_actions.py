from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import QFileDialog

from videotrans.configure.config import tr, params, app_cfg
from videotrans.mainwin._actions_base import WinActionBase
from videotrans.util.help_misc import show_error

from ._actions_check import WinActionCheckMixin
from ._actions_config import WinActionConfigMixin
from ._actions_task import WinActionTaskMixin


@dataclass
class WinAction(WinActionCheckMixin, WinActionConfigMixin, WinActionTaskMixin, WinActionBase):

    def _reset(self):
        self.obj_list = []
        self.main.source_mp4.setText(tr("No select videos"))

    def delete_process(self):
        for i in range(self.main.processlayout.count()):
            item = self.main.processlayout.itemAt(i)
            if item.widget():
                try:
                    item.widget().deleteLater()
                except Exception:
                    pass
        self.processbtns = {}

    def set_djs_timeout(self):
        app_cfg.set_countdown(-1)
        if self.had_click_btn:
            return
        self.had_click_btn = True
        self.main.subtitle_area.setReadOnly(True)
        self.had_click_btn = False

    def import_sub_fun(self):
        fname, _ = QFileDialog.getOpenFileName(self.main, tr('selectmp4'), params.get('last_opendir', ''),
                                               "Srt files(*.srt *.txt)")
        if not fname: return
        content = ""
        try:
            content = Path(fname).read_text(encoding='utf-8')
        except UnicodeError:
            content = Path(fname).read_text(encoding='gbk')

        if content:
            self.main.subtitle_area.clear()
            self.main.subtitle_area.insertPlainText(content.strip())
        else:
            return show_error(tr('import src error'))
