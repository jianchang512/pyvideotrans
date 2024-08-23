import os
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QFileDialog

from videotrans.configure import config
from videotrans.util import tools


# 合并2个srt
def open():
    class CompThread(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, file1=None, file2=None):
            super().__init__(parent=parent)
            self.file1 = file1
            self.file2 = file2
            self.result_dir = config.homedir + "/Mergersrt"
            os.makedirs(self.result_dir, exist_ok=True)
            self.result_file = self.result_dir + "/" + os.path.splitext(os.path.basename(file1))[0] + '-plus-' + \
                               os.path.splitext(os.path.basename(file2))[0] + '.srt'

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
                Path(self.result_file).write_text(text.strip(),encoding="utf-8", errors="ignore")
                self.uito.emit(self.result_file)
            except Exception as e:
                self.uito.emit('error:' + str(e))

    def feed(d):
        if d.startswith("error:"):
            QtWidgets.QMessageBox.critical(config.hebingw, config.transobj['anerror'], d)
        else:
            config.hebingw.startbtn.setText('开始执行合并' if config.defaulelang == 'zh' else 'commencement of execution')
            config.hebingw.startbtn.setDisabled(False)
            config.hebingw.resultlabel.setText(d)
            config.hebingw.resultbtn.setDisabled(False)
            config.hebingw.resultinput.setPlainText(Path(config.hebingw.resultlabel.text()).read_text(encoding='utf-8'))

    def get_file(inputname):
        fname, _ = QFileDialog.getOpenFileName(config.hebingw, "Select subtitles srt", config.params['last_opendir'],
                                               "files(*.srt)")
        if fname:
            if inputname == 1:
                config.hebingw.srtinput1.setText(fname.replace('file:///', '').replace('\\', '/'))
            else:
                config.hebingw.srtinput2.setText(fname.replace('file:///', '').replace('\\', '/'))

    def start():
        # 开始处理分离，判断是否选择了源文件
        srt1 = config.hebingw.srtinput1.text()
        srt2 = config.hebingw.srtinput2.text()
        if not srt1 or not srt2:
            QMessageBox.critical(config.hebingw, config.transobj['anerror'],
                                 '必须选择字幕文件1和字幕文件2' if config.defaulelang == 'zh' else 'Subtitle File 1 and Subtitle File 2 must be selected')
            return

        config.hebingw.startbtn.setText('执行合并中...' if config.defaulelang == 'zh' else 'Consolidation in progress...')
        config.hebingw.startbtn.setDisabled(True)
        config.hebingw.resultbtn.setDisabled(True)
        config.hebingw.resultinput.setPlainText("")

        task = CompThread(parent=config.hebingw, file1=srt1, file2=srt2)

        task.uito.connect(feed)
        task.start()

    def opendir():
        filepath = config.hebingw.resultlabel.text()
        if not filepath:
            return QMessageBox.critical(config.hebingw, config.transobj['anerror'],
                                        '尚未生成合并字幕' if config.defaulelang == 'zh' else 'Combined subtitles not yet generated')
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(filepath)))

    from videotrans.component import HebingsrtForm
    try:
        if config.hebingw is not None:
            config.hebingw.show()
            config.hebingw.raise_()
            config.hebingw.activateWindow()
            return
        config.hebingw = HebingsrtForm()
        config.hebingw.srtbtn1.clicked.connect(lambda: get_file(1))
        config.hebingw.srtbtn2.clicked.connect(lambda: get_file(2))

        config.hebingw.resultbtn.clicked.connect(opendir)
        config.hebingw.startbtn.clicked.connect(start)
        config.hebingw.show()
    except Exception:
        pass