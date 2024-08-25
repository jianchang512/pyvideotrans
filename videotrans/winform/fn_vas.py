import os
import textwrap
import threading
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
    class CompThread(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, video=None, audio=None, srt=None, saveraw=True,is_soft=False,language=None,maxlen=30):
            super().__init__(parent=parent)
            self.resultdir = config.homedir + "/vas"
            os.makedirs(self.resultdir, exist_ok=True)
            self.video = video
            self.audio = audio
            self.srt = srt
            self.saveraw = saveraw
            self.is_soft=is_soft
            self.language=language
            self.maxlen=maxlen
            print(f'{saveraw=}')
            self.file = f'{self.resultdir}/{Path(self.video).stem}-{int(time.time())}.mp4'
            self.video_info = tools.get_video_info(self.video)
            self.video_time = tools.get_video_duration(self.video)

        def hebing_pro(self, protxt, video_time):
            percent = 0
            while 1:
                if percent >= 100:
                    return
                if not os.path.exists(protxt):
                    time.sleep(1)
                    continue
                content = Path(protxt).read_text(encoding='utf-8').strip().split("\n")
                if content[-1] == 'progress=end':
                    return
                idx = len(content) - 1
                end_time = "00:00:00"
                while idx > 0:
                    if content[idx].startswith('out_time='):
                        end_time = content[idx].split('=')[1].strip()
                        break
                    idx -= 1
                try:
                    h, m, s = end_time.split(':')
                except Exception:
                    time.sleep(1)
                    continue
                else:
                    h, m, s = end_time.split(':')
                    tmp1 = round((int(h) * 3600000 + int(m) * 60000 + int(s[:2]) * 1000) / video_time, 2)
                    if percent + tmp1 < 99.9:
                        percent += tmp1
                    self.uito.emit(f'jd:{percent}%')
                    time.sleep(1)

        def run(self):
            try:
                if self.audio:
                    # 需要保留原视频中声音 并且原视频中有声音
                    tmp_mp4 = None
                    if self.saveraw and self.video_info['streams_audio']:
                        tmp_mp4 = config.TEMP_HOME + f"/{time.time()}.m4a"
                        # 存在声音，则需要混合
                        tools.runffmpeg([
                            '-y',
                            '-i',
                            self.video,
                            "-vn",
                            '-i',
                            self.audio,
                            '-filter_complex',
                            "[1:a]apad[a1];[0:a][a1]amerge=inputs=2[aout]",
                            '-map',
                            '[aout]',
                            '-ac',
                            '2', tmp_mp4])

                    # 不保留原声音
                    end_mp4 = config.TEMP_HOME + f"/hb{time.time()}.mp4"
                    tools.runffmpeg([
                        '-y',
                        '-i',
                        os.path.normpath(self.video),
                        '-i',
                        os.path.normpath(tmp_mp4 if tmp_mp4 else self.audio),
                        '-c:v',
                        'copy',
                        "-c:a",
                        "aac",
                        "-map",
                        "0:v:0",
                        "-map",
                        "1:a:0",
                        "-shortest",
                        end_mp4
                    ]
                    )
                    self.video = end_mp4
                if not self.srt:
                    self.file = self.video
                else:
                    protxt = config.TEMP_HOME + f'/jd{time.time()}.txt'
                    threading.Thread(target=self.hebing_pro, args=(protxt, self.video_time,)).start()

                    cmd=[
                        '-y',
                        "-progress",
                        protxt,
                        '-i',
                        os.path.normpath(self.video)
                    ]
                    if not self.is_soft or not self.language:
                        #硬字幕
                        sub_list=tools.get_subtitle_from_srt(self.srt,is_file=True)
                        text=""
                        for i, it in enumerate(sub_list):
                            it['text'] = textwrap.fill(it['text'], self.maxlen, replace_whitespace=False).strip()
                            text += f"{it['line']}\n{it['time']}\n{it['text'].strip()}\n\n"
                        srtfile=config.TEMP_HOME+f"/vasrt{time.time()}.srt"
                        Path(srtfile).write_text(text,encoding='utf-8')
                        assfile=tools.set_ass_font(srtfile)
                        os.chdir(config.TEMP_HOME)
                        cmd+=[
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
                        os.chdir(os.path.dirname(self.srt))
                        #软字幕
                        subtitle_language=translator.get_subtitle_code(
                            show_target=self.language)
                        cmd+=[
                            '-i',
                            os.path.basename(self.srt),
                            '-c:v',
                            'copy',
                            "-c:s",
                            "mov_text",
                            "-metadata:s:s:0",
                            f"language={subtitle_language}"
                        ]
                    cmd.append(self.file)
                    tools.runffmpeg(cmd)

            except Exception as e:
                print(e)
                self.uito.emit('error:' + str(e))
            else:
                self.uito.emit(self.file)

    def feed(d):
        if d.startswith("error:"):
            QtWidgets.QMessageBox.critical(config.vasform, config.transobj['anerror'], d)
            config.vasform.ysphb_startbtn.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            config.vasform.ysphb_startbtn.setDisabled(False)
            config.vasform.ysphb_opendir.setDisabled(False)
        elif d.startswith('jd:'):
            config.vasform.ysphb_startbtn.setText(d[3:])
        else:
            config.vasform.ysphb_startbtn.setText('执行完成/开始执行' if config.defaulelang == 'zh' else 'Ended/Start operate')
            config.vasform.ysphb_startbtn.setDisabled(False)
            config.vasform.ysphb_out.setText(d)
            config.vasform.ysphb_opendir.setDisabled(False)

    def get_file(type='video'):
        fname = None
        if type == 'video':
            fname, _ = QFileDialog.getOpenFileName(config.hunliuform, 'Select Video', config.params['last_opendir'],
                                                   "Video files(*.mp4 *.mov *.mkv *.avi *.mepg)")
        elif type == 'wav':
            fname, _ = QFileDialog.getOpenFileName(config.hunliuform, 'Select Audio', config.params['last_opendir'],
                                                   "Audio files(*.mp3 *.wav *.flac *.aac *.m4a)")
        elif type == 'srt':
            fname, _ = QFileDialog.getOpenFileName(config.hunliuform, 'Select SRT', config.params['last_opendir'],
                                                   "Srt files(*.srt)")

        if not fname:
            return

        if type == 'video':
            config.vasform.ysphb_videoinput.setText(fname.replace('\\', '/'))
        if type == 'wav':
            config.vasform.ysphb_wavinput.setText(fname.replace('\\', '/'))
        if type == 'srt':
            config.vasform.ysphb_srtinput.setText(fname.replace('\\', '/'))
        config.params['last_opendir'] = os.path.dirname(fname)

    def start():
        # 开始处理分离，判断是否选择了源文件
        video = config.vasform.ysphb_videoinput.text()
        audio = config.vasform.ysphb_wavinput.text()
        srt = config.vasform.ysphb_srtinput.text()
        is_soft=config.vasform.ysphb_issoft.isChecked()
        language=config.vasform.language.currentText()
        saveraw = config.vasform.ysphb_replace.isChecked()
        maxlen=30
        try:
            maxlen=int(config.vasform.ysphb_maxlen.text())
        except Exception:
            pass
        if not video:
            QMessageBox.critical(config.vasform, config.transobj['anerror'],
                                 '必须选择视频' if config.defaulelang == 'zh' else 'Video must be selected')
            return
        if not audio and not srt:
            QMessageBox.critical(config.vasform, config.transobj['anerror'],
                                 '音频和视频至少要选择一个' if config.defaulelang == 'zh' else 'Choose at least one for audio and video')
            return

        config.vasform.ysphb_startbtn.setText(
            '执行中...' if config.defaulelang == 'zh' else 'In Progress...')
        config.vasform.ysphb_startbtn.setDisabled(True)
        config.vasform.ysphb_opendir.setDisabled(True)
        task = CompThread(parent=config.vasform,
                          video=video,
                          audio=audio if audio else None,
                          srt=srt if srt else None,
                          saveraw=saveraw,
                          is_soft=is_soft,
                          language=language,
                          maxlen=maxlen
                          )
        task.uito.connect(feed)
        task.start()

    def opendir():
        filename = config.vasform.ysphb_out.text().strip()
        if filename:
            dirname = os.path.dirname(filename)
            if dirname:
                QDesktopServices.openUrl(QUrl.fromLocalFile(dirname))

    from videotrans.component import VASForm
    try:
        if config.vasform is not None:
            config.vasform.show()
            config.vasform.raise_()
            config.vasform.activateWindow()
            return
        config.vasform = VASForm()
        config.vasform.ysphb_selectvideo.clicked.connect(lambda: get_file('video'))
        config.vasform.ysphb_selectwav.clicked.connect(lambda: get_file('wav'))
        config.vasform.ysphb_selectsrt.clicked.connect(lambda: get_file('srt'))
        config.vasform.ysphb_startbtn.clicked.connect(start)
        config.vasform.ysphb_opendir.clicked.connect(opendir)
        config.vasform.show()
    except Exception as e:
        print(e)
