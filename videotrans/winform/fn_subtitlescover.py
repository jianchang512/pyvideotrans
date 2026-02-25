def openwin():
    import json
    import os
    import shutil
    import time
    from pathlib import Path
    from PySide6.QtCore import QThread, Signal, QUrl,QTimer
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QFileDialog

    from videotrans.configure import config
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
    from videotrans.util import tools
    RESULT_DIR = HOME_DIR + "/subtitlescover"


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
                    if self.target_format == 'txt':
                        if raw_path.name.lower().endswith('.srt'):
                            srt_list = tools.get_subtitle_from_srt(v, is_file=True)
                        else:
                            tmp_srt = TEMP_DIR + f'/{time.time()}.srt'
                            tools.runffmpeg([
                                "-y",
                                "-i",
                                os.path.normpath(v),
                                tmp_srt
                            ])
                            srt_list = tools.get_subtitle_from_srt(tmp_srt, is_file=True)
                        txt_list = []
                        for srt in srt_list:
                            txt_list.append(srt['text'])
                        with open(RESULT_DIR + f"/{Path(v).stem}.{self.target_format}", 'w', encoding='utf-8') as f:
                            f.write("\n".join(txt_list))
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
                from videotrans.configure._except import get_msg_from_except
                self.post(type='error', text=get_msg_from_except(e))
            else:
                self.post(type="ok", text='Ended')

    def feed(d):
        if winobj.has_done:
            return
        d = json.loads(d)
        if d['type'] == "error":
            winobj.has_done = True
            tools.show_error(d['text'])
            winobj.startbtn.setText(tr("start operate"))
            winobj.startbtn.setDisabled(False)
            winobj.opendir.setDisabled(False)
        elif d['type'] == 'jd' or d['type'] == 'logs':
            winobj.startbtn.setText(d['text'])
        else:
            winobj.has_done = True
            winobj.startbtn.setText(tr('zhixingwc'))
            winobj.startbtn.setDisabled(False)
            winobj.opendir.setDisabled(False)
            winobj.subtitlefiles = []

    def get_file():
        fnames, _ = QFileDialog.getOpenFileNames(winobj, tr('selectmp4'),
                                                 params.get('last_opendir',''), "Subtitles files(*.srt *.vtt *.ass)")
        if len(fnames) < 1:
            return
        winobj.subtitlefiles = []
        for it in fnames:
            winobj.subtitlefiles.append(it.replace('\\', '/'))

        if len(winobj.subtitlefiles) > 0:
            params['last_opendir'] = os.path.dirname(fnames[0])
            winobj.pathdir.setText(",".join(winobj.subtitlefiles))

    def start():
        if len(winobj.subtitlefiles) < 1:
            tools.show_error(tr("Must select subtitles"))
            return
        winobj.has_done = False

        winobj.startbtn.setText(
            tr("under implementation in progress..."))
        winobj.startbtn.setDisabled(True)
        winobj.opendir.setDisabled(True)
        target_format = winobj.formatlist.currentText()
        task = CompThread(parent=winobj, subtitlefiles=winobj.subtitlefiles,
                          target_format=target_format)
        task.uito.connect(feed)
        task.start()
        params['subtitlecover_outformat']=target_format
        params.save()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    from videotrans.component.set_form import SubtitlescoverForm
    winobj = SubtitlescoverForm()
    app_cfg.child_forms['fn_subtitlescover'] = winobj
    winobj.show()
    def _bind():
        Path(RESULT_DIR).mkdir(parents=True,exist_ok=True)
        winobj.selectbtn.clicked.connect(lambda: get_file())
        winobj.opendir.clicked.connect(opendir)
        winobj.startbtn.clicked.connect(start)
        winobj.formatlist.setCurrentText(params.get('subtitlecover_outformat','srt'))
    QTimer.singleShot(10,_bind)

