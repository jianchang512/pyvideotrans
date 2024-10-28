import json
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
def openwin():
    RESULT_DIR = config.HOME_DIR + "/vas"
    Path(RESULT_DIR).mkdir(exist_ok=True)

    class CompThread(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, video=None, audio=None, srt=None, saveraw=True, is_soft=False, language=None,
                     maxlen=30,audio_process=0):
            super().__init__(parent=parent)
            self.video = video
            self.audio = audio
            self.srt = srt
            self.saveraw = saveraw
            self.is_soft = is_soft
            self.language = language
            self.maxlen = maxlen
            self.audio_process=audio_process
            self.file = f'{RESULT_DIR}/{Path(self.video).stem}-{int(time.time())}.mp4'
            self.video_info = tools.get_video_info(self.video)
            self.video_time = tools.get_video_duration(self.video)

        def post(self, type='logs', text=''):
            self.uito.emit(json.dumps({"type": type, "text": text}))

        #
        def hebing_pro(self, protxt, video_time):
            percent = 0
            while 1:
                if percent >= 100:
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
                self.post(type='jd', text=f'{percent}%')
                time.sleep(1)

        def run(self):
            try:
                tmp_mp4 = None
                end_mp4 = None
                # 存在音频
                if self.audio:
                    video_time = tools.get_video_duration(self.video)
                    audio_time = int(tools.get_audio_time(self.audio) * 1000)
                    tmp_audio = config.TEMP_HOME + f"/{time.time()}-{Path(self.audio).name}"
                    if audio_time > video_time and self.audio_process == 0:
                        tools.runffmpeg(
                            ['-y', '-i', self.audio, '-ss', '00:00:00.000', '-t', str(video_time / 1000), tmp_audio])
                        self.audio = tmp_audio
                    elif audio_time > video_time and self.audio_process == 1:
                        tools.precise_speed_up_audio(file_path=self.audio, out=tmp_audio, target_duration_ms=video_time)
                        self.audio = tmp_audio
                    # 需要保留原视频中声音 并且原视频中有声音
                    if self.saveraw and self.video_info['streams_audio']:
                        tmp_mp4 = config.TEMP_HOME + f"/{time.time()}.m4a"
                        # 存在声音，则需要混合
                        tools.runffmpeg([
                            '-y',
                            '-i',
                            os.path.normpath(self.video),
                            "-vn",
                            '-i',
                            os.path.normpath(self.audio),
                            '-filter_complex',
                            "[1:a]apad[a1];[0:a][a1]amerge=inputs=2[aout]",
                            '-map',
                            '[aout]',
                            '-ac',
                            '2', tmp_mp4])

                    # 视频和音频混合
                    # 如果存在字幕则生成中间结果end_mp4
                    if self.srt:
                        end_mp4 = config.TEMP_HOME + f"/hb{time.time()}.mp4"
                    tools.runffmpeg([
                        '-y',
                        '-i',
                        os.path.normpath(self.video),
                        '-i',
                        os.path.normpath(tmp_mp4 if tmp_mp4 else self.audio),
                        '-c:v',
                        'copy' if Path(self.video).suffix.lower() == '.mp4' else 'libx264',
                        "-c:a",
                        "aac",
                        "-map",
                        "0:v:0",
                        "-map",
                        "1:a:0",
                        "-shortest",
                        end_mp4 if self.srt else self.file
                    ])
                # 存在字幕则继续嵌入
                if self.srt:
                    # 存在中间结果mp4
                    if end_mp4:
                        self.video = end_mp4
                    protxt = config.TEMP_HOME + f'/jd{time.time()}.txt'
                    threading.Thread(target=self.hebing_pro, args=(protxt, self.video_time,)).start()

                    cmd = [
                        '-y',
                        "-progress",
                        protxt,
                        '-i',
                        os.path.normpath(self.video)
                    ]
                    if not self.is_soft or not self.language:
                        # 硬字幕
                        sub_list = tools.get_subtitle_from_srt(self.srt, is_file=True)
                        text = ""
                        for i, it in enumerate(sub_list):
                            it['text'] = textwrap.fill(it['text'], self.maxlen, replace_whitespace=False).strip()
                            text += f"{it['line']}\n{it['time']}\n{it['text'].strip()}\n\n"
                        srtfile = config.TEMP_HOME + f"/vasrt{time.time()}.srt"
                        with Path(srtfile).open('w', encoding='utf-8') as f:
                            f.write(text)
                            f.flush()
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
                        os.chdir(os.path.dirname(self.srt))
                        # 软字幕
                        subtitle_language = translator.get_subtitle_code(
                            show_target=self.language)
                        cmd += [
                            '-i',
                            os.path.basename(self.srt),
                            '-c:v',
                            'copy' if Path(self.video).suffix.lower() == '.mp4' else 'libx264',
                            "-c:s",
                            "mov_text",
                            "-metadata:s:s:0",
                            f"language={subtitle_language}"
                        ]
                    cmd.append(self.file)
                    tools.runffmpeg(cmd)
            except Exception as e:
                print(e)
                self.post(type='error', text=str(e))
            else:
                self.post(type='ok', text=self.file)

    def feed(d):
        if winobj.has_done:
            return
        d = json.loads(d)
        if d['type'] == "error":
            winobj.has_done = True
            QtWidgets.QMessageBox.critical(winobj, config.transobj['anerror'], d['text'])
            winobj.ysphb_startbtn.setText('开始执行' if config.defaulelang == 'zh' else 'start operate')
            winobj.ysphb_startbtn.setDisabled(False)
            winobj.ysphb_opendir.setDisabled(False)
        elif d['type'] == 'jd':
            winobj.ysphb_startbtn.setText(d['text'])
        elif d['type'] == 'logs':
            winobj.ysphb_startbtn.setText(d['text'])
        elif d['type']=='ok':
            winobj.has_done = True
            winobj.ysphb_startbtn.setText(config.transobj['zhixingwc'])
            winobj.ysphb_startbtn.setDisabled(False)
            winobj.ysphb_out.setText(d['text'])
            winobj.ysphb_opendir.setDisabled(False)

    def get_file(type='video'):
        fname = None
        if type == 'video':
            format_str = " ".join(['*.' + f for f in config.VIDEO_EXTS])
            fname, _ = QFileDialog.getOpenFileName(winobj, 'Select Video', config.params['last_opendir'],
                                                   f"Video files({format_str})")
        elif type == 'wav':
            format_str = " ".join(['*.' + f for f in config.AUDIO_EXITS])
            fname, _ = QFileDialog.getOpenFileName(winobj, 'Select Audio', config.params['last_opendir'],
                                                   f"Audio files({format_str})")
        elif type == 'srt':
            fname, _ = QFileDialog.getOpenFileName(winobj, 'Select SRT', config.params['last_opendir'],
                                                   "Srt files(*.srt)")

        if not fname:
            return

        if type == 'video':
            winobj.ysphb_videoinput.setText(fname.replace('\\', '/'))
        if type == 'wav':
            winobj.ysphb_wavinput.setText(fname.replace('\\', '/'))
        if type == 'srt':
            winobj.ysphb_srtinput.setText(fname.replace('\\', '/'))
        config.params['last_opendir'] = os.path.dirname(fname)

    def start():
        winobj.has_done = False
        # 开始处理分离，判断是否选择了源文件
        video = winobj.ysphb_videoinput.text()
        audio = winobj.ysphb_wavinput.text()
        srt = winobj.ysphb_srtinput.text()
        is_soft = winobj.ysphb_issoft.isChecked()
        language = winobj.language.currentText()
        saveraw = winobj.ysphb_replace.isChecked()
        maxlen = 30
        try:
            maxlen = int(winobj.ysphb_maxlen.text())
        except Exception:
            pass
        if not video:
            QMessageBox.critical(winobj, config.transobj['anerror'],
                                 '必须选择视频' if config.defaulelang == 'zh' else 'Video must be selected')
            return
        if not audio and not srt:
            QMessageBox.critical(winobj, config.transobj['anerror'],
                                 '音频和视频至少要选择一个' if config.defaulelang == 'zh' else 'Choose at least one for audio and video')
            return

        winobj.ysphb_startbtn.setText(
            '执行中...' if config.defaulelang == 'zh' else 'In Progress...')
        winobj.ysphb_startbtn.setDisabled(True)
        winobj.ysphb_opendir.setDisabled(True)
        task = CompThread(parent=winobj,
                          video=video,
                          audio=audio if audio else None,
                          srt=srt if srt else None,
                          saveraw=saveraw,
                          is_soft=is_soft,
                          language=language,
                          maxlen=maxlen,
                          audio_process=winobj.audio_process.currentIndex()
                          )
        task.uito.connect(feed)
        task.start()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    from videotrans.component import VASForm
    try:
        winobj = config.child_forms.get('vasform')
        if winobj is not None:
            winobj.show()
            winobj.raise_()
            winobj.activateWindow()
            return
        winobj = VASForm()
        config.child_forms['vasform'] = winobj
        winobj.ysphb_selectvideo.clicked.connect(lambda: get_file('video'))
        winobj.ysphb_selectwav.clicked.connect(lambda: get_file('wav'))
        winobj.ysphb_selectsrt.clicked.connect(lambda: get_file('srt'))
        winobj.ysphb_startbtn.clicked.connect(start)
        winobj.ysphb_opendir.clicked.connect(opendir)
        winobj.show()
    except Exception as e:
        print(e)
