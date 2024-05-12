# -*- coding: utf-8 -*-
import datetime
import json
import os
import re
import time

import torch
from PySide6 import QtWidgets
from PySide6.QtCore import QSettings, QUrl, Qt
from PySide6.QtGui import QDesktopServices, QIcon, QTextCursor
from PySide6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QLabel, QPlainTextEdit
from videotrans import VERSION
from videotrans.box.component import Player, DropButton, Textedit, TextGetdir
from videotrans.box.logs_worker import LogsWorker
from videotrans.box.worker import Worker, WorkerWhisper, WorkerTTS, FanyiWorker
from videotrans.configure import config
from videotrans import translator
from videotrans.translator import GOOGLE_NAME
from videotrans.util import tools
import shutil
from videotrans.ui.toolboxen import Ui_MainWindow
from videotrans.util.tools import get_azure_rolelist, get_edge_rolelist


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.initSize = None
        self.shibie_out_path = None
        self.hecheng_files = []
        self.fanyi_files = []
        self.fanyi_errors = ""
        self.initUI()
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))
        self.setWindowTitle(
            f"pyVideoTrans{config.uilanglist['Video Toolbox']} {VERSION} pyvideotrans.com {' Q群 933714380 ' if config.defaulelang == 'zh' else ''}")

    def closeEvent(self, event):
        if config.exit_soft:
            event.accept()
            self.close()
            return
        # 拦截窗口关闭事件，隐藏窗口而不是真正关闭
        self.hide()
        event.ignore()

    def hideWindow(self):
        # 示例按钮点击时调用，隐藏窗口
        self.hide()

    def initUI(self):
        if not os.path.exists(config.homedir):
            os.makedirs(config.homedir, exist_ok=True)
        if not os.path.exists(config.TEMP_HOME):
            os.makedirs(config.TEMP_HOME, exist_ok=True)
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
        self.shibie_dropbtn = DropButton(config.transobj['xuanzeyinshipin'])
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.shibie_dropbtn.sizePolicy().hasHeightForWidth())
        self.shibie_dropbtn.setSizePolicy(sizePolicy)
        self.shibie_dropbtn.setMinimumSize(0, 150)
        self.shibie_widget.insertWidget(0, self.shibie_dropbtn)

        self.shibie_language.addItems(config.langnamelist)
        self.shibie_model.addItems(config.model_list)
        self.shibie_startbtn.clicked.connect(self.shibie_start_fun)
        self.shibie_opendir.clicked.connect(lambda: self.opendir_fn(self.shibie_out_path))
        self.is_cuda.toggled.connect(self.check_cuda)
        self.shibie_model_type.currentIndexChanged.connect(self.model_type_change)

        # tab-4 语音合成
        self.hecheng_plaintext = Textedit()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.hecheng_plaintext.sizePolicy().hasHeightForWidth())
        self.hecheng_plaintext.setSizePolicy(sizePolicy)
        self.hecheng_plaintext.setMinimumSize(0, 150)
        self.hecheng_plaintext.setPlaceholderText(config.transobj['tuodonghuoshuru'])

        self.hecheng_importbtn = QtWidgets.QPushButton(self.tab_2)
        self.hecheng_importbtn.setObjectName("hecheng_importbtn")
        self.hecheng_importbtn.setFixedHeight(150)
        self.hecheng_importbtn.setCursor(Qt.PointingHandCursor)

        self.hecheng_importbtn.setText(config.box_lang['Import text to be translated from a file..'])
        self.hecheng_importbtn.clicked.connect(self.hecheng_import_fun)

        self.hecheng_layout.insertWidget(0, self.hecheng_importbtn)
        self.hecheng_layout.insertWidget(1, self.hecheng_plaintext)
        self.hecheng_language.addItems(['-'] + config.langnamelist)
        self.hecheng_role.addItems(['No'])
        self.hecheng_language.currentTextChanged.connect(self.hecheng_language_fun)
        self.hecheng_startbtn.clicked.connect(self.hecheng_start_fun)
        self.hecheng_opendir.clicked.connect(lambda: self.opendir_fn(self.hecheng_out.text().strip()))
        # 设置 tts_type
        self.tts_type.addItems([i for i in config.params['tts_type_list']])
        # tts_type 改变时，重设角色
        self.tts_type.currentTextChanged.connect(self.tts_type_change)
        self.tts_issrt.stateChanged.connect(self.tts_issrt_change)

        # tab-5 格式转换
        # self.geshi_input = TextGetdir()
        # sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        # sizePolicy.setHorizontalStretch(0)
        # sizePolicy.setVerticalStretch(0)
        # sizePolicy.setHeightForWidth(self.geshi_result.sizePolicy().hasHeightForWidth())
        # self.geshi_input.setSizePolicy(sizePolicy)
        # self.geshi_input.setMinimumSize(300, 0)
        #
        # self.geshi_input.setPlaceholderText(config.transobj['tuodongdaoci'])
        #
        # self.geshi_importbtn = QtWidgets.QPushButton(self.tab_6)
        # self.geshi_importbtn.setObjectName("geshi_importbtn")
        # self.geshi_importbtn.setFixedWidth(100)
        # self.geshi_importbtn.setText(config.box_lang['import audio or video'])
        # self.geshi_importbtn.clicked.connect(lambda: self.geshi_import_fun(self.geshi_input))
        # self.horizontalLayout_14.insertWidget(0, self.geshi_importbtn)
        #
        # self.geshi_layout.insertWidget(0, self.geshi_input)
        # self.geshi_mp4.clicked.connect(lambda: self.geshi_start_fun("mp4"))
        # self.geshi_avi.clicked.connect(lambda: self.geshi_start_fun("avi"))
        # self.geshi_mov.clicked.connect(lambda: self.geshi_start_fun("mov"))
        # self.geshi_mp3.clicked.connect(lambda: self.geshi_start_fun("mp3"))
        # self.geshi_wav.clicked.connect(lambda: self.geshi_start_fun("wav"))
        # self.geshi_aac.clicked.connect(lambda: self.geshi_start_fun("aac"))
        # self.geshi_m4a.clicked.connect(lambda: self.geshi_start_fun("m4a"))
        # self.geshi_flac.clicked.connect(lambda: self.geshi_start_fun("flac"))
        # self.geshi_output.clicked.connect(lambda: self.opendir_fn(f'{config.homedir}/conver'))
        # if not os.path.exists(f'{config.homedir}/conver'):
        #     os.makedirs(f'{config.homedir}/conver', exist_ok=True)

        # 混流
        self.hun_file1btn.clicked.connect(lambda: self.hun_get_file('file1'))
        self.hun_file2btn.clicked.connect(lambda: self.hun_get_file('file2'))
        self.hun_startbtn.clicked.connect(self.hun_fun)
        self.hun_opendir.clicked.connect(lambda: self.opendir_fn(self.hun_out.text()))

        self.fanyi_target.addItems(["-"] + config.langnamelist)
        self.fanyi_import.clicked.connect(self.fanyi_import_fun)
        self.fanyi_start.clicked.connect(self.fanyi_start_fun)
        self.fanyi_translate_type.addItems(translator.TRANSNAMES)

        self.fanyi_sourcetext = QPlainTextEdit()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)

        self.fanyi_sourcetext.setSizePolicy(sizePolicy)
        self.fanyi_sourcetext.setMinimumSize(300, 0)
        self.fanyi_proxy.setText(config.proxy)

        self.fanyi_sourcetext.setPlaceholderText(config.transobj['tuodongfanyi'])
        self.fanyi_sourcetext.setToolTip(config.transobj['tuodongfanyi'])
        self.fanyi_sourcetext.setReadOnly(True)

        self.fanyi_layout.insertWidget(0, self.fanyi_sourcetext)
        self.daochu.clicked.connect(self.fanyi_save_fun)
        self.statuslabel = QLabel("")

        self.statusBar.addWidget(self.statuslabel)
        self.statusBar.addPermanentWidget(QLabel("github.com/jianchang512/pyvideotrans"))

        #     日志
        self.task_logs = LogsWorker(self)
        self.task_logs.post_logs.connect(self.receiver)
        self.task_logs.start()

    def geshi_import_fun(self, obj):
        fnames, _ = QFileDialog.getOpenFileNames(self, config.transobj['selectmp4'], config.last_opendir,
                                                 "Video files(*.mp4 *.avi *.mov *.m4a *.mp3 *.aac *.flac *.wav)")
        if len(fnames) < 1:
            return
        for (i, it) in enumerate(fnames):
            fnames[i] = it.replace('\\', '/')

        if len(fnames) > 0:
            config.last_opendir = os.path.dirname(fnames[0])
            self.settings.setValue("last_dir", config.last_opendir)
            obj.setPlainText("\n".join(fnames))

    # 获取wav件
    def hun_get_file(self, name='file1'):
        fname, _ = QFileDialog.getOpenFileName(self, "Select audio", config.last_opendir,
                                               "Audio files(*.wav *.mp3 *.aac *.m4a *.flac)")
        if fname:
            fname = fname.replace('file:///', '').replace('\\', '/')
            config.last_opendir = os.path.dirname(fname)
            self.settings.setValue("last_dir", config.last_opendir)
            if name == 'file1':
                self.hun_file1.setText(fname)
            else:
                self.hun_file2.setText(fname)

    # 文本翻译，导入文本文件
    def fanyi_import_fun(self, obj=None):
        fnames, _ = QFileDialog.getOpenFileNames(self,
                                                 config.transobj['tuodongfanyi'],
                                                 config.last_opendir,
                                                 "Subtitles files(*.srt)")
        if len(fnames) < 1:
            return
        for (i, it) in enumerate(fnames):
            fnames[i] = it.replace('\\', '/').replace('file:///', '')
        if fnames:
            self.fanyi_files = fnames
            config.last_opendir = os.path.dirname(fnames[0])
            self.settings.setValue("last_dir", config.last_opendir)
            self.fanyi_sourcetext.setPlainText(f'{config.transobj["yidaorujigewenjian"]}{len(fnames)}')

    def hecheng_import_fun(self):
        fnames, _ = QFileDialog.getOpenFileNames(self, "Select srt", config.last_opendir,
                                                 "Text files(*.srt)")
        if len(fnames) < 1:
            return
        for (i, it) in enumerate(fnames):
            fnames[i] = it.replace('\\', '/').replace('file:///', '')

        if len(fnames) > 0:
            config.last_opendir = os.path.dirname(fnames[0])
            self.settings.setValue("last_dir", config.last_opendir)
            self.hecheng_files = fnames
            content = ""
            try:
                with open(fnames[0], 'r', encoding='utf-8') as f:
                    content = f.read().strip()
            except:
                with open(fnames[0], 'r', encoding='GBK') as f:
                    content = f.read().strip()
            self.hecheng_plaintext.setPlainText(content)
            self.tts_issrt.setChecked(True)
            self.tts_issrt.setDisabled(True)
            self.hecheng_importbtn.setText(
                f'导入{len(fnames)}个srt文件' if config.defaulelang == 'zh' else f'Import {len(fnames)} Subtitles')

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
        QDesktopServices.openUrl(QUrl.fromLocalFile(dirname))

    # 通知更新ui
    def receiver(self, json_data):
        data = json.loads(json_data)
        # fun_name 方法名，type类型，text具体文本
        func = data['func_name']
        type = data['type']
        if func == 'yspfl':
            if type == 'end' or type == 'error':
                self.yspfl_startbtn.setDisabled(False)
                self.yspfl_startbtn.setText(config.transobj["zhixingwc"])
                if type=='error':
                    QMessageBox.critical(self,config.transobj['anerror'],data['text'])
            else:
                self.yspfl_startbtn.setText(data['text'])
                self.yspfl_startbtn.setDisabled(True)
        elif func == 'ysphb':
            if type == 'end' or type == 'error':
                self.ysphb_startbtn.setDisabled(False)
                self.ysphb_startbtn.setText(config.transobj["zhixingwc"])
                self.ysphb_opendir.setDisabled(False)
                if type=='error':
                    QMessageBox.critical(self,config.transobj['anerror'],data['text'])
            else:
                self.ysphb_startbtn.setText(data['text'])
                self.ysphb_startbtn.setDisabled(True)
        elif func == 'shibie':
            if type == 'replace':
                self.shibie_text.clear()
                self.shibie_text.insertPlainText(data['text'])
            elif type == 'set':
                self.shibie_text.moveCursor(QTextCursor.End)
                self.shibie_text.insertPlainText(data['text'].capitalize())
            elif type == 'error' or type == 'end':
                self.disabled_shibie(False)
                if type=='end':
                    self.shibie_startbtn.setText(config.transobj["zhixingwc"])
                    self.shibie_dropbtn.setText(config.transobj['quanbuend'] + ". " + config.transobj['xuanzeyinshipin'])
                else:
                    self.shibie_dropbtn.setText(data['text'])
            else:
                self.shibie_startbtn.setText(data['text'])
        elif func == 'hecheng':
            if type=='replace':
                self.hecheng_plaintext.clear()
                self.hecheng_plaintext.setPlainText(data['text'])
            elif type == 'error' or type == 'end':
                self.hecheng_startbtn.setDisabled(False)
                self.hecheng_startbtn.setText(data['text'] if type=='error' else config.transobj["zhixingwc"])
            else:
                self.hecheng_startbtn.setText(data['text'])
        elif func == 'fanyi':
            if type == 'error' or type == 'end':
                self.fanyi_start.setDisabled(False)
                self.daochu.setDisabled(False)
                self.fanyi_start.setText(config.transobj["zhixingwc"])
                self.fanyi_sourcetext.setPlainText(config.transobj["zhixingwc"])
                if type == 'error':
                    self.fanyi_sourcetext.setPlainText(data['text'])
                    self.fanyi_targettext.moveCursor(QTextCursor.End)
                    self.fanyi_targettext.insertPlainText(data['text'])
            elif type == 'replace':
                self.fanyi_targettext.clear()
                self.fanyi_targettext.setPlainText(data['text'])
            elif type == 'set':
                self.fanyi_targettext.moveCursor(QTextCursor.End)
                self.fanyi_targettext.insertPlainText(data['text'].capitalize())
            else:
                self.fanyi_sourcetext.setPlainText(data['text'])

        elif func == 'hunhe':
            if type == 'error' or type == 'end':
                self.hun_startbtn.setDisabled(False)
                self.hun_startbtn.setText(config.transobj["zhixingwc"])
                if type=='error':
                    QMessageBox.critical(self,config.transobj['anerror'],data['text'])
            else:
                self.hun_startbtn.setText(data['text'])

    # tab-1 音视频分离启动
    def yspfl_start_fn(self):
        if not self.yspfl_video_wrap.filepath:
            return QMessageBox.critical(self, config.transobj['anerror'], config.transobj['selectvideodir'])
        file = self.yspfl_video_wrap.filepath
        basename = os.path.basename(file)
        #rs, newfile, base = tools.rename_move(file, is_dir=False)
        #if rs:
        #    file = newfile
        #    basename = base
        video_out = f"{config.homedir}/{basename}"
        if not os.path.exists(video_out):
            os.makedirs(video_out, exist_ok=True)
        self.yspfl_task = Worker(
            [['-y', '-i', file, '-an', f"{video_out}/{basename}.mp4", f"{video_out}/{basename}.wav"]], "yspfl",
            self)

        self.yspfl_task.start()
        self.yspfl_startbtn.setText(config.transobj['running'])
        self.yspfl_startbtn.setDisabled(True)

        self.yspfl_videoinput.setText(f"{video_out}/{basename}.mp4")
        self.yspfl_wavinput.setText(f"{video_out}/{basename}.wav")

    # 音视频打开目录
    def yspfl_open_fn(self, name):
        pathdir = config.homedir
        if name == "video":
            pathdir = os.path.dirname(self.yspfl_videoinput.text())
        elif name == "wav":
            pathdir = os.path.dirname(self.yspfl_wavinput.text())
        QDesktopServices.openUrl(QUrl.fromLocalFile(pathdir))

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
        fname, _ = QFileDialog.getOpenFileName(self, f"Select {showname} file", os.path.expanduser('~') + "\\Videos", mime)
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
        # 是否保留原声
        save_raw = self.ysphb_replace.isChecked()
        if not videofile or not os.path.exists(videofile):
            QMessageBox.critical(self, config.transobj['anerror'], config.transobj['selectvideodir'])
            return
        if not wavfile and not srtfile:
            QMessageBox.critical(self, config.transobj['anerror'], config.transobj['yinpinhezimu'])
            return
        if not os.path.exists(wavfile) and not os.path.exists(srtfile):
            QMessageBox.critical(self, config.transobj['anerror'], config.transobj["yinpinhezimu"])
            return

        if os.path.exists(videofile):
            rs, newfile, base = tools.rename_move(videofile, is_dir=False)
            if rs:
                videofile = newfile
                basename = base
        if os.path.exists(srtfile):
            rs, newsrtfile, _ = tools.rename_move(srtfile, is_dir=False)
            if rs:
                srtfile = newsrtfile
        if os.path.exists(wavfile):
            rs, newwavfile, _ = tools.rename_move(wavfile, is_dir=False)
            if rs:
                wavfile = newwavfile

        savedir = f"{config.homedir}/hebing-{basename}"
        os.makedirs(savedir, exist_ok=True)

        cmds = []
        if not os.path.exists(f'{config.TEMP_DIR}'):
            os.makedirs(f'{config.TEMP_DIR}', exist_ok=True)
        tmpname = f'{config.TEMP_DIR}/{time.time()}.mp4'
        tmpname_conver = f'{config.TEMP_DIR}/box-conver.mp4'
        video_info = tools.get_video_info(videofile)
        video_codec= 'h264' if config.settings['video_codec']==264 else 'hevc'
        if videofile[-3:].lower() != 'mp4' or video_info['video_codec_name'] != video_codec or (
                video_info['streams_audio'] > 0 and video_info['audio_codec_name'] != 'aac'):
            try:
                tools.conver_mp4(videofile, tmpname_conver, is_box=True)
            except Exception as e:
                QMessageBox.critical(self, config.transobj['anerror'], str(e))
                self.ysphb_startbtn.setText(config.transobj["start"])
                self.ysphb_startbtn.setDisabled(False)
                return False
            videofile = tmpname_conver

        if wavfile:
            # 视频里是否有音轨 并且保留原声音
            if video_info['streams_audio'] > 0 and save_raw:
                tmp_a = f'{config.TEMP_DIR}/box-a.m4a'

                cmds = [
                    ['-y', '-i', videofile, '-i', wavfile, '-vn', '-filter_complex',
                     "[1:a]apad[a1];[0:a][a1]amerge=inputs=2[aout]", '-map', '[aout]', '-ac', '2', tmp_a],
                    ['-y', '-i', videofile, '-i', tmp_a, '-filter_complex', "[1:a]apad", '-c:v', 'copy', '-c:a', 'aac',
                     '-shortest',
                     tmpname if srtfile else f'{savedir}/{basename}.mp4']
                ]
            else:
                cmds = [
                    ['-y', '-i', videofile, '-i', wavfile, '-filter_complex', "[1:a]apad", '-c:v', 'copy', '-c:a',
                     'aac', '-shortest',
                     tmpname if srtfile else f'{savedir}/{basename}.mp4']]

        if srtfile:
            # srtfile = srtfile.replace('\\', '/').replace(':', '\\\\:')
            basename = os.path.basename(srtfile)
            shutil.copy2(srtfile, config.rootdir + f"/{basename}.srt")
            os.chdir(config.rootdir)
            cmds.append(
                # ['-y', '-i', tmpname if wavfile else videofile, "-vf", f"subtitles={basename}.srt", '-c:v', 'libx264',
                # '-c:a', 'copy', f'{savedir}/{basename}.mp4']
                [
                    "-y",
                    "-i",
                    os.path.normpath(tmpname if wavfile else videofile),

                    "-c:v",
                    "libx264",
                    "-vf",
                    f"subtitles={basename}.srt",
                    "-shortest",
                    f'{savedir}/{basename}.mp4'
                ])
        self.ysphb_task = Worker(cmds, "ysphb", self)
        self.ysphb_task.start()

        self.ysphb_startbtn.setText(config.transobj["running"])
        self.ysphb_startbtn.setDisabled(True)
        self.ysphb_out.setText(f"{savedir}/{basename}.mp4")
        self.ysphb_opendir.setDisabled(True)

    def check_cuda(self, state):
        # 选中如果无效，则取消
        if state:
            if not torch.cuda.is_available():
                QMessageBox.critical(self, config.transobj['anerror'], config.transobj['nocuda'])
                self.is_cuda.setChecked(False)
                self.is_cuda.setDisabled(True)
            else:
                from torch.backends import cudnn
                if not cudnn.is_available() or not cudnn.is_acceptable(torch.tensor(1.).cuda()):
                    QMessageBox.critical(self, config.transobj['anerror'], config.transobj["nocudnn"])
                    self.is_cuda.setChecked(False)
                    self.is_cuda.setDisabled(True)

    # 设定模型类型
    def model_type_change(self):
        if self.shibie_model_type.currentIndex() == 1:
            model_type = 'openai'
            self.shibie_whisper_type.setDisabled(False)
            self.shibie_model.setDisabled(False)
        elif self.shibie_model_type.currentIndex() == 2:
            model_type = 'GoogleSpeech'
            self.shibie_whisper_type.setDisabled(True)
            self.shibie_model.setDisabled(True)
        elif self.shibie_model_type.currentIndex() == 3:
            model_type = 'zh_recogn'
            self.shibie_whisper_type.setDisabled(True)
            self.shibie_model.setDisabled(True)
        else:
            self.shibie_whisper_type.setDisabled(False)
            self.shibie_model.setDisabled(False)
            model_type = 'faster'

    # tab-3 语音识别 预执行，检查
    def shibie_start_fun(self):
        model = self.shibie_model.currentText()
        split_type_index = self.shibie_whisper_type.currentIndex()
        if self.shibie_model_type.currentIndex() == 1:
            model_type = 'openai'
        elif self.shibie_model_type.currentIndex() == 2:
            model_type = 'GoogleSpeech'
        elif self.shibie_model_type.currentIndex() == 3:
            model_type = 'zh_recogn'
        else:
            model_type = "faster"
        is_cuda = self.is_cuda.isChecked()
        if is_cuda and model_type == 'faster':
            allow = True
            try:
                from torch.backends import cudnn
                if not cudnn.is_available() or not cudnn.is_acceptable(torch.tensor(1.).cuda()):
                    allow = False
            except:
                allow = False
            finally:
                if not allow:
                    self.is_cuda.setChecked(False)
                    return QMessageBox.critical(self, config.transobj['anerror'], config.transobj["nocudnn"])
        if model_type == 'faster' and model.find('/')==-1:
            file = f'{config.rootdir}/models/models--Systran--faster-whisper-{model}/snapshots'
            if model.startswith('distil'):
                file = f'{config.rootdir}/models/models--Systran--faster-{model}/snapshots'
            if not os.path.exists(file):
                QMessageBox.critical(self, config.transobj['anerror'],
                                     config.transobj['downloadmodel'].replace('{name}', model))
                return
        elif model_type == 'openai' and not os.path.exists(config.rootdir + f'/models/{model}.pt'):
            return QMessageBox.critical(self, config.transobj['anerror'],
                                        config.transobj['openaimodelnot'].replace('{name}', model))
        files = self.shibie_dropbtn.filelist

        if not files or len(files) < 1:
            return QMessageBox.critical(self, config.transobj['anerror'], config.transobj['bixuyinshipin'])

        wait_list = []
        self.shibie_startbtn.setText(config.transobj["running"])
        self.disabled_shibie(True)
        self.label_shibie10.setText('')
        for file in files:
            basename = os.path.basename(file)
            '''
            try:
                rs, newfile, base = tools.rename_move(file, is_dir=False)
                if rs:
                    file = newfile
                    basename = base
            except Exception as e:
                print(f"removename {str(e)}")
            '''
            self.shibie_text.clear()

            if os.path.splitext(basename)[-1].lower() in [".mp4", ".avi", ".mov", ".mp3", ".flac", ".m4a", ".mov",
                                                          ".aac"]:
                out_file = f"{config.TEMP_HOME}/{basename}.wav"
                if not os.path.exists(f"{config.TEMP_HOME}"):
                    os.makedirs(f"{config.TEMP_HOME}")
                try:
                    self.shibie_ffmpeg_task = Worker([
                        ['-y', '-i', file, '-vn', '-ac', '1', '-ar', '8000', out_file]
                    ], "logs", self)
                    self.shibie_ffmpeg_task.start()
                    wait_list.append(out_file)
                except Exception as e:
                    config.logger.error("执行语音识别前，先从视频中分离出音频失败：" + str(e))
                    self.shibie_startbtn.setText("执行")
                    self.disabled_shibie(False)
                    QMessageBox.critical(self, config.transobj['anerror'], str(e))
            else:
                wait_list.append(file)

        self.shibie_out_path = config.homedir + f"/recogn"

        os.makedirs(self.shibie_out_path, exist_ok=True)
        self.shibie_opendir.setDisabled(False)

        self.shibie_task = WorkerWhisper(
            audio_paths=wait_list,
            model=model,
            split_type=["all", "split", "avg"][split_type_index],
            model_type=model_type,
            language=translator.get_audio_code(show_source=self.shibie_language.currentText()),
            func_name="shibie",
            out_path=self.shibie_out_path,
            is_cuda=is_cuda,
            parent=self)
        self.shibie_task.start()

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
        langcode = translator.get_code(show_text=language)

        if not txt:
            return QMessageBox.critical(self, config.transobj['anerror'], config.transobj['neirongweikong'])
        if language == '-' or role == 'No':
            return QMessageBox.critical(self, config.transobj['anerror'], config.transobj['yuyanjuesebixuan'])
        if tts_type == 'openaiTTS' and not config.params['chatgpt_key']:
            return QMessageBox.critical(self, config.transobj['anerror'],
                                        config.transobj['bixutianxie'] + "chatGPT key")
        if tts_type == 'GPT-SoVITS' and langcode[:2] not in ['zh', 'ja', 'en']:
            # 除此指望不支持
            config.params['tts_type'] = 'edgeTTS'
            self.tts_type.setCurrentText('edgeTTS')
            QMessageBox.critical(self, config.transobj['anerror'], config.transobj['nogptsovitslanguage'])
            return
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"
        volume=int(self.volume_rate.value())
        pitch=int(self.pitch_rate.value())
        volume=f'+{volume}%' if volume>=0 else f'{volume}%'
        pitch=f'+{pitch}Hz' if pitch>=0 else f'{volume}Hz'

        # 文件名称
        filename = self.hecheng_out.text()
        if os.path.exists(filename):
            filename = ''
        if filename and re.search(r'[\\/]+', filename):
            filename = ""
        if not filename:
            newrole = role.replace('/', '-').replace('\\', '-')
            filename = f"{newrole}-rate{rate.replace('%','')}-volume{volume.replace('%','')}-pitch{pitch}"
        else:
            filename = filename.replace('.wav', '')

        if not os.path.exists(f"{config.homedir}/tts"):
            os.makedirs(f"{config.homedir}/tts", exist_ok=True)

        wavname = f"{config.homedir}/tts/{filename}"



        issrt = self.tts_issrt.isChecked()
        self.hecheng_task = WorkerTTS(self,
                                      files=self.hecheng_files if len(self.hecheng_files) > 0 else txt,
                                      role=role,
                                      rate=rate,
                                      pitch=pitch,
                                      volume=volume,
                                      langcode=langcode,
                                      wavname=wavname,
                                      tts_type=self.tts_type.currentText(),
                                      func_name="hecheng",
                                      voice_autorate=issrt and self.voice_autorate.isChecked(),
                                      audio_ajust=issrt and self.audio_ajust.isChecked(),
                                      tts_issrt=issrt)
        self.hecheng_task.start()
        self.hecheng_startbtn.setText(config.transobj["running"])
        self.hecheng_startbtn.setDisabled(True)
        self.hecheng_out.setText(wavname)
        self.hecheng_out.setDisabled(True)

    def tts_issrt_change(self, state):
        if state:
            self.voice_autorate.setDisabled(False)
            self.audio_ajust.setDisabled(False)
        else:
            self.voice_autorate.setDisabled(True)
            self.audio_ajust.setDisabled(True)

    # tts类型改变
    def tts_type_change(self, type):
        if type in ['edgeTTS','AzureTTS']:
            self.volume_rate.setDisabled(False)
            self.pitch_rate.setDisabled(False)
        else:
            self.volume_rate.setDisabled(True)
            self.pitch_rate.setDisabled(True)


        if type == 'gtts':
            self.hecheng_role.clear()
            self.hecheng_role.addItems(['gtts'])
        elif type == "openaiTTS":
            self.hecheng_role.clear()
            self.hecheng_role.addItems(config.params['openaitts_role'].split(","))
        elif type == 'elevenlabsTTS':
            self.hecheng_role.clear()
            self.hecheng_role.addItems(config.params['elevenlabstts_role'])
        elif type in ['edgeTTS', 'AzureTTS']:
            self.hecheng_language_fun(self.hecheng_language.currentText())
        elif type == 'clone-voice':
            self.hecheng_role.clear()
            self.hecheng_role.addItems([it for it in config.clone_voicelist if it != 'clone'])
        elif type == 'TTS-API':
            if not config.params['ttsapi_url']:
                QMessageBox.critical(self, config.transobj['anerror'], config.transobj['ttsapi_nourl'])
                return
            self.hecheng_role.clear()
            self.hecheng_role.addItems(config.params['ttsapi_voice_role'].split(","))
        elif type == 'GPT-SoVITS':
            code = translator.get_code(show_text=self.hecheng_language.currentText())
            if code and code != '-' and code[:2] not in ['zh', 'ja', 'en']:
                self.tts_type.setCurrentText('edgeTTS')
                QMessageBox.critical(self, config.transobj['anerror'], config.transobj['nogptsovitslanguage'])
                return
            rolelist = tools.get_gptsovits_role()
            self.hecheng_role.clear()
            self.hecheng_role.addItems(list(rolelist.keys()) if rolelist else ['GPT-SoVITS'])

    # 合成语言变化，需要获取到角色
    def hecheng_language_fun(self, t):
        code = translator.get_code(show_text=t)
        if code and code != '-' and self.tts_type.currentText() == 'GPT-SoVITS' and code[:2] not in ['zh', 'ja', 'en']:
            # 除此指望不支持
            QMessageBox.critical(self, config.transobj['anerror'], config.transobj['nogptsovitslanguage'])
            self.tts_type.setCurrentText('edgeTTS')
        if self.tts_type.currentText() not in ["edgeTTS", "AzureTTS"]:
            return
        self.hecheng_role.clear()
        if t == '-':
            self.hecheng_role.addItems(['No'])
            return

        show_rolelist = get_edge_rolelist() if config.params['tts_type'] == 'edgeTTS' else get_azure_rolelist()
        if not show_rolelist:
            show_rolelist = get_edge_rolelist()
        if not show_rolelist:
            self.hecheng_language.setCurrentText('-')
            QMessageBox.critical(self, config.transobj['anerror'], config.transobj['nojueselist'])
            return

        try:
            vt = code.split('-')[0]
            if vt not in show_rolelist:
                self.hecheng_role.addItems(['No'])
                return
            if len(show_rolelist[vt]) < 2:
                self.hecheng_language.setCurrentText('-')
                QMessageBox.critical(self, config.transobj['anerror'], config.transobj['waitrole'])
                return
            self.hecheng_role.addItems(show_rolelist[vt])
        except:
            self.hecheng_role.addItems(['No'])

    # 音频混流
    def hun_fun(self):
        out = self.hun_out.text().strip()
        if out and os.path.isfile(out):
            out = ""
        if not out:
            out = f'{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}.wav'
        elif not out.endswith('.wav'):
            out += '.wav'
            out = out.replace('\\', '').replace('/', '')
        dirname = config.homedir + "/hun_liu"
        if not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)
        savename = f'{dirname}/{out}'

        self.hun_out.setText(savename)

        file1 = self.hun_file1.text()
        file2 = self.hun_file2.text()

        #rs, newfile1, _ = tools.rename_move(file1, is_dir=False)
        #if rs:
        #    file1 = newfile1
        #rs, newfile2, _ = tools.rename_move(file2, is_dir=False)
        #if rs:
        #    file2 = newfile2

        cmd = ['-y', '-i', file1, '-i', file2, '-filter_complex',
               "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2", '-ac', '2', savename]
        self.geshi_task = Worker([cmd], "hunhe", self)
        self.geshi_task.start()
        self.hun_startbtn.setDisabled(True)
        self.hun_out.setDisabled(True)

    # 翻译开始
    def fanyi_start_fun(self):
        target_language = self.fanyi_target.currentText()
        translate_type = self.fanyi_translate_type.currentText()
        if target_language == '-':
            return QMessageBox.critical(self, config.transobj['anerror'], config.transobj["fanyimoshi1"])
        proxy = self.fanyi_proxy.text()

        if proxy:
            tools.set_proxy(proxy)
            self.settings.setValue('proxy', proxy)
            config.proxy = proxy
        else:
            proxy = self.settings.value("proxy", "", str)
            if proxy:
                tools.set_proxy(proxy)
                config.proxy = proxy
                self.settings.setValue('proxy', proxy)
                if translate_type.lower() == GOOGLE_NAME:
                    self.fanyi_proxy.setText(proxy)

        config.params["baidu_appid"] = self.settings.value("baidu_appid", "")
        config.params["baidu_miyue"] = self.settings.value("baidu_miyue", "")
        config.params["deepl_authkey"] = self.settings.value("deepl_authkey", "")
        config.params["deeplx_address"] = self.settings.value("deeplx_address", "")
        config.params["chatgpt_api"] = self.settings.value("chatgpt_api", "")
        config.params["chatgpt_key"] = self.settings.value("chatgpt_key", "")
        config.params["tencent_SecretId"] = self.settings.value("tencent_SecretId", "")
        config.params["tencent_SecretKey"] = self.settings.value("tencent_SecretKey", "")
        config.params["gemini_key"] = self.settings.value("gemini_key", "")
        config.params["azure_api"] = self.settings.value("azure_api", "")
        config.params["azure_key"] = self.settings.value("azure_key", "")
        config.params["azure_model"] = self.settings.value("azure_model", "")

        rs = translator.is_allow_translate(translate_type=translate_type, show_target=target_language)
        if rs is not True:
            QMessageBox.critical(self, config.transobj['anerror'], rs)
            return
        self.fanyi_sourcetext.clear()
        self.fanyi_task = FanyiWorker(translate_type, target_language, self.fanyi_files, self)
        self.fanyi_task.start()
        self.fanyi_start.setDisabled(True)
        self.fanyi_start.setText(config.transobj["running"])
        self.fanyi_targettext.clear()
        self.daochu.setDisabled(True)

    def fanyi_save_fun(self):
        target = os.path.join(os.path.dirname(self.fanyi_files[0]), '_translate')
        if len(self.fanyi_files) < 1 or not os.path.exists(target):
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(target))
