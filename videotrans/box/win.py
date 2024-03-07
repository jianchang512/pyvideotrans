# -*- coding: utf-8 -*-
import datetime
import json
import os
import re
import time

import torch
from PySide6 import QtWidgets
from PySide6.QtCore import QSettings, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QTextCursor
from PySide6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QLabel
from videotrans import VERSION
from videotrans.box.component import Player, DropButton, Textedit, TextGetdir
from videotrans.box.logs_worker import LogsWorker
from videotrans.box.worker import Worker, WorkerWhisper, WorkerTTS, FanyiWorker
from videotrans.configure import config
from videotrans  import translator
from videotrans.translator import GOOGLE_NAME
from videotrans.util  import tools
import shutil
from videotrans.ui.toolboxen import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.initSize=None
        self.shibie_out_path=None
        self.initUI()
        self.setWindowIcon(QIcon(f"{config.rootdir}/videotrans/styles/icon.ico"))
        self.setWindowTitle(f"VideoTrans{config.uilanglist['Video Toolbox']} {VERSION}  {' Q群 608815898 微信公众号 pyvideotrans ' if config.defaulelang=='zh' else ''}")

    def closeEvent(self, event):
        # 拦截窗口关闭事件，隐藏窗口而不是真正关闭
        self.hide()
        event.ignore()

    def hideWindow(self):
        # 示例按钮点击时调用，隐藏窗口
        self.hide()

    def initUI(self):
        if not os.path.exists(config.homedir):
            os.makedirs(config.homedir, exist_ok=True)
        if not os.path.exists(config.homedir + "/tmp"):
            os.makedirs(config.homedir + "/tmp", exist_ok=True)
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
        self.shibie_model.addItems(["base", "small", "medium", "large-v2","large-v3"])
        self.shibie_startbtn.clicked.connect(self.shibie_start_fun)
        self.shibie_opendir.clicked.connect(lambda :self.opendir_fn(self.shibie_out_path))
        self.is_cuda.toggled.connect(self.check_cuda)

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
        self.hecheng_importbtn.setFixedWidth(100)
        self.hecheng_importbtn.setText(config.box_lang['Import text to be translated from a file..'])
        self.hecheng_importbtn.clicked.connect(lambda:self.fanyi_import_fun(self.hecheng_plaintext))

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
        self.geshi_input = TextGetdir()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.geshi_result.sizePolicy().hasHeightForWidth())
        self.geshi_input.setSizePolicy(sizePolicy)
        self.geshi_input.setMinimumSize(300, 0)

        self.geshi_input.setPlaceholderText(config.transobj['tuodongdaoci'])

        self.geshi_importbtn = QtWidgets.QPushButton(self.tab_6)
        self.geshi_importbtn.setObjectName("geshi_importbtn")
        self.geshi_importbtn.setFixedWidth(100)
        self.geshi_importbtn.setText(config.box_lang['import audio or video'])
        self.geshi_importbtn.clicked.connect(lambda :self.geshi_import_fun(self.geshi_input))
        self.horizontalLayout_14.insertWidget(0,self.geshi_importbtn)

        self.geshi_layout.insertWidget(0, self.geshi_input)
        self.geshi_mp4.clicked.connect(lambda: self.geshi_start_fun("mp4"))
        self.geshi_avi.clicked.connect(lambda: self.geshi_start_fun("avi"))
        self.geshi_mov.clicked.connect(lambda: self.geshi_start_fun("mov"))
        self.geshi_mp3.clicked.connect(lambda: self.geshi_start_fun("mp3"))
        self.geshi_wav.clicked.connect(lambda: self.geshi_start_fun("wav"))
        self.geshi_aac.clicked.connect(lambda: self.geshi_start_fun("aac"))
        self.geshi_m4a.clicked.connect(lambda: self.geshi_start_fun("m4a"))
        self.geshi_flac.clicked.connect(lambda: self.geshi_start_fun("flac"))
        self.geshi_output.clicked.connect(lambda: self.opendir_fn(f'{config.homedir}/conver'))
        if not os.path.exists(f'{config.homedir}/conver'):
            os.makedirs(f'{config.homedir}/conver', exist_ok=True)

        # 混流
        self.hun_file1btn.clicked.connect(lambda: self.hun_get_file('file1'))
        self.hun_file2btn.clicked.connect(lambda: self.hun_get_file('file2'))
        self.hun_startbtn.clicked.connect(self.hun_fun)
        self.hun_opendir.clicked.connect(lambda: self.opendir_fn(self.hun_out.text()))


        self.fanyi_target.addItems(["-"] + config.langnamelist)
        self.fanyi_import.clicked.connect(self.fanyi_import_fun)
        self.fanyi_start.clicked.connect(self.fanyi_start_fun)
        self.fanyi_translate_type.addItems(translator.TRANSNAMES)

        self.fanyi_sourcetext = Textedit()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)

        self.fanyi_sourcetext.setSizePolicy(sizePolicy)
        self.fanyi_sourcetext.setMinimumSize(300, 0)
        self.fanyi_proxy.setText(config.proxy)

        self.fanyi_sourcetext.setPlaceholderText(config.transobj['tuodongfanyi'])

        self.fanyi_layout.insertWidget(0, self.fanyi_sourcetext)
        self.daochu.clicked.connect(self.fanyi_save_fun)
        self.statuslabel = QLabel("")

        self.statusBar.addWidget(self.statuslabel)
        self.statusBar.addPermanentWidget(QLabel("github.com/jianchang512/pyvideotrans"))

        #     日志
        self.task_logs = LogsWorker(self)
        self.task_logs.post_logs.connect(self.receiver)
        self.task_logs.start()
        # self.show()

    def geshi_import_fun(self,obj):
        fnames, _ = QFileDialog.getOpenFileNames(self, config.transobj['selectmp4'], config.last_opendir,
                                                 "Video files(*.mp4 *.avi *.mov *.m4a *.mp3 *.aac *.flac *.wav)")
        if len(fnames) < 1:
            return
        for (i, it) in enumerate(fnames):
            fnames[i] = it.replace('\\', '/')

        if len(fnames) > 0:
            config.last_opendir=os.path.dirname(fnames[0])
            self.settings.setValue("last_dir", config.last_opendir)
            obj.setPlainText("\n".join(fnames))

    # 获取wav件
    def hun_get_file(self, name='file1'):
        fname, _ = QFileDialog.getOpenFileName(self, "Select audio", config.last_opendir,
                                               "Audio files(*.wav *.mp3 *.aac *.m4a *.flac)")
        if fname:
            fname=fname.replace('file:///', '').replace('\\', '/')
            config.last_opendir=os.path.dirname(fname)
            self.settings.setValue("last_dir", config.last_opendir)
            if name == 'file1':
                self.hun_file1.setText(fname)
            else:
                self.hun_file2.setText(fname)

    # 文本翻译，导入文本文件
    def fanyi_import_fun(self, obj=None):
        fname, _ = QFileDialog.getOpenFileName(self, "Select txt or srt", config.last_opendir,
                                               "Text files(*.srt *.txt)")
        if fname:
            fname=fname.replace('file:///', '')
            config.last_opendir=os.path.dirname(fname)
            self.settings.setValue("last_dir", config.last_opendir)
            try:
                with open(fname, 'r', encoding='utf-8') as f:
                    content=f.read().strip()
            except:
                with open(fname, 'r', encoding='GBK') as f:
                    content=f.read().strip()
            if obj and not isinstance(obj,bool):
                return obj.setPlainText(content)
            else:
                self.fanyi_sourcetext.setPlainText(content)
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
        # QDesktopServices.openUrl(QUrl(f"file:{dirname.strip()}"))

    # 通知更新ui
    def receiver(self, json_data):
        data = json.loads(json_data)
        # fun_name 方法名，type类型，text具体文本

        if data['func_name'] == "yspfl_end":
            # 音视频分离完成了
            self.yspfl_startbtn.setText(config.transobj["zhixingwc"] if data['type'] == "end" else config.transobj["zhixinger"])
            self.yspfl_startbtn.setDisabled(False)
            self.statuslabel.setText("Succeed")
        elif data['func_name'] == 'ysphb_end':
            self.ysphb_startbtn.setText(config.transobj["zhixingwc"] if data['type'] == "end" else config.transobj["zhixinger"])
            self.ysphb_startbtn.setDisabled(False)
            self.ysphb_opendir.setDisabled(False)
            if data['type'] == 'end':
                self.statuslabel.setText("Succeed")
                basename = os.path.basename(self.ysphb_videoinput.text())
                if os.path.exists(config.rootdir + f"/{basename}.srt"):
                    os.unlink(config.rootdir + f"/{basename}.srt")
        elif data['func_name'] == "shibie_end":
            # 识别执行完成
            self.disabled_shibie(False)
            if data['type'] == 'replace_subtitle':
                self.shibie_text.clear()
                text,per=data['text'].split('@@@@@@')
                self.shibie_text.insertPlainText(text)
                self.shibie_startbtn.setText(config.transobj["ing"]+per)
            elif data['type']=='allend':
                self.shibie_startbtn.setText(config.transobj["zhixingwc"])
                self.statuslabel.setText("Succeed")
                self.shibie_dropbtn.setText(config.transobj['quanbuend']+". "+config.transobj['xuanzeyinshipin'])
                if data['text']:
                    self.label_shibie10.setText(data['text'])
                    self.label_shibie10.setStyleSheet('''color:#ff0000''')
                    QMessageBox.critical(self,config.transobj['anerror'],data['text'])
            else:
                self.shibie_dropbtn.setText(data['text'])
        elif data['func_name'] == 'hecheng_end':
            if data['type'] == 'end':
                self.hecheng_startbtn.setText(config.transobj["zhixingwc"])
                self.hecheng_startbtn.setToolTip(config.transobj["zhixingwc"])
                self.statuslabel.setText("Succeed")
            else:
                self.hecheng_startbtn.setText(data['text'])
                self.hecheng_startbtn.setToolTip(data['text'])
                self.hecheng_startbtn.setStyleSheet("""color:#ff0000""")
                QMessageBox.critical(self,config.transobj['anerror'],data['text'])
            self.hecheng_startbtn.setDisabled(False)
        elif data['func_name'] == 'geshi_end':
            config.geshi_num -= 1
            self.geshi_result.moveCursor(QTextCursor.End)
            self.geshi_result.insertPlainText("\n"+data['text'])
            if config.geshi_num <= 0:
                self.disabled_geshi(False)
                self.geshi_result.moveCursor(QTextCursor.End)
                self.geshi_result.insertPlainText(config.transobj["zhixingwc"])
                self.geshi_input.clear()
                self.statuslabel.setText("Succeed")
        elif data['func_name'] == 'hun_end':
            self.hun_startbtn.setDisabled(False)
            self.hun_out.setDisabled(False)
            self.statuslabel.setText("Succeed")
        elif data['func_name'] == 'fanyi_end':
            print(f'翻译结束={data["text"]}')
            self.fanyi_start.setDisabled(False)
            self.fanyi_start.setText(config.transobj['starttrans'])
            self.fanyi_targettext.clear()
            self.fanyi_targettext.setPlainText(data['text'])
            self.daochu.setDisabled(False)
            self.statuslabel.setText("Translate end")
        elif data['func_name']=='set_fanyi':
            print(f'翻译结果=={data=}')
            self.fanyi_targettext.moveCursor(QTextCursor.End)
            self.fanyi_targettext.insertPlainText(data['text'].capitalize())
        elif data['func_name']=='set_subtitle':
            self.shibie_text.moveCursor(QTextCursor.End)
            self.shibie_text.insertPlainText(data['text'].capitalize())
        elif "func_name" not in data or not data['func_name']:
            self.statuslabel.setText(data['text'][:60])
            if data['type'] == 'error':
                self.statuslabel.setStyle("""color:#ff0000""")
                QMessageBox.critical(self,config.transobj['anerror'],data['text'])
        else:
            self.statuslabel.setText(data['text'])

    # tab-1 音视频分离启动
    def yspfl_start_fn(self):
        if not self.yspfl_video_wrap.filepath:
            return QMessageBox.critical(self, config.transobj['anerror'], config.transobj['selectvideodir'])
        file = self.yspfl_video_wrap.filepath
        basename = os.path.basename(file)
        rs,newfile,base=tools.rename_move(file,is_dir=False)
        if rs:
            file=newfile
            basename=base
        video_out = f"{config.homedir}/{basename}"
        if not os.path.exists(video_out):
            os.makedirs(video_out, exist_ok=True)
        self.yspfl_task = Worker(
            [['-y', '-i', file, '-an', f"{video_out}/{basename}.mp4", f"{video_out}/{basename}.wav"]], "yspfl_end",
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
        # QDesktopServices.openUrl(QUrl(f"file:{pathdir}"))
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
        fname, _ = QFileDialog.getOpenFileName(self, f"Select {showname} file", os.path.expanduser('~') + "\\Videos",
                                               mime)
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
        save_raw=self.ysphb_replace.isChecked()
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
            rs,newfile,base=tools.rename_move(videofile,is_dir=False)
            if rs:
                videofile=newfile
                basename=base
        if os.path.exists(srtfile):
            rs,newsrtfile,_=tools.rename_move(srtfile,is_dir=False)
            if rs:
                srtfile=newsrtfile
        if os.path.exists(wavfile):
            rs,newwavfile,_=tools.rename_move(wavfile,is_dir=False)
            if rs:
             wavfile=newwavfile



        savedir = f"{config.homedir}/hebing-{basename}"
        os.makedirs(savedir, exist_ok=True)

        cmds = []
        if not os.path.exists(f'{config.rootdir}/tmp'):
            os.makedirs(f'{config.rootdir}/tmp', exist_ok=True)
        tmpname = f'{config.rootdir}/tmp/{time.time()}.mp4'
        tmpname_conver = f'{config.rootdir}/tmp/box-conver.mp4'
        video_info = tools.get_video_info(videofile)
        if videofile[-3:].lower() != 'mp4' or video_info['video_codec_name'] != 'h264' or (
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
                tmp_a = f'{config.rootdir}/tmp/box-a.m4a'
                
                cmds = [
                    ['-y', '-i', videofile, '-i', wavfile,'-vn', '-filter_complex',
               "[1:a]apad[a1];[0:a][a1]amerge=inputs=2[aout]", '-map','[aout]','-ac', '2', tmp_a],
                    ['-y', '-i', videofile, '-i', tmp_a, '-filter_complex', "[1:a]apad", '-c:v', 'copy', '-c:a', 'aac','-shortest',
                     tmpname if srtfile else f'{savedir}/{basename}.mp4']
                ]
            else:
                cmds = [
                    ['-y', '-i', videofile, '-i', wavfile, '-filter_complex', "[1:a]apad", '-c:v', 'copy', '-c:a', 'aac','-shortest',
                     tmpname if srtfile else f'{savedir}/{basename}.mp4']]

        if srtfile:
            #srtfile = srtfile.replace('\\', '/').replace(':', '\\\\:')
            basename=os.path.basename(srtfile)
            shutil.copy2(srtfile, config.rootdir + f"/{basename}.srt")
            os.chdir(config.rootdir)
            cmds.append(
                #['-y', '-i', tmpname if wavfile else videofile, "-vf", f"subtitles={basename}.srt", '-c:v', 'libx264',
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
                ]
                 
                 )
        self.ysphb_task = Worker(cmds, "ysphb_end", self)
        self.ysphb_task.start()

        self.ysphb_startbtn.setText(config.transobj["running"])
        self.ysphb_startbtn.setDisabled(True)
        self.ysphb_out.setText(f"{savedir}/{basename}.mp4")
        self.ysphb_opendir.setDisabled(True)

    def check_cuda(self, state):
        # 选中如果无效，则取消
        if state and not torch.cuda.is_available():
            QMessageBox.critical(self, config.transobj['anerror'], config.transobj['nocuda'])
            self.is_cuda.setChecked(False)
            self.is_cuda.setDisabled(True)

    # tab-3 语音识别 预执行，检查
    def shibie_start_fun(self):
        model = self.shibie_model.currentText()
        split_type_index=self.shibie_whisper_type.currentIndex()
        model_type="faster" if self.shibie_model_type.currentIndex()==0 else 'openai'
        is_cuda=self.is_cuda.isChecked()
        if is_cuda and model_type == 'faster':
            allow=True
            try:
                from torch.backends import cudnn
                if not cudnn.is_available() or not cudnn.is_acceptable(torch.tensor(1.).cuda()):
                    allow=False
            except:
                allow=False
            finally:
                if not allow:
                    self.is_cuda.setChecked(False)
                    return QMessageBox.critical(self, config.transobj['anerror'], config.transobj["nocudnn"])
        if model_type=='faster' and not os.path.exists(config.rootdir + f"/models/models--Systran--faster-whisper-{model}"):
            return QMessageBox.critical(self, config.transobj['anerror'], config.transobj['downloadmodel'].replace('{name}',model))
        elif model_type=='openai' and not os.path.exists(config.rootdir+f'/models/{model}.pt'):
            return QMessageBox.critical(self, config.transobj['anerror'], config.transobj['openaimodelnot'].replace('{name}',model))
        files = self.shibie_dropbtn.filelist

        if not files or len(files)<1:
            return QMessageBox.critical(self, config.transobj['anerror'], config.transobj['bixuyinshipin'])


        wait_list=[]
        self.shibie_startbtn.setText(config.transobj["running"])
        self.disabled_shibie(True)
        self.label_shibie10.setText('')
        print('33')
        for file in files:
            basename = os.path.basename(file)
            print(f'{basename=}')
            try:
                rs,newfile,base=tools.rename_move(file,is_dir=False)
                if rs:
                    file=newfile
                    basename=base
            except Exception as e:
                print(f"removename {str(e)}")
            self.shibie_text.clear()

            if os.path.splitext(basename)[-1].lower() in [".mp4", ".avi", ".mov",".mp3",".flac",".m4a",".mov",".aac"]:
                out_file = f"{config.homedir}/tmp/{basename}.wav"
                if not os.path.exists(f"{config.homedir}/tmp"):
                    os.makedirs(f"{config.homedir}/tmp")
                try:
                    self.shibie_ffmpeg_task = Worker([
                        ['-y', '-i', file,'-vn','-ac','1','-ar','8000', out_file]
                    ],"logs", self)
                    self.shibie_ffmpeg_task.start()
                    wait_list.append(out_file)
                except Exception as e:
                    config.logger.error("执行语音识别前，先从视频中分离出音频失败：" + str(e))
                    self.shibie_startbtn.setText("执行")
                    self.disabled_shibie(False)
                    QMessageBox.critical(self, config.transobj['anerror'], str(e))
            else:
                print('66')
                wait_list.append(file)

        self.shibie_out_path=config.homedir+f"/recogn"

        os.makedirs(self.shibie_out_path,exist_ok=True)
        self.shibie_opendir.setDisabled(False)

        self.shibie_task = WorkerWhisper(
            audio_paths=wait_list,
            model=model,
            split_type= ["all","split","avg"][split_type_index],
            model_type=model_type,
            language=translator.get_audio_code(show_source=self.shibie_language.currentText()),
            func_name="shibie_end",
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
        print(f'{language=},{langcode=}')

        if not txt:
            return QMessageBox.critical(self, config.transobj['anerror'], config.transobj['neirongweikong'])
        if language == '-' or role == 'No':
            return QMessageBox.critical(self, config.transobj['anerror'], config.transobj['yuyanjuesebixuan'])
        if tts_type == 'openaiTTS' and not config.params['chatgpt_key']:
            return QMessageBox.critical(self, config.transobj['anerror'], config.transobj['bixutianxie'] + "chatGPT key")
        if  tts_type =='GPT-SoVITS' and langcode[:2] not in ['zh','ja','en']:
            #除此指望不支持
            config.params['tts_type']='edgeTTS'
            self.tts_type.setCurrentText('edgeTTS')
            QMessageBox.critical(self,config.transobj['anerror'],config.transobj['nogptsovitslanguage'])
            return

        # 文件名称
        filename = self.hecheng_out.text()
        if os.path.exists(filename):
            filename=''
        if filename and re.search(r'[\\/]+', filename):
            filename = ""
        if not filename:
            newrole=role.replace('/','-').replace('\\','-')
            filename = f"tts-{newrole}-{rate}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.wav"
        else:
            filename = filename.replace('.wav', '') + ".wav"
        if not os.path.exists(f"{config.homedir}/tts"):
            os.makedirs(f"{config.homedir}/tts", exist_ok=True)
        wavname = f"{config.homedir}/tts/{filename}"
        
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"

        issrt = self.tts_issrt.isChecked()
        self.hecheng_task = WorkerTTS(self,
                                      text=txt,
                                      role=role,
                                      rate=rate,
                                      langcode=langcode,
                                      filename=wavname,
                                      tts_type=self.tts_type.currentText(),
                                      func_name="hecheng_end",
                                      voice_autorate=issrt and self.voice_autorate.isChecked(),
                                      tts_issrt=issrt)
        self.hecheng_task.start()
        self.hecheng_startbtn.setText(config.transobj["running"])
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
        elif type == 'elevenlabsTTS':
            self.hecheng_role.clear()
            self.hecheng_role.addItems(config.params['elevenlabstts_role'])
        elif type == 'edgeTTS':
            self.hecheng_language_fun(self.hecheng_language.currentText())
        elif type=='clone-voice':
            self.hecheng_role.clear()
            self.hecheng_role.addItems([it for it in config.clone_voicelist if it !='clone'])
        elif type=='TTS-API':
            if not config.params['ttsapi_url']:
                QMessageBox.critical(self,config.transobj['anerror'],config.transobj['ttsapi_nourl'])
                return
            self.hecheng_role.clear()
            self.hecheng_role.addItems(config.params['ttsapi_voice_role'].split(","))
        elif type=='GPT-SoVITS':
            code=translator.get_code(show_text=self.hecheng_language.currentText())
            if code and code !='-' and code[:2] not in ['zh','ja','en']:
                self.tts_type.setCurrentText('edgeTTS')
                QMessageBox.critical(self,config.transobj['anerror'],config.transobj['nogptsovitslanguage'])
                return
            rolelist=tools.get_gptsovits_role()
            self.hecheng_role.clear()
            self.hecheng_role.addItems(list(rolelist.keys()) if rolelist else ['GPT-SoVITS'])
    # 合成语言变化，需要获取到角色
    def hecheng_language_fun(self, t):
        code = translator.get_code(show_text=t)
        if code and code !='-' and self.tts_type.currentText()=='GPT-SoVITS' and code[:2] not in ['zh','ja','en']:
            #除此指望不支持
            self.tts_type.setCurrentText('edgeTTS')
        if self.tts_type.currentText() != "edgeTTS":
            return
        self.hecheng_role.clear()
        if t == '-':
            self.hecheng_role.addItems(['No'])
            return
        if not config.edgeTTS_rolelist:
            config.edgeTTS_rolelist = tools.get_edge_rolelist()
        if not config.edgeTTS_rolelist:
            self.hecheng_language.setCurrentText('-')
            QMessageBox.critical(self, config.transobj['anerror'], config.transobj['nojueselist'])
            return

        try:
            vt = code.split('-')[0]
            if vt not in config.edgeTTS_rolelist:
                self.hecheng_role.addItems(['No'])
                return
            if len(config.edgeTTS_rolelist[vt]) < 2:
                self.hecheng_language.setCurrentText('-')
                QMessageBox.critical(self, config.transobj['anerror'], config.transobj['waitrole'])
                return
            self.hecheng_role.addItems(config.edgeTTS_rolelist[vt])
        except:
            self.hecheng_role.addItems(['No'])

    # tab-5 转换
    def geshi_start_fun(self, ext):
        filelist = self.geshi_input.toPlainText().strip().split("\n")
        filelist_vail = []
        for it in filelist:
            if it and os.path.exists(it) and it.split('.')[-1].lower() in ['mp4', 'avi', 'mov', 'mp3', 'wav', 'aac',
                                                                           'm4a', 'flac']:
                filelist_vail.append(it)
        if len(filelist_vail) < 1:
            return QMessageBox.critical(self, config.transobj['anerror'], config.transobj['nowenjian'])
        self.geshi_input.setPlainText("\n".join(filelist_vail))
        self.disabled_geshi(True)
        config.geshi_num = len(filelist_vail)
        cmdlist = []
        savedir = f"{config.homedir}/conver"
        if not os.path.exists(savedir):
            os.makedirs(savedir, exist_ok=True)
        for it in filelist_vail:
            basename = os.path.basename(it)
            ext_this = basename.split('.')[-1].lower()
            if ext == ext_this:
                config.geshi_num -= 1
                self.geshi_result.insertPlainText(f"{it} -> {ext}")

                continue
            if ext_this in ["wav", "mp3", "aac", "m4a", "flac"] and ext in ["mp4", "mov", "avi"]:
                self.geshi_result.insertPlainText(f"{it} {config.transobj['yinpinbuke']} {ext} ")
                config.geshi_num -= 1

                continue

            self.geshi_result.insertPlainText(f'{savedir}/{basename}.{ext}')
            cmdlist.append(['-y', '-i', f'{it}', f'{savedir}/{basename}.{ext}'])

        if len(cmdlist) < 1:
            self.geshi_result.insertPlainText(config.transobj["quanbuend"])
            self.disabled_geshi(False)
            return
        self.geshi_task = Worker(cmdlist, "geshi_end", self, True)
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

        rs, newfile1, _ = tools.rename_move(file1, is_dir=False)
        if rs:
            file1 = newfile1
        rs, newfile2, _ = tools.rename_move(file2, is_dir=False)
        if rs:
            file2 = newfile2

        cmd = ['-y', '-i', file1, '-i', file2, '-filter_complex',
               "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2", '-ac', '2', savename]
        self.geshi_task = Worker([cmd], "hun_end", self, True)
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
        print(f'{proxy=}')
        if proxy:
            tools.set_proxy(proxy)
            self.settings.setValue('proxy',proxy)
        else:
            proxy = self.settings.value("proxy", "", str)
            if proxy:
                tools.set_proxy(proxy)
                self.settings.setValue('proxy',proxy)
                if translate_type.lower()==GOOGLE_NAME:
                    self.fanyi_proxy.setText(proxy)
        issrt = self.fanyi_issrt.isChecked()
        source_text = self.fanyi_sourcetext.toPlainText().strip()
        if not source_text:
            return QMessageBox.critical(self, config.transobj['anerror'], config.transobj["wenbenbukeweikong"])

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

        rs=translator.is_allow_translate(translate_type=translate_type,show_target=target_language)
        if rs is not True:
            QMessageBox.critical(self, config.transobj['anerror'], rs)
            return
        self.fanyi_task = FanyiWorker(translate_type, target_language, source_text, issrt, self)
        self.fanyi_task.start()
        self.fanyi_start.setDisabled(True)
        self.fanyi_start.setText(config.transobj["running"])
        self.fanyi_targettext.clear()
        self.daochu.setDisabled(True)

    def fanyi_save_fun(self):
        srttxt = self.fanyi_targettext.toPlainText().strip()
        if not srttxt:
            return QMessageBox.critical(self, config.transobj['anerror'], config.transobj['srtisempty'])
        issrt = self.fanyi_issrt.isChecked()
        dialog = QFileDialog()
        dialog.setWindowTitle(config.transobj['savesrtto'])
        dialog.setNameFilters(["subtitle files (*.srt)" if issrt else "text files (*.txt)"])
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.exec_()
        if not dialog.selectedFiles():  # If the user closed the choice window without selecting anything.
            return
        else:
            path_to_file = dialog.selectedFiles()[0]
        ext = ".srt" if issrt else ".txt"
        if path_to_file.endswith('.srt') or path_to_file.endswith('.txt'):
            path_to_file = path_to_file[:-4] + ext
        else:
            path_to_file += ext
        with open(path_to_file, "w",encoding='utf-8') as file:
            file.write(srttxt)
