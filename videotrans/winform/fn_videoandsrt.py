import json
import os
import textwrap
import time
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QFileDialog

from videotrans import translator
from videotrans.configure import config
from videotrans.util import tools


# 视频 字幕 音频 合并
def open():
    RESULT_DIR = config.HOME_DIR + "/videoandsrt"
    Path(RESULT_DIR).mkdir(exist_ok=True)

    class CompThread(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, folder=None,
                     is_soft=False, language=None, maxlen=30):
            super().__init__(parent=parent)
            self.is_soft = is_soft
            self.language = language
            self.maxlen = maxlen
            self.folder = folder

        def post(self, type='logs', text=""):
            self.uito.emit(json.dumps({"type": type, "text": text}))

        # 取出具有相同名称的视频和音频文件，组装为dict待处理
        def get_list(self):
            videos = {}
            srts = {}
            for it in Path(self.folder).iterdir():
                if it.is_file():
                    suffix = it.suffix.lower()
                    if suffix in config.VIDEO_EXTS:
                        videos[it.stem] = it.resolve().as_posix()
                    elif suffix in ['.srt']:
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
                          text='不存在同名视频和srt字幕，无法合并' if config.defaulelang == 'zh' else 'Video and srt of the same name do not exist and cannot be merged')
                return
            percent = 0
            self.post(type='logs',
                      text=f'有{length}组同名视频和srt字幕需合并' if config.defaulelang == 'zh' else f'There are {length} sets of videos with the same name and srt subtitles that need to be merged.')
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
                    if not self.is_soft or not self.language:
                        # 硬字幕
                        sub_list = tools.get_subtitle_from_srt(srt, is_file=True)
                        text = ""
                        for i, it in enumerate(sub_list):
                            it['text'] = textwrap.fill(it['text'], self.maxlen, replace_whitespace=False).strip()
                            text += f"{it['line']}\n{it['time']}\n{it['text'].strip()}\n\n"
                        srtfile = config.TEMP_HOME + f"/srt{time.time()}.srt"
                        Path(srtfile).write_text(text, encoding='utf-8')
                        assfile = tools.set_ass_font(srtfile)
                        os.chdir(config.TEMP_HOME)
                        cmd += [
                            '-c:v',
                            'libx264',
                            '-vf',
                            f"subtitles={os.path.basename(assfile)}",
                            '-crf',
                            f'{config.settings["crf"]}',
                            '-preset',
                            config.settings['preset']
                        ]
                    else:
                        # 软字幕
                        os.chdir(self.folder)
                        subtitle_language = translator.get_subtitle_code(
                            show_target=self.language)
                        cmd += [
                            '-i',
                            os.path.basename(srt),
                            '-c:v',
                            'copy' if Path(info['video']).suffix.lower() == '.mp4' else 'libx264',
                            "-c:s",
                            "mov_text",
                            "-metadata:s:s:0",
                            f"language={subtitle_language}"
                        ]
                    cmd.append(result_file)
                    tools.runffmpeg(cmd)
                except Exception as e:
                    print(e)
                    self.post(type='error', text=str(e))
                    return
                finally:
                    percent += round(100 / length, 2)
                    self.post(type='jd', text=f'{percent if percent <= 100 else 99}%')
            self.post(type='ok', text='执行完成' if config.defaulelang == 'zh' else 'Ended')

    def feed(d):
        d = json.loads(d)
        if d['type'] == "error":
            QtWidgets.QMessageBox.critical(vandsrtform, config.transobj['anerror'], d['text'])
            vandsrtform.startbtn.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            vandsrtform.startbtn.setDisabled(False)
            vandsrtform.opendir.setDisabled(False)
        elif d['type'] == 'jd':
            vandsrtform.startbtn.setText(d['text'])
        elif d['type'] == 'logs':
            vandsrtform.loglabel.setText(d['text'])
        else:
            vandsrtform.startbtn.setText(config.transobj['zhixingwc'])
            vandsrtform.startbtn.setDisabled(False)
            vandsrtform.loglabel.setText(config.transobj['quanbuend'])
            vandsrtform.opendir.setDisabled(False)

    def get_file():
        dirname = QFileDialog.getExistingDirectory(vandsrtform, config.transobj['selectsavedir'],
                                                   config.params['last_opendir'])
        vandsrtform.folder.setText(dirname.replace('\\', '/'))

    def start():
        folder = vandsrtform.folder.text()
        if not folder or not Path(folder).exists() or not Path(folder).is_dir():
            QMessageBox.critical(vandsrtform, config.transobj['anerror'],
                                 '必须选择存在同名视频和srt字幕的文件夹' if config.defaulelang == 'zh' else 'You must select the folder where the video and srt subtitles with the same name exists.')
            return
        is_soft = vandsrtform.issoft.isChecked()
        language = vandsrtform.language.currentText()
        maxlen = 30
        try:
            maxlen = int(vandsrtform.maxlen.text())
        except Exception:
            pass

        vandsrtform.startbtn.setText(
            '执行中...' if config.defaulelang == 'zh' else 'In Progress...')
        vandsrtform.startbtn.setDisabled(True)
        vandsrtform.opendir.setDisabled(True)
        task = CompThread(parent=vandsrtform,
                          folder=folder,
                          is_soft=is_soft,
                          language=language,
                          maxlen=maxlen
                          )
        task.uito.connect(feed)
        task.start()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    from videotrans.component import Videoandsrtform
    try:
        vandsrtform = config.child_forms.get('vandsrtform')
        if vandsrtform is not None:
            vandsrtform.show()
            vandsrtform.raise_()
            vandsrtform.activateWindow()
            return
        vandsrtform = Videoandsrtform()
        config.child_forms['vandsrtform'] = vandsrtform
        vandsrtform.folder_btn.clicked.connect(get_file)
        vandsrtform.startbtn.clicked.connect(start)
        vandsrtform.opendir.clicked.connect(opendir)
        vandsrtform.show()
    except Exception as e:
        print(e)
