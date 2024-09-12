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


# 水印
def openwin():
    RESULT_DIR = config.HOME_DIR + "/watermark"
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
            self.every_percent = 1 / len(winobj.videourls)
            self.percent = 0
            self.end = False

        def post(self, type='logs', text=""):
            self.uito.emit(json.dumps({"type": type, "text": text}))

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
                self.post(type='jd', text=f'{self.percent * 100}%')
                time.sleep(1)

        def run(self) -> None:
            os.chdir(RESULT_DIR)
            # 确保临时目录存在

            for video in winobj.videourls:
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
                    self.post(type='error', text=f'{str(e)}')
                finally:
                    self.percent += self.every_percent
                self.post(type='jd', text=f'{self.percent * 100}%')
            self.post(type='ok', text='Ended')
            self.end = True

    def feed(d):
        if winobj.has_done:
            return
        d = json.loads(d)
        if d['type'] == "error":
            winobj.has_done = True
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d['text'])
            winobj.startbtn.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            winobj.startbtn.setDisabled(False)
            winobj.resultlabel.setText('')
        elif d['type'] == 'jd':
            winobj.startbtn.setText(d['text'])
        elif d['type'] == 'logs':
            winobj.resultlabel.setText(d['text'])
        else:
            winobj.has_done = True
            winobj.startbtn.setText(config.transobj['zhixingwc'])
            winobj.startbtn.setDisabled(False)
            winobj.resultlabel.setText(config.transobj['quanbuend'])
            winobj.resultbtn.setDisabled(False)

    def get_file(type):
        if type == 1:
            format_str = " ".join(['*.' + f for f in config.VIDEO_EXTS])
            fname, _ = QFileDialog.getOpenFileNames(winobj, "Select Video",
                                                    config.params['last_opendir'],
                                                    f"Video files({format_str})")
            if len(fname) > 0:
                winobj.videourls = [it.replace('file:///', '').replace('\\', '/') for it in fname]
                winobj.videourl.setText(",".join(winobj.videourls))
        else:
            fname, _ = QFileDialog.getOpenFileName(winobj, "Select Image",
                                                   config.params['last_opendir'],
                                                   "files(*.png *.jpg *.jpeg *.gif)")
            if fname:
                winobj.pngurl.setText(fname.replace('file:///', '').replace('\\', '/'))

    def start():
        winobj.has_done = False
        png = winobj.pngurl.text()
        if len(winobj.videourls) < 1 or not png:
            QMessageBox.critical(winobj, config.transobj['anerror'],
                                 '必须选择视频和水印图片' if config.defaulelang == 'zh' else 'Must select video and watermark image')
            return

        winobj.startbtn.setText(
            '执行中...' if config.defaulelang == 'zh' else 'under implementation in progress...')
        winobj.startbtn.setDisabled(True)
        winobj.resultbtn.setDisabled(True)

        x, y = 10, 10
        try:
            x = int(winobj.linex.text())
        except Exception:
            pass
        try:
            y = int(winobj.liney.text())
        except Exception:
            pass
        w, h = 50, 50
        try:
            tmp_w = winobj.linew.text().strip().split('x')
            w, h = int(tmp_w[0]), int(tmp_w[1])
        except Exception:
            pass

        task = CompThread(parent=winobj, png=png, x=max(x, 0), y=max(y, 0),
                          width=max(w, 1), height=max(h, 1), pos=int(winobj.compos.currentIndex()))

        task.uito.connect(feed)
        task.start()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    from videotrans.component import WatermarkForm
    try:
        winobj = config.child_forms.get('waterform')
        if winobj is not None:
            winobj.show()
            winobj.raise_()
            winobj.activateWindow()
            return
        winobj = WatermarkForm()
        config.child_forms['waterform'] = winobj

        winobj.videobtn.clicked.connect(lambda: get_file(1))
        winobj.pngbtn.clicked.connect(lambda: get_file(2))

        winobj.resultbtn.clicked.connect(opendir)
        winobj.startbtn.clicked.connect(start)
        winobj.show()
    except Exception:
        pass
