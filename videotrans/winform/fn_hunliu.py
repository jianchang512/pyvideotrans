import json
import os
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QFileDialog

from videotrans.configure import config
from videotrans.util import tools


def open():
    RESULT_DIR=config.homedir + "/hunliu"
    Path(RESULT_DIR).mkdir(exist_ok=True)
    class CompThread(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, videourls=[]):
            super().__init__(parent=parent)
            self.videourls = videourls
            self.file = f'{RESULT_DIR}/{Path(self.videourls[0]).stem}-{Path(self.videourls[1]).stem}.wav'
        def post(self,type='logs',text=""):
            self.uito.emit(json.dumps({"type":type,"text":text}))

        def run(self):
            try:
                tools.runffmpeg([
                    '-y',
                    '-i',
                    os.path.normpath(self.videourls[0]),
                    '-i',
                    os.path.normpath(self.videourls[1]),
                    '-filter_complex',
                    "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2",
                    '-ac',
                    '2',
                    self.file
                ])
            except Exception as e:
                self.post(type='error',text=str(e))
            else:
                self.post(type='ok',text=self.file)

    def feed(d):
        d=json.loads(d)
        if d['type']=="error":
            QtWidgets.QMessageBox.critical(config.hunliuform, config.transobj['anerror'], d['text'])
            config.hunliuform.hun_startbtn.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            config.hunliuform.hun_startbtn.setDisabled(False)
            config.hunliuform.hun_opendir.setDisabled(False)
        elif d['type']=='logs':
            config.hunliuform.hun_startbtn.setText(d['text'])
        else:
            config.hunliuform.hun_startbtn.setText('执行完成/开始执行' if config.defaulelang == 'zh' else 'Ended/Start operate')
            config.hunliuform.hun_startbtn.setDisabled(False)
            config.hunliuform.hun_out.setText(d['text'])
            config.hunliuform.hun_opendir.setDisabled(False)

    def get_file(num=1):
        fname, _ = QFileDialog.getOpenFileName(config.hunliuform, 'Select Audio', config.params['last_opendir'], "Audio files(*.mp3 *.wav *.m4a *.flac *.aac)")
        if not fname:
            return
        if num == 1:
            config.hunliuform.hun_file1.setText(fname.replace('\\', '/'))
        else:
            config.hunliuform.hun_file2.setText(fname.replace('\\', '/'))
        config.params['last_opendir'] = os.path.dirname(fname)

    def start():
        audio1 = config.hunliuform.hun_file1.text()
        audio2 = config.hunliuform.hun_file2.text()
        if not audio1 or not audio2:
            QMessageBox.critical(config.hunliuform, config.transobj['anerror'],
                                 '必须选择音频1和音频2' if config.defaulelang == 'zh' else '必须选择视频')
            return

        config.hunliuform.hun_startbtn.setText(
            '执行中...' if config.defaulelang == 'zh' else 'In Progress...')
        config.hunliuform.hun_startbtn.setDisabled(True)
        config.hunliuform.hun_opendir.setDisabled(True)
        task = CompThread(parent=config.hunliuform, videourls=[audio1, audio2])
        task.uito.connect(feed)
        task.start()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    from videotrans.component import HunliuForm
    try:
        if config.hunliuform is not None:
            config.hunliuform.show()
            config.hunliuform.raise_()
            config.hunliuform.activateWindow()
            return
        config.hunliuform = HunliuForm()
        config.hunliuform.hun_file1btn.clicked.connect(lambda: get_file(1))
        config.hunliuform.hun_file2btn.clicked.connect(lambda: get_file(2))
        config.hunliuform.hun_opendir.clicked.connect(opendir)
        config.hunliuform.hun_startbtn.clicked.connect(start)
        config.hunliuform.show()
    except Exception as e:
        print(e)
