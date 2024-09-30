import json
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QFileDialog

from videotrans.configure import config
from videotrans.util import tools


# 合并2个srt
def openwin():
    RESULT_DIR = config.HOME_DIR + "/Mergersrt"
    Path(RESULT_DIR).mkdir(exist_ok=True)

    class CompThread(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, file1=None, file2=None):
            super().__init__(parent=parent)
            self.file1 = file1
            self.file2 = file2
            self.result_file = RESULT_DIR + "/" + Path(file1).stem + '-add-' + Path(file2).stem + '.srt'

        def post(self, type='logs', text=""):
            self.uito.emit(json.dumps({"type": type, "text": text}))

        def run(self):
            try:
                text = ""
                srt1_list = tools.get_subtitle_from_srt(self.file1)
                srt2_list = tools.get_subtitle_from_srt(self.file2)
                srt2_len = len(srt2_list)
                for i, it in enumerate(srt1_list):
                    text += f"{it['line']}\n{it['time']}\n{it['text'].strip()}"
                    if i < srt2_len:
                        text += f"\n{srt2_list[i]['text'].strip()}"
                    text += "\n\n"
                with Path(self.result_file).open('w', encoding='utf-8') as f:
                    f.write(text.strip())
                    f.flush()
                self.post(type='ok', text=self.result_file)
            except Exception as e:
                self.post(type='error', text=str(e))

    def feed(d):
        if winobj.has_done:
            return
        d = json.loads(d)
        if d['type'] == "error":
            winobj.has_done = True
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d['text'])
        elif d['type'] == 'logs':
            winobj.startbtn.setText(d['text'])
        else:
            winobj.has_done = True
            winobj.startbtn.setText('开始执行合并' if config.defaulelang == 'zh' else 'commencement of execution')
            winobj.startbtn.setDisabled(False)
            winobj.resultlabel.setText(d['text'])
            winobj.resultbtn.setDisabled(False)
            winobj.resultinput.setPlainText(Path(winobj.resultlabel.text()).read_text(encoding='utf-8'))

    def get_file(inputname):
        fname, _ = QFileDialog.getOpenFileName(winobj, "Select subtitles srt", config.params['last_opendir'],
                                               "files(*.srt)")
        if fname:
            if inputname == 1:
                winobj.srtinput1.setText(fname.replace('file:///', '').replace('\\', '/'))
            else:
                winobj.srtinput2.setText(fname.replace('file:///', '').replace('\\', '/'))

    def start():
        winobj.has_done = False
        srt1 = winobj.srtinput1.text()
        srt2 = winobj.srtinput2.text()
        if not srt1 or not srt2:
            QMessageBox.critical(winobj, config.transobj['anerror'],
                                 '必须选择字幕文件1和字幕文件2' if config.defaulelang == 'zh' else 'Subtitle File 1 and Subtitle File 2 must be selected')
            return

        winobj.startbtn.setText('执行合并中...' if config.defaulelang == 'zh' else 'Consolidation in progress...')
        winobj.startbtn.setDisabled(True)
        winobj.resultbtn.setDisabled(True)
        winobj.resultinput.setPlainText("")

        task = CompThread(parent=winobj, file1=srt1, file2=srt2)

        task.uito.connect(feed)
        task.start()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    from videotrans.component import HebingsrtForm
    try:
        winobj = config.child_forms.get('hebingw')
        if winobj is not None:
            winobj.show()
            winobj.raise_()
            winobj.activateWindow()
            return
        winobj = HebingsrtForm()
        config.child_forms['hebingw'] = winobj
        winobj.srtbtn1.clicked.connect(lambda: get_file(1))
        winobj.srtbtn2.clicked.connect(lambda: get_file(2))

        winobj.resultbtn.clicked.connect(opendir)
        winobj.startbtn.clicked.connect(start)
        winobj.show()
    except Exception:
        pass
