

def openwin():
    import json
    import os
    from pathlib import Path
    from PySide6.QtCore import QThread, Signal, QUrl,QTimer
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QFileDialog
    from videotrans.util import contants
    from videotrans.configure import config
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
    from videotrans.util import tools
    RESULT_DIR = HOME_DIR + "/hunliu"


    class CompThread(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, videourls=None):
            super().__init__(parent=parent)
            self.videourls = videourls
            self.file = f'{RESULT_DIR}/{Path(self.videourls[0]).stem}-{Path(self.videourls[1]).stem}.wav'

        def post(self, type='logs', text=""):
            self.uito.emit(json.dumps({"type": type, "text": text}))

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
                self.post(type='error', text=str(e))
            else:
                self.post(type='ok', text=self.file)

    def feed(d):
        if winobj.has_done:
            return
        d = json.loads(d)
        if d['type'] == "error":
            winobj.has_done = True
            tools.show_error(d['text'])
            winobj.hun_startbtn.setText(tr("start operate"))
            winobj.hun_startbtn.setDisabled(False)
            winobj.hun_opendir.setDisabled(False)
        elif d['type'] == 'logs':
            winobj.hun_startbtn.setText(d['text'])
        else:
            winobj.has_done = True
            winobj.hun_startbtn.setText(tr("Ended/Start operate"))
            winobj.hun_startbtn.setDisabled(False)
            winobj.hun_out.setText(d['text'])
            winobj.hun_opendir.setDisabled(False)

    def get_file(num=1):
        format_str = " ".join(['*.' + f for f in contants.AUDIO_EXITS])
        fname, _ = QFileDialog.getOpenFileName(winobj, 'Select Audio', params.get('last_opendir',''),
                                               f"Audio files({format_str})")
        if not fname:
            return
        if num == 1:
            winobj.hun_file1.setText(fname.replace('\\', '/'))
        else:
            winobj.hun_file2.setText(fname.replace('\\', '/'))
        params['last_opendir'] = os.path.dirname(fname)

    def start():
        winobj.has_done = False
        audio1 = winobj.hun_file1.text()
        audio2 = winobj.hun_file2.text()
        if not audio1 or not audio2:
            tools.show_error(tr("必须选择视频"))
            return

        winobj.hun_startbtn.setText(
            tr("In Progress..."))
        winobj.hun_startbtn.setDisabled(True)
        winobj.hun_opendir.setDisabled(True)
        task = CompThread(parent=winobj, videourls=[audio1, audio2])
        task.uito.connect(feed)
        task.start()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    from videotrans.component.set_form import HunliuForm
    winobj = HunliuForm()
    app_cfg.child_forms['fn_hunliu'] = winobj
    winobj.show()
    def _bind():
        Path(RESULT_DIR).mkdir(parents=True,exist_ok=True)
        winobj.hun_file1btn.clicked.connect(lambda: get_file(1))
        winobj.hun_file2btn.clicked.connect(lambda: get_file(2))
        winobj.hun_opendir.clicked.connect(opendir)
        winobj.hun_startbtn.clicked.connect(start)
    QTimer.singleShot(10,_bind)
