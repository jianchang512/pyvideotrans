# 视频 字幕 音频 合并


def openwin():
    import json
    import os
    import time
    from pathlib import Path
    from PySide6.QtCore import QThread, Signal, QUrl,QTimer
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QFileDialog

    from videotrans.util import contants
    from videotrans.configure import config
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
    from videotrans.util import tools
    RESULT_DIR = HOME_DIR + "/videoandsrt"

    from videotrans import translator

    class CompThread(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, folder=None,
                     is_soft=False, language=None, maxlen=30,remain_hr=False):
            super().__init__(parent=parent)
            self.is_soft = is_soft
            self.language = language
            self.maxlen = maxlen
            self.folder = folder
            self.remain_hr=remain_hr

        def post(self, type='logs', text=""):
            self.uito.emit(json.dumps({"type": type, "text": text}))

        # 取出具有相同名称的视频和音频文件，组装为dict待处理
        def get_list(self):
            videos = {}
            srts = {}
            for it in Path(self.folder).iterdir():
                if it.is_file():
                    suffix = it.suffix.lower()[1:]
                    if suffix in contants.VIDEO_EXTS:
                        videos[it.stem] = it.resolve().as_posix()
                    elif suffix == 'srt':
                        srts[it.stem] = it.resolve().as_posix()
            vailfiles = {}
            for key, val in videos.items():
                if key in srts:
                    vailfiles[key] = {"video": val, "srt": srts[key]}
            length = len(vailfiles.keys())
            if length < 1:
                return None, 0
            return vailfiles, length

        def run(self):
            vailfiles, length = self.get_list()
            if not vailfiles:
                self.post(type='error',
                          text=tr("Video and srt of the same name do not exist and cannot be merged"))
                return
            percent = 0
            self.post(type='logs',
                      text=tr('There are {} sets of videos with the same name and srt subtitles that need to be merged.',length))
            for name, info in vailfiles.items():
                try:
                    srt = info['srt']
                    self.post(type='logs', text=f'{Path(srt).name} --> {Path(info["video"]).name} ')
                    result_file = RESULT_DIR + f'/{name}.mp4'
                    cmd = [
                        '-y',
                        '-i',
                        os.path.normpath(info['video'])
                    ]
                    sub_list = tools.get_subtitle_from_srt(srt, is_file=True)
                    text = ""
                    for i, it in enumerate(sub_list):
                        if self.remain_hr:
                            txt_list = []
                            for txt_line in it['text'].strip().split("\n"):
                                txt_list.append(tools.textwrap(txt_line.strip(), self.maxlen))
                            text+= "\n".join(txt_list)
                        else:
                            it['text'] = tools.textwrap(it['text'], self.maxlen).strip()
                            text += f"{it['line']}\n{it['time']}\n{it['text'].strip()}\n\n"
                    srtfile = TEMP_DIR + f"/srt{time.time()}.srt"
                    with Path(srtfile).open('w', encoding='utf-8') as f:
                        f.write(text)
                    os.chdir(TEMP_DIR)
                    if not self.is_soft or not self.language:
                        # 硬字幕
                        assfile = tools.set_ass_font(srtfile)
                        cmd += [
                            '-c:v',
                            'libx265',
                            '-vf',
                            f"subtitles={os.path.basename(assfile)}",
                            '-crf',
                            f'{settings.get("crf",26)}',
                            '-preset',
                            settings.get('preset','fast')
                        ]
                    else:
                        # 软字幕
                        subtitle_language = translator.get_subtitle_code(
                            show_target=self.language)
                        cmd += [
                            '-i',
                            srtfile,
                            '-c:v',
                            'copy' if Path(info['video']).suffix.lower() == '.mp4' else 'libx265',
                            "-c:s",
                            "mov_text",
                            "-metadata:s:s:0",
                            f"language={subtitle_language}"
                        ]
                    cmd.append(result_file)
                    tools.runffmpeg(cmd,force_cpu=False)
                except Exception as e:
                    print(e)
                    self.post(type='error', text=str(e))
                    return
                finally:
                    percent += round(100 / length, 2)
                    self.post(type='jd', text=f'{percent if percent <= 100 else 99}%')
            self.post(type='ok', text=tr("Ended"))

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
        elif d['type'] == 'jd':
            winobj.startbtn.setText(d['text'])
        elif d['type'] == 'logs':
            winobj.loglabel.setText(d['text'])
        else:
            winobj.has_done = True
            winobj.startbtn.setText(tr('zhixingwc'))
            winobj.startbtn.setDisabled(False)
            winobj.loglabel.setText(tr('quanbuend'))
            winobj.opendir.setDisabled(False)

    def get_file():
        dirname = QFileDialog.getExistingDirectory(winobj, tr('selectsavedir'),
                                                   params.get('last_opendir',''))
        winobj.folder.setText(dirname.replace('\\', '/'))

    def start():
        winobj.has_done = False
        folder = winobj.folder.text()
        if not folder or not Path(folder).exists() or not Path(folder).is_dir():
            tools.show_error(
                tr("You must select the folder where the video and srt subtitles with the same name exists."))
            return
        is_soft = winobj.issoft.isChecked()
        language = winobj.language.currentText()
        maxlen = 30
        try:
            maxlen = int(winobj.maxlen.text())
        except ValueError:
            pass

        winobj.startbtn.setText(
            tr("In Progress..."))
        winobj.startbtn.setDisabled(True)
        winobj.opendir.setDisabled(True)
        task = CompThread(parent=winobj,
                          folder=folder,
                          is_soft=is_soft,
                          language=language,
                          maxlen=maxlen,
                          remain_hr=winobj.remain_hr.isChecked()
        )
        task.uito.connect(feed)
        task.start()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    def _open_ass():
        from videotrans.component.set_ass import ASSStyleDialog
        dialog = ASSStyleDialog()
        dialog.exec()

    from videotrans.component.set_form import Videoandsrtform
    from videotrans.translator import LANGNAME_DICT
    winobj = Videoandsrtform()
    app_cfg.child_forms['fn_videoandsrt'] = winobj
    winobj.show()

    def _bind():
        Path(RESULT_DIR).mkdir(parents=True,exist_ok=True)
        winobj.folder_btn.clicked.connect(get_file)
        winobj.startbtn.clicked.connect(start)
        winobj.opendir.clicked.connect(opendir)
        winobj.language.addItems(list(LANGNAME_DICT.values()))
        winobj.set_ass.clicked.connect(_open_ass)

    QTimer.singleShot(10,_bind)