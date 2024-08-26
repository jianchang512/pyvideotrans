import builtins
import json
import os
import threading
import time
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QFileDialog

from videotrans.configure import config
# 使用内置的 open 函数
from videotrans.util import tools

builtin_open = builtins.open


# 水印
def open():
    RESULT_DIR=config.homedir + "/watermark"
    Path(RESULT_DIR).mkdir(exist_ok=True)
    class CompThread(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, png=None, x=10, y=10, width=50, height=50, pos=0):
            super().__init__(parent=parent)
            self.png = png
            self.x = int(x)
            self.y = int(y)
            self.width = int(width)
            self.height = int(height)
            self.pos = int(pos)
            self.every_percent = 1 / len(config.waterform.videourls)
            self.percent = 0
            self.end = False

        def post(self,type='logs',text=""):
            self.uito.emit(json.dumps({"type":type,"text":text}))

        def hebing_pro(self, protxt, video_time):
            percent = 0
            while 1:
                if self.end or percent >= 100:
                    return
                if not os.path.exists(protxt):
                    time.sleep(1)
                    continue
                try:
                    content = Path(protxt).read_text(encoding='utf-8').strip().split("\n")
                except Exception:
                    continue
                if content[-1] == 'progress=end':
                    return
                idx = len(content) - 1
                end_time = "00:00:00"
                while idx > 0:
                    if content[idx].startswith('out_time='):
                        end_time = content[idx].split('=')[1].strip()
                        break
                    idx -= 1

                h, m, s = end_time.split(':')
                tmp1 = round((int(h) * 3600000 + int(m) * 60000 + int(s[:2]) * 1000) / video_time, 2)
                if percent + tmp1 < 99.9:
                    percent += tmp1
                self.percent += percent * self.every_percent / 100
                self.post(type='jd',text=f'{self.percent * 100}%')
                time.sleep(1)

        def run(self) -> None:
            os.chdir(RESULT_DIR)
            # 确保临时目录存在

            for video in config.waterform.videourls:
                result_file = RESULT_DIR + f'/{Path(video).stem}.mp4'

                # 计算水印位置
                duration = tools.get_video_duration(video)
                positions = [
                    f"{self.x}:{self.y}",  # 左上角
                    f"(w-overlay_w-{self.x}):{self.y}",  # 右上角
                    f"(w-overlay_w-{self.x}):(h-overlay_h-{self.y})",  # 右下角
                    f"{self.x}:(h-overlay_h-{self.y})",  # 左下角
                    f"(w-overlay_w)/2:(h-overlay_h)/2"  # 中心
                ]

                position = positions[self.pos]
                protxt = config.TEMP_HOME + f'/jd{time.time()}.txt'
                threading.Thread(target=self.hebing_pro, args=(protxt, duration,)).start()

                # 构建 FFmpeg 命令
                ffmpeg_command = [
                    "-y",
                    "-progress",
                    protxt,
                    "-i", os.path.normpath(video),
                    "-i", os.path.normpath(self.png),
                    "-filter_complex",
                    f"[1:v]scale={self.width}:{self.height}[overlay];[0:v][overlay]overlay={position}:enable='between(t,0,999999)'",
                    "-c:v", "libx264",
                    "-crf", f"{config.settings['crf']}",
                    "-preset", f"{config.settings['preset']}",
                    "-c:a", "aac",
                    "-pix_fmt", "yuv420p",
                    result_file
                ]
                try:
                    tools.runffmpeg(ffmpeg_command)
                except Exception as e:
                    self.post(type='error',text=f'{str(e)}')
                finally:
                    self.percent += self.every_percent
                self.post(type='jd',text=f'{self.percent * 100}%')
            self.post(type='ok',text='Ended')
            self.end = True

    def feed(d):
        d=json.loads(d)
        if d['type']=="error":
            QtWidgets.QMessageBox.critical(config.waterform, config.transobj['anerror'], d['text'])
            config.waterform.startbtn.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            config.waterform.startbtn.setDisabled(False)
            config.waterform.resultlabel.setText('')
        elif d['type']=='jd':
            config.waterform.startbtn.setText(d['text'])
        elif d['type']=='logs':
            config.waterform.resultlabel.setText(d['text'])
        else:
            config.waterform.startbtn.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            config.waterform.startbtn.setDisabled(False)
            config.waterform.resultlabel.setText(d['text'])
            config.waterform.resultbtn.setDisabled(False)

    def get_file(type):
        if type == 1:
            fname, _ = QFileDialog.getOpenFileNames(config.waterform, "Select Video",
                                                    config.params['last_opendir'],
                                                    "files(*.mp4 *.mov *.mkv *.avi *.mpeg)")
            if len(fname) > 0:
                config.waterform.videourls = [it.replace('file:///', '').replace('\\', '/') for it in fname]
                config.waterform.videourl.setText(",".join(config.waterform.videourls))
        else:
            fname, _ = QFileDialog.getOpenFileName(config.waterform, "Select Image",
                                                   config.params['last_opendir'],
                                                   "files(*.png *.jpg *.jpeg *.gif)")
            if fname:
                config.waterform.pngurl.setText(fname.replace('file:///', '').replace('\\', '/'))

    def start():
        png = config.waterform.pngurl.text()
        if len(config.waterform.videourls) < 1 or not png:
            QMessageBox.critical(config.waterform, config.transobj['anerror'],
                                 '必须选择视频和水印图片' if config.defaulelang == 'zh' else 'Must select video and watermark image')
            return

        config.waterform.startbtn.setText(
            '执行中...' if config.defaulelang == 'zh' else 'under implementation in progress...')
        config.waterform.startbtn.setDisabled(True)
        config.waterform.resultbtn.setDisabled(True)

        x, y = 10, 10
        try:
            x = int(config.waterform.linex.text())
        except Exception:
            pass
        try:
            y = int(config.waterform.liney.text())
        except Exception:
            pass
        w, h = 50, 50
        try:
            tmp_w = config.waterform.linew.text().strip().split('x')
            w, h = int(tmp_w[0]), int(tmp_w[1])
        except Exception:
            pass

        task = CompThread(parent=config.waterform, png=png, x=max(x, 0), y=max(y, 0),
                          width=max(w, 1), height=max(h, 1), pos=int(config.waterform.compos.currentIndex()))

        task.uito.connect(feed)
        task.start()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    from videotrans.component import WatermarkForm
    try:
        if config.waterform is not None:
            config.waterform.show()
            config.waterform.raise_()
            config.waterform.activateWindow()
            return
        config.waterform = WatermarkForm()
        config.waterform.videobtn.clicked.connect(lambda: get_file(1))
        config.waterform.pngbtn.clicked.connect(lambda: get_file(2))

        config.waterform.resultbtn.clicked.connect(opendir)
        config.waterform.startbtn.clicked.connect(start)
        config.waterform.show()
    except Exception:
        pass
