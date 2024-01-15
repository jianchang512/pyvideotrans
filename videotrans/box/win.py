# -*- coding: utf-8 -*-
import datetime
import json
import os
import re
import time
from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings, QUrl
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtWidgets import QMainWindow,  QFileDialog, QMessageBox,   QLabel
from videotrans import VERSION
from videotrans.box.component import Player, DropButton, Textedit, TextGetdir
from videotrans.box.logs_worker import LogsWorker
from videotrans.box.worker import Worker, WorkerWhisper, WorkerTTS, FanyiWorker
from videotrans.configure import boxcfg, config
from videotrans.configure.config import logger, rootdir, homedir, langlist, english_code_bygpt
from videotrans.util.tools import set_proxy, get_video_info, runffmpeg

from videotrans.configure.config import transobj

if config.defaulelang == "zh":
    from videotrans.ui.toolbox import Ui_MainWindow
else:
    from videotrans.ui.toolboxen import Ui_MainWindow

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.initUI()
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))
        self.setWindowTitle(f"Video Toolbox {VERSION}")

    def closeEvent(self, event):
        # 拦截窗口关闭事件，隐藏窗口而不是真正关闭
        self.hide()
        event.ignore()

    def hideWindow(self):
        # 示例按钮点击时调用，隐藏窗口
        self.hide()

    def initUI(self):
        self.settings = QSettings("Jameson", "VideoTranslate")
        # tab-1
        self.yspfl_video_wrap = Player(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.yspfl_video_wrap.sizePolicy().hasHeightForWidth())
        self.yspfl_video_wrap.setSizePolicy(sizePolicy)
        self.yspfl_widget.insertWidget(0, self.yspfl_video_wrap)
        self.yspfl_video_wrap.setStyleSheet("""background-color:rgb(10,10,10)""")
        self.yspfl_video_wrap.setAcceptDrops(True)

        # 启动音视频分离
        self.yspfl_startbtn.clicked.connect(self.yspfl_start_fn)
        self.yspfl_openbtn1.clicked.connect(lambda: self.yspfl_open_fn("video"))
        self.yspfl_openbtn2.clicked.connect(lambda: self.yspfl_open_fn("wav"))

        # tab-2 音视频字幕合并
        self.ysphb_selectvideo.clicked.connect(lambda: self.ysphb_select_fun("video"))
        self.ysphb_selectwav.clicked.connect(lambda: self.ysphb_select_fun("wav"))
        self.ysphb_selectsrt.clicked.connect(lambda: self.ysphb_select_fun("srt"))
        self.ysphb_startbtn.clicked.connect(self.ysphb_start_fun)
        self.ysphb_opendir.clicked.connect(lambda: self.opendir_fn(os.path.dirname(self.ysphb_out.text())))

        # tab-3 语音识别 先添加按钮
        self.shibie_dropbtn = DropButton(transobj['xuanzeyinshipin'])
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.shibie_dropbtn.sizePolicy().hasHeightForWidth())
        self.shibie_dropbtn.setSizePolicy(sizePolicy)
        self.shibie_dropbtn.setMinimumSize(0, 150)
        self.shibie_widget.insertWidget(0, self.shibie_dropbtn)

        self.langauge_name = list(langlist.keys())
        self.shibie_language.addItems(self.langauge_name)
        self.shibie_model.addItems(["base", "small", "medium", "large-v3"])
        self.shibie_startbtn.clicked.connect(self.shibie_start_fun)
        self.shibie_savebtn.clicked.connect(self.shibie_save_fun)

        # tab-4 语音合成
        self.hecheng_plaintext = Textedit()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.hecheng_plaintext.sizePolicy().hasHeightForWidth())
        self.hecheng_plaintext.setSizePolicy(sizePolicy)
        self.hecheng_plaintext.setMinimumSize(0, 150)
        self.hecheng_plaintext.setPlaceholderText(transobj['tuodonghuoshuru'])
        self.hecheng_layout.insertWidget(0, self.hecheng_plaintext)
        self.hecheng_language.addItems(['-'] + self.langauge_name)
        self.hecheng_role.addItems(['No'])
        self.hecheng_language.currentTextChanged.connect(self.hecheng_language_fun)
        self.hecheng_startbtn.clicked.connect(self.hecheng_start_fun)
        self.hecheng_opendir.clicked.connect(lambda: self.opendir_fn(self.hecheng_out.text().strip()))
        # 设置 tts_type
        self.tts_type.addItems(config.params['tts_type_list'])
        # tts_type 改变时，重设角色
        self.tts_type.currentTextChanged.connect(self.tts_type_change)
        self.tts_issrt.stateChanged.connect(self.tts_issrt_change)

        # tab-5 格式转换
        self.geshi_input = TextGetdir()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.geshi_result.sizePolicy().hasHeightForWidth())
        self.geshi_input.setSizePolicy(sizePolicy)
        self.geshi_input.setMinimumSize(300, 0)

        self.geshi_input.setPlaceholderText(transobj['tuodongdaoci'])
        #self.geshi_input.setReadOnly(True)
        self.geshi_layout.insertWidget(0, self.geshi_input)
        self.geshi_mp4.clicked.connect(lambda: self.geshi_start_fun("mp4"))
        self.geshi_avi.clicked.connect(lambda: self.geshi_start_fun("avi"))
        self.geshi_mov.clicked.connect(lambda: self.geshi_start_fun("mov"))
        self.geshi_mp3.clicked.connect(lambda: self.geshi_start_fun("mp3"))
        self.geshi_wav.clicked.connect(lambda: self.geshi_start_fun("wav"))
        self.geshi_aac.clicked.connect(lambda: self.geshi_start_fun("aac"))
        self.geshi_m4a.clicked.connect(lambda: self.geshi_start_fun("m4a"))
        self.geshi_flac.clicked.connect(lambda: self.geshi_start_fun("flac"))
        self.geshi_output.clicked.connect(lambda: self.opendir_fn(f'{homedir}/conver'))
        if not os.path.exists(f'{homedir}/conver'):
            os.makedirs(f'{homedir}/conver', exist_ok=True)

        # 混流
        self.hun_file1btn.clicked.connect(lambda: self.hun_get_file('file1'))
        self.hun_file2btn.clicked.connect(lambda: self.hun_get_file('file2'))
        self.hun_startbtn.clicked.connect(self.hun_fun)
        self.hun_opendir.clicked.connect(lambda: self.opendir_fn(self.hun_out.text()))

        # 翻译
        proxy = set_proxy()
        if proxy:
            self.fanyi_proxy.setText(proxy)
        self.languagename = list(langlist.keys())
        self.fanyi_target.addItems(["-"] + self.languagename)
        self.fanyi_import.clicked.connect(self.fanyi_import_fun)
        self.fanyi_start.clicked.connect(self.fanyi_start_fun)
        self.fanyi_translate_type.addItems(
            ["google", "baidu", "chatGPT", 'Azure', 'Gemini', "tencent", "DeepL", "DeepLX"])

        self.fanyi_sourcetext = Textedit()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)

        self.fanyi_sourcetext.setSizePolicy(sizePolicy)
        self.fanyi_sourcetext.setMinimumSize(300, 0)

        self.fanyi_sourcetext.setPlaceholderText(transobj['tuodongfanyi'])

        self.fanyi_layout.insertWidget(0, self.fanyi_sourcetext)
        self.daochu.clicked.connect(self.fanyi_save_fun)
        self.statuslabel=QLabel("")

        self.statusBar.addWidget(self.statuslabel)
        self.statusBar.addPermanentWidget(QLabel("github.com/jianchang512/pyvideotrans"))

        #     日志
        self.task_logs = LogsWorker(self)
        self.task_logs.post_logs.connect(self.receiver)
        self.task_logs.start()

    # 获取wav件
    def hun_get_file(self, name='file1'):
        fname, _ = QFileDialog.getOpenFileName(self, "Select audio", os.path.expanduser('~'),
                                               "Audio files(*.wav *.mp3 *.aac *.m4a *.flac)")
        if fname:
            if name == 'file1':
                self.hun_file1.setText(fname.replace('file:///', '').replace('\\', '/'))
            else:
                self.hun_file2.setText(fname.replace('file:///', '').replace('\\', '/'))

    # 文本翻译，导入文本文件
    def fanyi_import_fun(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Select txt or srt", os.path.expanduser('~'),
                                               "Text files(*.srt *.txt)")
        if fname:
            with open(fname.replace('file:///', ''), 'r', encoding='utf-8') as f:
                self.fanyi_sourcetext.setPlainText(f.read().strip())

    def render_play(self, t):
        if t != 'ok':
            return
        self.yspfl_video_wrap.close()
        self.yspfl_video_wrap = None
        self.yspfl_video_wrap = Player(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.yspfl_video_wrap.sizePolicy().hasHeightForWidth())
        self.yspfl_video_wrap.setSizePolicy(sizePolicy)
        self.yspfl_widget.insertWidget(0, self.yspfl_video_wrap)
        self.yspfl_video_wrap.setStyleSheet("""background-color:rgb(10,10,10)""")
        self.yspfl_video_wrap.setAcceptDrops(True)

    def opendir_fn(self, dirname=None):
        if not dirname:
            return
        if not os.path.isdir(dirname):
            dirname = os.path.dirname(dirname)
        QDesktopServices.openUrl(QUrl(f"file:{dirname.strip()}"))

    # 通知更新ui
    def receiver(self, json_data):
        data = json.loads(json_data)
        # fun_name 方法名，type类型，text具体文本
        if "func_name" not in data:
            self.statuslabel.setText(data['text'][:60])
            if data['type']=='error':
                self.statuslabel.setStyle("""color:#ff0000""")
        elif data['func_name'] == "yspfl_end":
            # 音视频分离完成了
            self.yspfl_startbtn.setText(transobj["zhixingwc"] if data['type'] == "end" else transobj["zhixinger"])
            self.yspfl_startbtn.setDisabled(False)
        elif data['func_name'] == 'ysphb_end':
            self.ysphb_startbtn.setText(transobj["zhixingwc"] if data['type'] == "end" else transobj["zhixinger"])
            self.ysphb_startbtn.setDisabled(False)
            self.ysphb_opendir.setDisabled(False)
            if data['type'] == 'end':
                basename = os.path.basename(self.ysphb_videoinput.text())
                if os.path.exists(rootdir + f"/{basename}.srt"):
                    os.unlink(rootdir + f"/{basename}.srt")
        elif data['func_name'] == 'shibie_next':
            #     转换wav完成，开始最终识别
            self.shibie_start_next_fun()
        elif data['func_name'] == "shibie_end":
            # 识别执行完成
            self.disabled_shibie(False)
            if data['type'] == 'end':
                self.shibie_startbtn.setText(transobj["zhixingwc"])
                self.shibie_text.insertPlainText(data['text'])
            else:
                self.shibie_startbtn.setText(transobj["zhixinger"])
        elif data['func_name'] == 'hecheng_end':
            if data['type'] == 'end':
                self.hecheng_startbtn.setText(transobj["zhixingwc"])
                self.hecheng_startbtn.setToolTip(transobj["zhixingwc"])
            else:
                self.hecheng_startbtn.setText(data['text'])
                self.hecheng_startbtn.setToolTip(data['text'])
                self.hecheng_startbtn.setStyleSheet("""color:#ff0000""")
            self.hecheng_startbtn.setDisabled(False)
        elif data['func_name'] == 'geshi_end':
            boxcfg.geshi_num -= 1
            self.geshi_result.insertPlainText(data['text'])
            if boxcfg.geshi_num <= 0:
                self.disabled_geshi(False)
                self.geshi_result.insertPlainText(transobj["zhixingwc"])
                self.geshi_input.clear()
        elif data['func_name'] == 'hun_end':
            self.hun_startbtn.setDisabled(False)
            self.hun_out.setDisabled(False)
        elif data['func_name'] == 'fanyi_end':
            self.fanyi_start.setDisabled(False)
            self.fanyi_start.setText(transobj['starttrans'])
            self.fanyi_targettext.setPlainText(data['text'])
            self.daochu.setDisabled(False)


    # tab-1 音视频分离启动
    def yspfl_start_fn(self):
        if not self.yspfl_video_wrap.filepath:
            return QMessageBox.critical(self, transobj['anerror'], transobj['selectvideodir'])
        file = self.yspfl_video_wrap.filepath
        basename = os.path.basename(file)
        video_out = f"{homedir}/{basename}"
        if not os.path.exists(video_out):
            os.makedirs(video_out, exist_ok=True)
        self.yspfl_task = Worker(
            [['-y', '-i', file, '-an', f"{video_out}/{basename}.mp4", f"{video_out}/{basename}.wav"]], "yspfl_end",
            self)
        self.yspfl_task.update_ui.connect(self.receiver)
        self.yspfl_task.start()
        self.yspfl_startbtn.setText(transobj['running'])
        self.yspfl_startbtn.setDisabled(True)

        self.yspfl_videoinput.setText(f"{video_out}/{basename}.mp4")
        self.yspfl_wavinput.setText(f"{video_out}/{basename}.wav")

    # 音视频打开目录
    def yspfl_open_fn(self, name):
        pathdir = homedir
        if name == "video":
            pathdir = os.path.dirname(self.yspfl_videoinput.text())
        elif name == "wav":
            pathdir = os.path.dirname(self.yspfl_wavinput.text())
        QDesktopServices.openUrl(QUrl(f"file:{pathdir}"))

    # tab-2音视频合并
    def ysphb_select_fun(self, name):
        if name == "video":
            mime = "Video files(*.mp4 *.avi *.mov)"
            showname = " Video "
        elif name == "wav":
            mime = "Audio files(*.mp3 *.wav *.m4a *.aac *.flac)"
            showname = " Audio "
        else:
            mime = "Srt files(*.srt)"
            showname = " srt "
        fname, _ = QFileDialog.getOpenFileName(self, f"Select {showname} file", os.path.expanduser('~') + "\\Videos",  mime)
        if not fname:
            return

        if name == "video":
            self.ysphb_videoinput.setText(fname)
        elif name == "wav":
            self.ysphb_wavinput.setText(fname)
        else:
            self.ysphb_srtinput.setText(fname)


    def ysphb_start_fun(self):
        # 启动合并
        videofile = self.ysphb_videoinput.text()
        basename = os.path.basename(videofile)
        srtfile = self.ysphb_srtinput.text()
        wavfile = self.ysphb_wavinput.text()

        if not videofile or not os.path.exists(videofile):
            QMessageBox.critical(self, transobj['anerror'], transobj['selectvideodir'])
            return
        if not wavfile and not srtfile:
            QMessageBox.critical(self, transobj['anerror'], transobj['yinpinhezimu'])
            return
        if not os.path.exists(wavfile) and not os.path.exists(srtfile):
            QMessageBox.critical(self, transobj['anerror'], transobj["yinpinhezimu"])
            return

        savedir = f"{homedir}/hebing-{basename}"
        if not os.path.exists(savedir):
            os.makedirs(savedir, exist_ok=True)

        cmds = []
        if not os.path.exists(f'{config.rootdir}/tmp'):
            os.makedirs(f'{config.rootdir}/tmp',exist_ok=True)
        tmpname = f'{config.rootdir}/tmp/{time.time()}.mp4'
        tmpname_conver = f'{config.rootdir}/tmp/box-conver.mp4'
        video_info=get_video_info(videofile)
        if videofile[-3:].lower()!='mp4' or video_info['video_codec_name']!='h264' or (video_info['streams_audio']>0 and video_info['audio_codec_name']!='aac'):
            con_cmd=[
                '-y',
                '-i',
                videofile,
                '-c:v',
                "libx264",
                '-c:a',
                'aac'
            ]
            try:
                runffmpeg(con_cmd,de_format="nv12",no_decode=True,is_box=True)
            except:
                self.ysphb_startbtn.setText(transobj["start"])
                self.ysphb_startbtn.setDisabled(False)
                return False

            videofile=tmpname_conver

        if wavfile:
            # 视频里是否有音轨
            if video_info['streams_audio']>0:
                cmds = [
                    ['-y', '-i', videofile, '-i', wavfile, '-filter_complex', "[0:a][1:a]amerge=inputs=2[aout]",'-map', '0:v', '-map', "[aout]", '-c:v', 'copy', '-c:a', 'aac', tmpname],
                ]
            else:
                cmds=[['-y', '-i', videofile, '-i', wavfile, '-map','0:v','-map', '1:a', '-c:v', 'copy', '-c:a','aac',tmpname]]

        if srtfile:
            srtfile = srtfile.replace('\\', '/').replace(':', '\\\\:')
            cmds.append(['-y', '-i', tmpname if wavfile else videofile, "-vf", f"subtitles={srtfile}",'-c:v','libx264','-c:a','copy', f'{savedir}/{basename}.mp4'])
        self.ysphb_task = Worker(cmds, "ysphb_end", self)
        self.ysphb_task.update_ui.connect(self.receiver)
        self.ysphb_task.start()

        self.ysphb_startbtn.setText(transobj["running"])
        self.ysphb_startbtn.setDisabled(True)
        self.ysphb_out.setText(f"{savedir}/{basename}.mp4")
        self.ysphb_opendir.setDisabled(True)

    # tab-3 语音识别 预执行，检查
    def shibie_start_fun(self):
        model = self.shibie_model.currentText()
        if not os.path.exists(config.rootdir + f"/models/models--Systran--faster-whisper-{model}"):
            return QMessageBox.critical(self, transobj['anerror'], transobj['modellost'])
        file = self.shibie_dropbtn.text()
        if not file or not os.path.exists(file):
            return QMessageBox.critical(self, transobj['anerror'], transobj['bixuyinshipin'])
        basename = os.path.basename(file)
        self.shibie_startbtn.setText(transobj["running"])
        self.disabled_shibie(True)
        self.shibie_text.clear()

        if os.path.splitext(basename)[-1].lower() in [".mp4", ".avi", ".mov"]:
            out_file = f"{homedir}/tmp/{basename}.wav"
            if not os.path.exists(f"{homedir}/tmp"):
                os.makedirs(f"{homedir}/tmp")
            try:
                print(f'{file=}')
                self.shibie_dropbtn.setText(out_file)
                self.shibie_ffmpeg_task = Worker([
                    ['-y', '-i', file, out_file]
                ], "shibie_next", self)
                self.shibie_ffmpeg_task.update_ui.connect(self.receiver)
                self.shibie_ffmpeg_task.start()
            except Exception as e:
                logger.error("执行语音识别前，先从视频中分离出音频失败：" + str(e))
                self.shibie_startbtn.setText("执行")
                self.disabled_shibie(False)
                QMessageBox.critical(self, transobj['anerror'], str(e))
        else:
            # 是音频，直接执行
            self.shibie_start_next_fun()

    # 最终执行
    def shibie_start_next_fun(self):
        file = self.shibie_dropbtn.text()
        if not os.path.exists(file):
            return QMessageBox.critical(self, transobj['anerror'], transobj['chakanerror'])
        model = self.shibie_model.currentText()
        self.shibie_task = WorkerWhisper(file, model, langlist[self.shibie_language.currentText()][0],
                                         "shibie_end", self)
        self.shibie_task.update_ui.connect(self.receiver)
        self.shibie_task.start()

    def shibie_save_fun(self):
        srttxt = self.shibie_text.toPlainText().strip()
        if not srttxt:
            return QMessageBox.critical(self, transobj['anerror'], transobj['srtisempty'])
        dialog = QFileDialog()
        dialog.setWindowTitle(transobj['savesrtto'])
        dialog.setNameFilters(["subtitle files (*.srt)"])
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.exec_()
        if not dialog.selectedFiles():  # If the user closed the choice window without selecting anything.
            return
        else:
            path_to_file = dialog.selectedFiles()[0]
        with open(path_to_file + f"{'' if path_to_file.endswith('.srt') else '.srt'}", "w") as file:
            file.write(srttxt)

    # 禁用启用按钮
    def disabled_shibie(self, type):
        self.shibie_startbtn.setDisabled(type)
        self.shibie_dropbtn.setDisabled(type)
        self.shibie_language.setDisabled(type)
        self.shibie_model.setDisabled(type)

    # tab-4 语音合成
    def hecheng_start_fun(self):
        txt = self.hecheng_plaintext.toPlainText().strip()
        language = self.hecheng_language.currentText()
        role = self.hecheng_role.currentText()
        rate = int(self.hecheng_rate.value())
        tts_type = self.tts_type.currentText()

        if not txt:
            return QMessageBox.critical(self, transobj['anerror'], transobj['neirongweikong'])
        if language == '-' or role == 'No':
            return QMessageBox.critical(self, transobj['anerror'], transobj['yuyanjuesebixuan'])
        if tts_type == 'openaiTTS' and not config.params['chatgpt_key']:
            return QMessageBox.critical(self, transobj['anerror'], transobj['bixutianxie'] + "chatGPT key")
        elif tts_type == 'coquiTTS' and not config.params['coquitts_key']:
            return QMessageBox.critical(self, transobj['anerror'], transobj['bixutianxie'] + " coquiTTS key")
        # 文件名称
        filename = self.hecheng_out.text()
        if filename and re.search(r'\\|/', filename):
            filename=""
        if not filename:
            filename = f"tts-{role}-{rate}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.wav"
        else:
            filename = filename.replace('.wav', '') + ".wav"
        if not os.path.exists(f"{homedir}/tts"):
            os.makedirs(f"{homedir}/tts", exist_ok=True)
        wavname = f"{homedir}/tts/{filename}"
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"-{rate}%"

        issrt = self.tts_issrt.isChecked()
        self.hecheng_task = WorkerTTS(self,
                                      text=txt,
                                      role=role,
                                      rate=rate,
                                      filename=wavname,
                                      tts_type=self.tts_type.currentText(),
                                      func_name="hecheng_end",
                                      voice_autorate=issrt and self.voice_autorate.isChecked(),
                                      tts_issrt=issrt)
        self.hecheng_task.update_ui.connect(self.receiver)
        self.hecheng_task.start()
        self.hecheng_startbtn.setText(transobj["running"])
        self.hecheng_startbtn.setDisabled(True)
        self.hecheng_out.setText(wavname)
        self.hecheng_out.setDisabled(True)

    def tts_issrt_change(self, state):
        if state:
            self.voice_autorate.setDisabled(False)
        else:
            self.voice_autorate.setDisabled(True)

    # tts类型改变
    def tts_type_change(self, type):
        if type == "openaiTTS":
            self.hecheng_role.clear()
            self.hecheng_role.addItems(config.params['openaitts_role'].split(","))
        elif type == 'coquiTTS':
            self.hecheng_role.clear()
            self.hecheng_role.addItems(config.params['coquitts_role'].split(","))
        elif type == 'elevenlabsTTS':
            self.hecheng_role.clear()
            self.hecheng_role.addItems(config.params['elevenlabstts_role'])
        elif type == 'edgeTTS':
            self.hecheng_language_fun(self.hecheng_language.currentText())

    # 合成语言变化，需要获取到角色
    def hecheng_language_fun(self, t):
        if self.tts_type.currentText() != "edgeTTS":
            return
        self.hecheng_role.clear()
        if t == '-':
            self.hecheng_role.addItems(['No'])
            return
        voice_list = config.edgeTTS_rolelist#get_edge_rolelist()
        if not voice_list:
            self.hecheng_language.setCurrentText('-')
            QMessageBox.critical(self, transobj['anerror'], transobj['nojueselist'])
            return
        try:
            vt = langlist[t][0].split('-')[0]
            print(f"{vt=}")
            if vt not in voice_list:
                self.hecheng_role.addItems(['No'])
                QMessageBox.critical(self, transobj['anerror'], f'{transobj["buzhichijuese"]}:{t}_{vt}')
                return
            if len(voice_list[vt]) < 2:
                self.hecheng_language.setCurrentText('-')
                QMessageBox.critical(self, transobj['anerror'], f'{transobj["buzhichijuese"]}:{t}_{vt}')
                return
            self.hecheng_role.addItems(voice_list[vt])
        except Exception as e:
            print(e)
            self.hecheng_role.addItems(["No"])

    # tab-5 转换
    def geshi_start_fun(self, ext):
        filelist = self.geshi_input.toPlainText().strip().split("\n")
        filelist_vail = []
        for it in filelist:
            if it and os.path.exists(it) and it.split('.')[-1].lower() in ['mp4', 'avi', 'mov', 'mp3', 'wav','aac','m4a','flac']:
                filelist_vail.append(it)
        if len(filelist_vail) < 1:
            return QMessageBox.critical(self, transobj['anerror'], transobj['nowenjian'])
        self.geshi_input.setPlainText("\n".join(filelist_vail))
        self.disabled_geshi(True)
        boxcfg.geshi_num = len(filelist_vail)
        cmdlist = []
        savedir = f"{homedir}/conver"
        if not os.path.exists(savedir):
            os.makedirs(savedir, exist_ok=True)
        for it in filelist_vail:
            basename = os.path.basename(it)
            ext_this = basename.split('.')[-1].lower()
            if ext == ext_this:
                boxcfg.geshi_num -= 1
                self.geshi_result.insertPlainText(f"{it} -> {ext}")
                continue
            if ext_this in ["wav", "mp3","aac","m4a","flac"] and ext in ["mp4", "mov", "avi"]:
                self.geshi_result.insertPlainText(f"{it} {transobj['yinpinbuke']} {ext} ")
                boxcfg.geshi_num -= 1
                continue
            cmdlist.append(['-y', '-i', f'{it}', f'{savedir}/{basename}.{ext}'])

        if len(cmdlist) < 1:
            self.geshi_result.insertPlainText(transobj["quanbuend"])
            self.disabled_geshi(False)
            return
        self.geshi_task = Worker(cmdlist, "geshi_end", self, True)
        self.geshi_task.update_ui.connect(self.receiver)
        self.geshi_task.start()

    # 禁用按钮
    def disabled_geshi(self, type):
        self.geshi_mp4.setDisabled(type)
        self.geshi_avi.setDisabled(type)
        self.geshi_mov.setDisabled(type)
        self.geshi_mp3.setDisabled(type)
        self.geshi_wav.setDisabled(type)
        self.geshi_aac.setDisabled(type)
        self.geshi_flac.setDisabled(type)
        self.geshi_m4a.setDisabled(type)

    # 音频混流
    def hun_fun(self):
        out = self.hun_out.text().strip()
        if out and os.path.isfile(out):
            out=""
        if not out:
            out = f'{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}.wav'
        elif not out.endswith('.wav'):
            out += '.wav'
            out = out.replace('\\', '').replace('/', '')
        dirname = homedir + "/hun_liu"
        if not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)
        savename = f'{dirname}/{out}'

        self.hun_out.setText(savename)

        file1 = self.hun_file1.text()
        file2 = self.hun_file2.text()

        cmd = ['-y', '-i', file1, '-i', file2, '-filter_complex',
               "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2", '-ac', '2', savename]
        self.geshi_task = Worker([cmd], "hun_end", self, True)
        self.geshi_task.update_ui.connect(self.receiver)
        self.geshi_task.start()
        self.hun_startbtn.setDisabled(True)
        self.hun_out.setDisabled(True)

    # 翻译开始
    def fanyi_start_fun(self):
        target_language = self.fanyi_target.currentText()
        translate_type = self.fanyi_translate_type.currentText()
        if target_language == '-':
            return QMessageBox.critical(self, transobj['anerror'], transobj["fanyimoshi1"])
        proxy = self.fanyi_proxy.text()
        if proxy:
            set_proxy(proxy)
        else:
            proxy=self.settings.value("proxy", "", str)
            if proxy:
                set_proxy(proxy)
                self.fanyi_proxy.setText(proxy)
        issrt = self.fanyi_issrt.isChecked()
        source_text = self.fanyi_sourcetext.toPlainText().strip()
        if not source_text:
            return QMessageBox.critical(self, transobj['anerror'], transobj["wenbenbukeweikong"])
        # target_language = langlist[target_language][0]
        config.baidu_appid = self.settings.value("baidu_appid", "")
        config.baidu_miyue = self.settings.value("baidu_miyue", "")
        config.deepl_authkey = self.settings.value("deepl_authkey", "")
        config.deeplx_address = self.settings.value("deeplx_address", "")
        config.chatgpt_api = self.settings.value("chatgpt_api", "")
        config.chatgpt_key = self.settings.value("chatgpt_key", "")
        config.tencent_SecretId = self.settings.value("tencent_SecretId", "")
        config.tencent_SecretKey = self.settings.value("tencent_SecretKey", "")
        # os.environ['OPENAI_API_KEY'] = self.cfg['chatgpt_key']
        # google language code

        if translate_type == 'google':
            target_language = langlist[target_language][0]
        elif translate_type == 'baidu(noKey)':
            target_language = langlist[target_language][2]
        elif translate_type == 'baidu':
            # baidu language code
            target_language = langlist[target_language][2]
            if not config.baidu_appid or not config.baidu_miyue:
                QMessageBox.critical(self, transobj['anerror'], transobj['bixutianxie'] + 'Baidu key')
                return
        elif translate_type == 'tencent':
            #     腾讯翻译
            target_language = langlist[target_language][4]
            if not config.tencent_SecretId or not config.tencent_SecretKey:
                QMessageBox.critical(self, transobj['anerror'], transobj['bixutianxie'] + ' Tencent key')
                return
        elif translate_type == 'chatGPT':
            # chatGPT 翻译
            target_language = english_code_bygpt[self.languagename.index(target_language)]
            if not config.chatgpt_key:
                QMessageBox.critical(self, transobj['anerror'], transobj['bixutianxie'] + 'ChatGPT key')
                return
        elif translate_type == 'DeepL' or translate_type == 'DeepLX':
            # DeepL翻译
            if translate_type == 'DeepL' and not config.deepl_authkey:
                QMessageBox.critical(self, transobj['anerror'], transobj['bixutianxie'] + ' DeepL key')
                return
            if translate_type == 'DeepLX' and not config.deeplx_address:
                QMessageBox.critical(self, transobj['anerror'], transobj['bixutianxie'] + ' DeepLX url')
                return
            target_language = langlist[target_language][3]
            if target_language == 'No':
                QMessageBox.critical(self, transobj['anerror'], 'DeepL ' + transobj['buzhichifanyi'])
                return
        self.fanyi_task = FanyiWorker(translate_type, target_language, source_text, issrt, self)
        self.fanyi_task.ui.connect(self.receiver)
        self.fanyi_task.start()
        self.fanyi_start.setDisabled(True)
        self.fanyi_start.setText(transobj["running"])
        self.fanyi_targettext.clear()
        self.daochu.setDisabled(True)
    def fanyi_save_fun(self):
        srttxt = self.fanyi_targettext.toPlainText().strip()
        if not srttxt:
            return QMessageBox.critical(self, transobj['anerror'], transobj['srtisempty'])
        issrt = self.fanyi_issrt.isChecked()
        dialog = QFileDialog()
        dialog.setWindowTitle(transobj['savesrtto'])
        dialog.setNameFilters(["subtitle files (*.srt)" if issrt else "text files (*.txt)"])
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.exec_()
        if not dialog.selectedFiles():  # If the user closed the choice window without selecting anything.
            return
        else:
            path_to_file = dialog.selectedFiles()[0]
        ext= ".srt" if issrt else ".txt"
        if path_to_file.endswith('.srt') or path_to_file.endswith('.txt'):
            path_to_file=path_to_file[:-4]+ext
        else:
            path_to_file+=ext
        with open(path_to_file , "w") as file:
            file.write(srttxt)