import json
import os
import shutil
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QFileDialog

from videotrans.configure import config
from videotrans.util import tools


# 音视频格式转换
def open():
    RESULT_DIR = config.HOME_DIR + "/subtitlescover"
    Path(RESULT_DIR).mkdir(exist_ok=True)

    class CompThread(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, subtitlefiles=None, target_format=""):
            super().__init__(parent=parent)
            self.subtitlefiles = subtitlefiles
            self.target_format = target_format.lower()

        def post(self, type='logs', text=""):
            self.uito.emit(json.dumps({"type": type, "text": text}))

        def run(self):
            try:
                for i, v in enumerate(self.subtitlefiles):
                    raw_path = Path(v)
                    # 格式不变直接复制
                    if raw_path.suffix.lower() == self.target_format:
                        shutil.copy2(self.subtitlefiles, RESULT_DIR + f'/{raw_path.name}')
                        continue
                    tools.runffmpeg([
                        "-y",
                        "-i",
                        os.path.normpath(v),
                        RESULT_DIR + f"/{Path(v).stem}.{self.target_format}"
                    ])
                    jd = round((i + 1) * 100 / len(self.subtitlefiles), 2)
                    self.post(type='jd', text=f'{jd}%')
            except Exception as e:
                self.post(type='error', text=str(e))
            else:
                self.post(type="ok", text='Ended')

    def feed(d):
        d = json.loads(d)
        if d['type'] == "error":
            QtWidgets.QMessageBox.critical(subtitlescoverform, config.transobj['anerror'], d['text'])
            subtitlescoverform.startbtn.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            subtitlescoverform.startbtn.setDisabled(False)
            subtitlescoverform.opendir.setDisabled(False)
        elif d['type'] == 'jd' or d['type'] == 'logs':
            subtitlescoverform.startbtn.setText(d['text'])
        else:
            subtitlescoverform.startbtn.setText(config.transobj['zhixingwc'])
            subtitlescoverform.startbtn.setDisabled(False)
            subtitlescoverform.opendir.setDisabled(False)
            subtitlescoverform.subtitlefiles = []

    def get_file():
        fnames, _ = QFileDialog.getOpenFileNames(subtitlescoverform, config.transobj['selectmp4'],
                                                 config.params['last_opendir'], "Subtitles files(*.srt *.vtt *.ass)")
        if len(fnames) < 1:
            return
        subtitlescoverform.subtitlefiles = []
        for it in fnames:
            subtitlescoverform.subtitlefiles.append(it.replace('\\', '/'))

        if len(subtitlescoverform.subtitlefiles) > 0:
            config.params['last_opendir'] = os.path.dirname(fnames[0])
            subtitlescoverform.pathdir.setText(",".join(subtitlescoverform.subtitlefiles))

    def start():
        if len(subtitlescoverform.subtitlefiles) < 1:
            QMessageBox.critical(subtitlescoverform, config.transobj['anerror'],
                                 '必须选择字幕文件' if config.defaulelang == 'zh' else 'Must select subtitles ')
            return

        subtitlescoverform.startbtn.setText(
            '执行中...' if config.defaulelang == 'zh' else 'under implementation in progress...')
        subtitlescoverform.startbtn.setDisabled(True)
        subtitlescoverform.opendir.setDisabled(True)
        target_format = subtitlescoverform.formatlist.currentText()
        task = CompThread(parent=subtitlescoverform, subtitlefiles=subtitlescoverform.subtitlefiles,
                          target_format=target_format)
        task.uito.connect(feed)
        task.start()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    from videotrans.component import SubtitlescoverForm
    try:
        subtitlescoverform = config.child_forms.get('subtitlescoverform')
        if subtitlescoverform is not None:
            subtitlescoverform.show()
            subtitlescoverform.raise_()
            subtitlescoverform.activateWindow()
            return
        subtitlescoverform = SubtitlescoverForm()
        config.child_forms['subtitlescoverform'] = subtitlescoverform
        subtitlescoverform.selectbtn.clicked.connect(lambda: get_file())
        subtitlescoverform.opendir.clicked.connect(opendir)
        subtitlescoverform.startbtn.clicked.connect(start)
        subtitlescoverform.show()
    except Exception:
        pass
