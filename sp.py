# -*- coding: utf-8 -*-
import datetime
import json
import shutil
import sys
import os
import threading
import time
import webbrowser

from PyQt5 import QtWidgets
from PyQt5.QtGui import QTextCursor, QIcon, QDesktopServices
from PyQt5.QtCore import pyqtSignal, QThread, QSettings, QUrl
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QFileDialog, QLabel
import warnings

from videotrans.task.logs_worker import LogsWorker
from videotrans.task.main_worker import Worker, WorkerOnlyDubbing
from videotrans.task.play_audio import PlayMp3

warnings.filterwarnings('ignore')

from videotrans import VERSION
from videotrans.component import DeepLForm, DeepLXForm, BaiduForm, TencentForm, ChatgptForm
from videotrans.component.controlobj import TextGetdir
from videotrans.configure.config import langlist, transobj, logger, queue_logs, homedir
from videotrans.configure.language import english_code_bygpt
from videotrans.util.tools import recognition_translation_all, recognition_translation_split, runffmpeg, \
    delete_temp, dubbing, \
    show_popup, compos_video, set_proxy, set_process, get_edge_rolelist, text_to_speech, is_vlc
from videotrans.configure import config
import pygame

if config.defaulelang == "zh":
    from videotrans.ui.cn import Ui_MainWindow
else:
    from videotrans.ui.en import Ui_MainWindow


# primary ui
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.initUI()
        self.setWindowIcon(QIcon("./icon.ico"))
        self.setWindowTitle(
            f"{'视频翻译配音' if config.defaulelang != 'en' else ' Video Translate & Dubbing'} {VERSION}")

    def initUI(self):
        self.settings = QSettings("Jameson", "VideoTranslate")
        # 获取最后一次选择的目录
        self.last_dir = self.settings.value("last_dir", ".", str)
        # language code
        self.languagename = list(langlist.keys())
        # task thread
        self.task = None

        self.get_setting()

        self.splitter.setSizes([830, 350])

        # start
        self.startbtn.clicked.connect(self.check_start)
        # subtitle btn
        self.continue_compos.hide()
        self.continue_compos.clicked.connect(self.update_subtitle)

        # select and save
        self.btn_get_video.clicked.connect(self.get_mp4)
        self.source_mp4.setAcceptDrops(True)
        self.btn_save_dir.clicked.connect(self.get_save_dir)
        self.target_dir.setAcceptDrops(True)
        self.proxy.setText(config.video['proxy'])
        self.open_targetdir.clicked.connect(lambda: self.open_dir(self.target_dir.text()))

        # language
        self.source_language.addItems(self.languagename)
        self.source_language.setCurrentIndex(2)

        # 目标语言改变时，如果当前tts是 edgeTTS，则根据目标语言去修改显示的角色
        self.target_language.addItems(["-"] + self.languagename)
        # 目标语言改变
        self.target_language.currentTextChanged.connect(self.set_voice_role)

        self.listen_btn.hide()
        self.listen_btn.clicked.connect(self.listen_voice_fun)

        #  translation type
        self.translate_type.addItems(["google", "baidu", "chatGPT", "tencent", "DeepL", "DeepLX", "baidu(noKey)"])
        self.translate_type.setCurrentText(config.video['translate_type'])
        self.translate_type.currentTextChanged.connect(self.set_translate_type)

        #         model
        self.whisper_type.addItems([transobj['whisper_type_all'], transobj['whisper_type_split']])
        self.whisper_type.currentIndexChanged.connect(self.check_whisper_type)
        if config.video['whisper_type']:
            self.whisper_type.setCurrentIndex(0 if config.video['whisper_type'] == 'all' else 1)
        self.whisper_model.addItems(['base', 'small', 'medium', 'large', 'large-v3'])
        self.whisper_model.setCurrentText(config.video['whisper_model'])
        self.whisper_model.currentTextChanged.connect(self.check_whisper_model)

        #
        self.voice_rate.setText(config.video['voice_rate'])
        self.voice_silence.setText(config.video['voice_silence'])
        self.voice_autorate.setChecked(config.video['voice_autorate'])
        # 设置角色类型，如果当前是OPENTTS或 coquiTTS则设置，如果是edgeTTS，则为No
        if config.video['tts_type'] == 'edgeTTS':
            self.voice_role.addItems(['No'])
        elif config.video['tts_type'] == 'openaiTTS':
            self.voice_role.addItems(config.video['openaitts_role'].split(','))
        elif config.video['tts_type'] == 'coquiTTS':
            self.voice_role.addItems(config.video['coquitts_role'].split(','))
        # 设置 tts_type
        self.tts_type.addItems(config.video['tts_type_list'])
        self.tts_type.setCurrentText(config.video['tts_type'])
        # tts_type 改变时，重设角色
        self.tts_type.currentTextChanged.connect(self.tts_type_change)
        self.enable_cuda.setChecked(config.video['enable_cuda'])

        # subtitle 0 no 1=embed subtitle 2=softsubtitle
        self.subtitle_type.addItems([transobj['nosubtitle'], transobj['embedsubtitle'], transobj['softsubtitle']])
        self.subtitle_type.setCurrentIndex(config.video['subtitle_type'])

        # 字幕编辑
        self.subtitle_area = TextGetdir(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        # sizePolicy.setWidthForHeight(self.subtitle_area.sizePolicy().hasWidthForHeight())
        self.subtitle_area.setSizePolicy(sizePolicy)
        self.subtitle_area.setMinimumSize(300, 0)
        self.subtitle_area.setPlaceholderText(transobj['subtitle_tips'])
        self.subtitle_layout.insertWidget(0, self.subtitle_area)
        self.subtitle_area.textChanged.connect(self.reset_timeid)

        # menubar
        self.actionbaidu_key.triggered.connect(self.set_baidu_key)
        self.actiontencent_key.triggered.connect(self.set_tencent_key)
        self.actionchatgpt_key.triggered.connect(self.set_chatgpt_key)
        self.actiondeepL_key.triggered.connect(self.set_deepL_key)
        self.actiondeepLX_address.triggered.connect(self.set_deepLX_address)
        self.action_vlc.triggered.connect(lambda: self.open_url('vlc'))
        self.action_ffmpeg.triggered.connect(lambda: self.open_url('ffmpeg'))
        self.action_git.triggered.connect(lambda: self.open_url('git'))
        self.action_discord.triggered.connect(lambda: self.open_url('discord'))
        self.action_website.triggered.connect(lambda: self.open_url('website'))
        self.action_issue.triggered.connect(lambda: self.open_url('issue'))
        self.action_tool.triggered.connect(self.open_toolbox)
        self.action_clone.triggered.connect(lambda: show_popup(transobj['yinsekaifazhong'], transobj['yinsekelong']))

        # status
        self.statusLabel = QLabel(transobj['modelpathis'] + " /models")
        self.statusLabel.setStyleSheet("color:#e8bf46")
        self.statusBar.addWidget(self.statusLabel)
        self.statusBar.addPermanentWidget(QLabel("github.com/jianchang512/pyvideotrans"))

        # 隐藏高级设置
        self.gaoji_show = True
        self.hide_layout_recursive()
        self.gaoji_btn.clicked.connect(self.hide_layout_recursive)
        #     日志
        self.task_logs = LogsWorker()
        self.task_logs.post_logs.connect(self.update_data)
        self.task_logs.start()
    def open_dir(self, dirname=None):
        if not dirname:
            return
        if not os.path.isdir(dirname):
            dirname = os.path.dirname(dirname)
        QDesktopServices.openUrl(QUrl(f"file:{dirname}"))

    # 隐藏或显示高级设置
    def hide_layout_recursive(self):
        # 递归隐藏布局及其下的所有元素
        def hide_recursive(layout, show):
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item.widget():
                    if show:
                        item.widget().hide()
                    else:
                        item.widget().show()
                elif item.layout():
                    hide_recursive(item.layout(), show)

        hide_recursive(self.gaoji_layout_wrap, self.gaoji_show)
        self.gaoji_show = not self.gaoji_show

    # 开启执行后，禁用按钮，停止或结束后，启用按钮
    def disabled_widget(self, type):
        self.btn_get_video.setDisabled(type)
        self.source_mp4.setDisabled(type)
        self.btn_save_dir.setDisabled(type)
        self.target_dir.setDisabled(type)
        self.translate_type.setDisabled(type)
        self.proxy.setDisabled(type)
        self.source_language.setDisabled(type)
        self.target_language.setDisabled(type)
        self.tts_type.setDisabled(type)
        self.voice_role.setDisabled(type)
        self.whisper_model.setDisabled(type)
        self.whisper_type.setDisabled(type)
        self.subtitle_type.setDisabled(type)
        self.voice_rate.setDisabled(type)
        self.voice_silence.setDisabled(type)
        self.voice_autorate.setDisabled(type)
        self.enable_cuda.setDisabled(type)

    def closeEvent(self, event):
        # 在关闭窗口前执行的操作
        if config.ffmpeg_status == 'ing':
            config.ffmpeg_status = "stop"
            msg = QMessageBox()
            msg.setWindowTitle(transobj['exit'])
            msg.setWindowIcon(QIcon(config.rootdir + "/icon.ico"))
            msg.setText(transobj['waitclear'])
            msg.addButton(transobj['queding'], QMessageBox.AcceptRole)
            msg.setIcon(QMessageBox.Information)
            msg.exec_()  # 显示消息框

            event.accept()
        else:
            event.accept()

    def get_setting(self):
        # init storage value
        config.video['baidu_appid'] = self.settings.value("baidu_appid", "")
        config.video['baidu_miyue'] = self.settings.value("baidu_miyue", "")
        config.video['deepl_authkey'] = self.settings.value("deepl_authkey", "")
        config.video['deeplx_address'] = self.settings.value("deeplx_address", "")
        config.video['chatgpt_api'] = self.settings.value("chatgpt_api", "")
        config.video['chatgpt_key'] = self.settings.value("chatgpt_key", "")
        config.video['tencent_SecretId'] = self.settings.value("tencent_SecretId", "")
        config.video['tencent_SecretKey'] = self.settings.value("tencent_SecretKey", "")
        os.environ['OPENAI_API_KEY'] = config.video['chatgpt_key']
        config.video['chatgpt_model'] = self.settings.value("chatgpt_model", config.video['chatgpt_model'])
        config.video['chatgpt_template'] = config.video['chatgpt_template']
        # config.video['chatgpt_template'] = self.settings.value("chatgpt_template", config.video['chatgpt_template'])
        config.video['translate_type'] = self.settings.value("translate_type", config.video['translate_type'])
        config.video['subtitle_type'] = self.settings.value("subtitle_type", config.video['subtitle_type'], int)
        config.video['proxy'] = self.settings.value("proxy", "", str)
        config.video['voice_rate'] = self.settings.value("voice_rate", config.video['voice_rate'], str)
        config.video['voice_silence'] = self.settings.value("voice_silence", config.video['voice_silence'], str)
        config.video['voice_autorate'] = self.settings.value("voice_autorate", config.video['voice_autorate'], bool)
        config.video['enable_cuda'] = self.settings.value("enable_cuda", config.video['enable_cuda'], bool)
        config.video['whisper_model'] = self.settings.value("whisper_model", config.video['whisper_model'], str)
        config.video['whisper_type'] = self.settings.value("whisper_type", config.video['whisper_type'], str)
        config.video['tts_type'] = self.settings.value("tts_type", config.video['tts_type'], str)
        if not config.video['tts_type']:
            config.video['tts_type'] = 'edgeTTS'

    def open_url(self, title):
        if title == 'vlc':
            webbrowser.open_new_tab("https://www.videolan.org/vlc/")
        elif title == 'ffmpeg':
            webbrowser.open_new_tab("https://www.ffmpeg.org/download.html")
        elif title == 'git':
            webbrowser.open_new_tab("https://github.com/jianchang512/pyvideotrans")
        elif title == 'issue':
            webbrowser.open_new_tab("https://github.com/jianchang512/pyvideotrans/issues")
        elif title == 'discord':
            webbrowser.open_new_tab("https://discord.com/channels/1174626422044766258/1174626425702207562")
        elif title == 'website':
            webbrowser.open_new_tab("https://v.wonyes.org")

    def open_toolbox(self):
        try:
            import box
            toolbox_main = box.MainWindow()
            toolbox_main.show()
        except Exception as e:
            QMessageBox.critical(self, "出错了", "你可能需要先安装VLC解码器，" + str(e))
            logger.error("vlc" + str(e))

    # 停止自动合并倒计时
    def reset_timeid(self):
        if not config.exec_compos and config.subtitle_end and self.task is not None:
            if self.task.timeid is None:
                return
            self.task.timeid = None if self.task.timeid is None or self.task.timeid > 0 else 0
            self.process.moveCursor(QTextCursor.Start)
            self.process.insertPlainText("停止倒计时，请修改字幕后点击合并按钮\n")

    # set deepl key
    def set_deepL_key(self):
        def save():
            key = self.w.deepl_authkey.text()
            self.settings.setValue("deepl_authkey", key)
            config.video['deepl_authkey'] = key
            self.w.close()

        self.w = DeepLForm()
        if config.video['deepl_authkey']:
            self.w.deepl_authkey.setText(config.video['deepl_authkey'])
        self.w.set_deepl.clicked.connect(save)
        self.w.show()

    def set_deepLX_address(self):
        def save():
            key = self.w.deeplx_address.text()
            self.settings.setValue("deeplx_address", key)
            config.video['deeplx_address'] = key
            self.w.close()

        self.w = DeepLXForm()
        if config.video['deeplx_address']:
            self.w.deeplx_address.setText(config.video['deeplx_address'])
        self.w.set_deeplx.clicked.connect(save)
        self.w.show()

    # set baidu
    def set_baidu_key(self):
        def save_baidu():
            appid = self.w.baidu_appid.text()
            miyue = self.w.baidu_miyue.text()
            self.settings.setValue("baidu_appid", appid)
            self.settings.setValue("baidu_miyue", miyue)
            config.video['baidu_appid'] = appid
            config.video['baidu_miyue'] = miyue
            self.w.close()

        self.w = BaiduForm()
        if config.video['baidu_appid']:
            self.w.baidu_appid.setText(config.video['baidu_appid'])
        if config.video['baidu_miyue']:
            self.w.baidu_miyue.setText(config.video['baidu_miyue'])
        self.w.set_badiu.clicked.connect(save_baidu)
        self.w.show()

    def set_tencent_key(self):
        def save():
            SecretId = self.w.tencent_SecretId.text()
            SecretKey = self.w.tencent_SecretKey.text()
            self.settings.setValue("tencent_SecretId", SecretId)
            self.settings.setValue("tencent_SecretKey", SecretKey)
            config.video['tencent_SecretId'] = SecretId
            config.video['tencent_SecretKey'] = SecretKey
            self.w.close()

        self.w = TencentForm()
        if config.video['tencent_SecretId']:
            self.w.tencent_SecretId.setText(config.video['tencent_SecretId'])
        if config.video['tencent_SecretKey']:
            self.w.tencent_SecretKey.setText(config.video['tencent_SecretKey'])
        self.w.set_tencent.clicked.connect(save)
        self.w.show()

    # set chatgpt
    def set_chatgpt_key(self):
        def save_chatgpt():
            key = self.w.chatgpt_key.text()
            api = self.w.chatgpt_api.text()
            model = self.w.chatgpt_model.currentText()
            template = self.w.chatgpt_template.toPlainText()
            self.settings.setValue("chatgpt_key", key)
            self.settings.setValue("chatgpt_api", api)

            self.settings.setValue("chatgpt_model", model)
            self.settings.setValue("chatgpt_template", template)

            os.environ['OPENAI_API_KEY'] = key
            config.video['chatgpt_key'] = key
            config.video['chatgpt_api'] = api
            config.video['chatgpt_model'] = model
            config.video['chatgpt_template'] = template
            self.w.close()

        self.w = ChatgptForm()
        if config.video['chatgpt_key']:
            self.w.chatgpt_key.setText(config.video['chatgpt_key'])
        if config.video['chatgpt_api']:
            self.w.chatgpt_api.setText(config.video['chatgpt_api'])
        if config.video['chatgpt_model']:
            self.w.chatgpt_model.setCurrentText(config.video['chatgpt_model'])
        if config.video['chatgpt_template']:
            self.w.chatgpt_template.setPlainText(config.video['chatgpt_template'])
        self.w.set_chatgpt.clicked.connect(save_chatgpt)
        self.w.show()

    # watching translate_type toggle
    def set_translate_type(self, name):
        try:
            if name == "baidu" and not config.video['baidu_appid']:
                QMessageBox.critical(self, transobj['anerror'], transobj['baidukeymust'])
                return
            if name == "chatGPT" and not config.video["chatgpt_key"]:
                QMessageBox.critical(self, transobj['anerror'], transobj['chatgptkeymust'])
                return
            if name == "DeepL" and not config.video["deepl_authkey"]:
                QMessageBox.critical(self, transobj['anerror'], transobj['setdeepl_authkey'])
                return
            if name == "DeepLX" and not config.video["deeplx_address"]:
                QMessageBox.critical(self, transobj['anerror'], transobj['setdeeplx_address'])
                return
            config.video['translate_type'] = name
        except Exception as e:
            QMessageBox.critical(self, transobj['anerror'], str(e))

    def check_whisper_type(self, index):
        print(f"whisper_type={index=}")
        if index == 0:
            config.video['whisper_type'] = 'all'
        else:
            config.video['whisper_type'] = 'split'

    # check model is exits
    def check_whisper_model(self, name):
        if not os.path.exists(config.rootdir + f"/models/{name}.pt"):
            self.statusLabel.setText(transobj['downloadmodel'] + f" ./models/{name}.pt")
            QMessageBox.critical(self, transobj['downloadmodel'], f"./models/{name}.pt")
        else:
            self.statusLabel.setText(transobj['modelpathis'] + f" ./models/{name}.pt")

    # start or stop ,update start button text and stop worker thread
    def update_start(self, type):
        config.current_status = type
        self.startbtn.setText(transobj[type])
        if type == 'stop' or type == 'end':
            config.exec_compos = False
            config.subtitle_end = False
            config.ffmpeg_status = 'stop'
            self.continue_compos.hide()
            self.btn_get_video.setDisabled(False)
            # 启用
            self.disabled_widget(False)
            if type == 'end':
                # 清理字幕
                self.subtitle_area.clear()
            if self.task:
                self.task.requestInterruption()
                self.task.quit()
        else:
            self.disabled_widget(True)
            config.ffmpeg_status = 'ing'

    # tts类型改变
    def tts_type_change(self, type):
        config.video['tts_type'] = type
        if type == "openaiTTS":
            self.voice_role.clear()
            self.voice_role.addItems(config.video['openaitts_role'].split(','))
        elif type == 'coquiTTS':
            self.voice_role.addItems(config.video['coquitts_role'].split(','))
        elif type == 'edgeTTS':
            self.set_voice_role(self.target_language.currentText())

    # 试听配音
    def listen_voice_fun(self):
        currentlang = self.target_language.currentText()
        if currentlang in ["English", "英语"]:
            text = config.video['listen_text_en']
            lang = "en"
        elif currentlang in ["中文简", "中文繁", "Simplified_Chinese", "Traditional_Chinese"]:
            text = config.video['listen_text_cn']
            lang = "zh"
        else:
            return
        print(f"{text}")
        role = self.voice_role.currentText()
        if not role or role == 'No':
            return QMessageBox.critical(self, transobj['anerror'], transobj['mustberole'])
        voice_dir = os.environ.get('APPDATA') or os.environ.get('appdata')
        if not voice_dir or not os.path.exists(voice_dir):
            voice_dir = config.rootdir + "/tmp/voice_tmp"
        else:
            voice_dir = voice_dir.replace('\\', '/') + "/pyvideotrans"
        if not os.path.exists(voice_dir):
            os.makedirs(voice_dir)
        voice_file = f"{voice_dir}/{config.video['tts_type']}-{lang}-{role}.mp3"
        print(f"{voice_file=}")
        obj = {
            "text": text,
            "rate": "+0%",
            "role": role,
            "voice_file": voice_file,
            "tts_type": config.video['tts_type'],
        }

        t = PlayMp3(obj, self)
        t.start()

    # set edge-ttss change voice role when target_language changed
    def set_voice_role(self, t):
        # t in  中文简 中文繁 英语 Simplified_Chinese Traditional_Chinese English 显示试听按钮
        if t in ["中文简", "中文繁", "英语", "Simplified_Chinese", "Traditional_Chinese", "English"]:
            self.listen_btn.show()
            self.listen_btn.setDisabled(False)
        else:
            self.listen_btn.hide()
            self.listen_btn.setDisabled(True)
        # 如果tts类型是 openaiTTS，则角色不变
        # 是edgeTTS时需要改变
        if config.video['tts_type'] != 'edgeTTS':
            return
        self.voice_role.clear()
        if t == '-':
            self.voice_role.addItems(['No'])
            return
        if not config.edgeTTS_rolelist:
            self.target_language.setCurrentText('-')
            QMessageBox.critical(self, transobj['anerror'], transobj['waitrole'])
            return
        try:
            vt = langlist[t][0].split('-')[0]
            if vt not in config.edgeTTS_rolelist:
                self.voice_role.addItems(['No'])
                return
            if len(config.edgeTTS_rolelist[vt]) < 2:
                self.target_language.setCurrentText('-')
                QMessageBox.critical(self, transobj['anerror'], transobj['waitrole'])
                return
            self.voice_role.addItems(config.edgeTTS_rolelist[vt])
        except:
            self.voice_role.addItems([it for item in list(config.edgeTTS_rolelist.values()) for it in item])

    # get video filter mp4
    def get_mp4(self):
        fnames, _ = QFileDialog.getOpenFileNames(self, transobj['selectmp4'], self.last_dir,
                                                 "Video files(*.mp4 *.avi *.mov *.mpg *.mkv)")
        if len(fnames) < 1:
            return
        first = fnames.pop(0)
        self.source_mp4.setText(first)
        self.settings.setValue("last_dir", os.path.dirname(first))
        if len(fnames) > 0:
            config.queue_mp4 = fnames
            self.statusLabel.setText(f"Add {len(fnames) + 1} mp4 ")

    # output dir
    def get_save_dir(self):
        dirname = QFileDialog.getExistingDirectory(self, transobj['selectsavedir'], self.last_dir)
        dirname = dirname.replace('\\', '/')
        self.target_dir.setText(dirname)

    # 仅配音
    def only_dubbing(self):
        reply = QMessageBox.question(self, transobj['qingqueren'], transobj['subtitleandvoice_role'],
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        # 确定仅创建字幕
        if reply != QMessageBox.Yes:
            self.update_start("stop")
            return
        # 如果没有配音角色
        config.video['voice_role'] = self.voice_role.currentText()
        if not config.video['voice_role'] or config.video['voice_role'] in ['No', '-']:
            self.update_start("stop")
            QMessageBox.critical(self, transobj['anerror'], transobj['xuanzejuese'])
            return
        #  创建字幕文件
        noextname = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        tmp_dir = f"{config.rootdir}/tmp/{noextname}"
        target_dir = homedir+f"/only_dubbing"
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir, exist_ok=True)
        if not os.path.exists(target_dir+f"/{noextname}"):
            os.makedirs(target_dir+f"/{noextname}", exist_ok=True)
        self.open_targetdir.setDisabled(False)
        # 创建字幕文件
        self.get_sub_toarea(noextname)
        # 创建目标文件夹
        config.video['target_dir'] = target_dir
        self.target_dir.setText(target_dir)
        # 开始线程
        self.update_start("ing")
        self.btn_get_video.setDisabled(True)
        self.save_setting()
        self.task = WorkerOnlyDubbing(noextname, self)
        self.task.start()

    # start
    def check_start(self):
        if config.current_status == 'ing':
            question = show_popup(transobj['exit'], transobj['confirmstop'])
            if question == QMessageBox.AcceptRole:
                self.update_start('stop')
                return
        self.process.clear()
        if config.video['proxy']:
            os.environ['http_proxy'] = 'http://%s' % config.video['proxy'].replace("http://", '')
            os.environ['https_proxy'] = 'http://%s' % config.video['proxy'].replace("http://", '')
        else:
            set_proxy()

        config.video['source_mp4'] = self.source_mp4.text().strip().replace('\\', '/')
        txt = self.subtitle_area.toPlainText().strip()
        # 如果无输入视频，但字幕区有内容，则仅创建配音
        if not config.video['source_mp4'] and txt:
            self.only_dubbing()
            return
        # 检测参数
        if not config.video['source_mp4'] or not os.path.exists(config.video['source_mp4']):
            self.update_start("stop")
            QMessageBox.critical(self, transobj['anerror'], transobj['selectvideodir'])
            return
        noextname = os.path.splitext(os.path.basename(config.video['source_mp4']))[0]
        mp4dirname = os.path.dirname(config.video['source_mp4']).lower()
        target_dir = self.target_dir.text().strip().lower().replace('\\', '/')
        if not target_dir or mp4dirname == target_dir:
            target_dir = mp4dirname + "/_video_out"
            self.target_dir.setText(target_dir)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
        if not os.path.exists(target_dir + f"/{noextname}"):
            os.makedirs(target_dir + f"/{noextname}", exist_ok=True)

        config.video['target_dir'] = target_dir
        config.video['proxy'] = self.proxy.text().strip()

        target_language = self.target_language.currentText()
        config.video['source_language'] = langlist[self.source_language.currentText()][0]
        if '-' == target_language:
            self.update_start("stop")
            QMessageBox.critical(self, transobj['anerror'], transobj['shoundselecttargetlanguage'])
            return
        config.video['target_language'] = langlist[target_language][0]

        # google language code
        if config.video['translate_type'] == 'google':
            config.video['target_language'] = langlist[target_language][0]
        elif config.video['translate_type'] == 'baidu(noKey)':
            config.video['target_language_baidu'] = langlist[target_language][2]
        elif config.video['translate_type'] == 'baidu':
            # baidu language code
            config.video['target_language_baidu'] = langlist[target_language][2]
            if not config.video['baidu_appid'] or not config.video['baidu_miyue']:
                QMessageBox.critical(self, transobj['anerror'], transobj['baikeymust'])
                return
        elif config.video['translate_type'] == 'tencent':
            #     腾讯翻译
            config.video['target_language_tencent'] = langlist[target_language][4]
            if not config.video['tencent_SecretId'] or not config.video['tencent_SecretKey']:
                QMessageBox.critical(self, transobj['anerror'], transobj['tencent_key'])
                return
        elif config.video['translate_type'] == 'chatGPT':
            # chatGPT 翻译
            config.video['target_language_chatgpt'] = english_code_bygpt[self.languagename.index(target_language)]
            if not config.video['chatgpt_key']:
                QMessageBox.critical(self, transobj['anerror'], transobj['chatgptkeymust'])
                return
        elif config.video['translate_type'] == 'DeepL' or config.video['translate_type'] == 'DeepLX':
            # DeepL翻译
            if config.video['translate_type'] == 'DeepL' and not config.video['deepl_authkey']:
                QMessageBox.critical(self, transobj['anerror'], transobj['deepl_authkey'])
                return
            if config.video['translate_type'] == 'DeepLX' and not config.video['deeplx_address']:
                QMessageBox.critical(self, transobj['anerror'], transobj['setdeeplx_address'])
                return

            config.video['target_language_deepl'] = langlist[target_language][3]
            if config.video['target_language_deepl'] == 'No':
                QMessageBox.critical(self, transobj['anerror'], transobj['deepl_nosupport'])
                return

        if config.video['source_language'] == config.video['target_language']:
            self.update_start("stop")
            QMessageBox.critical(self, transobj['anerror'], transobj['sourenotequaltarget'])
            return
        # tts类型
        if config.video['tts_type'] == 'openaiTTS' and not config.video['chatgpt_key']:
            QMessageBox.critical(self, transobj['anerror'], transobj['chatgptkeymust'])
            return

        config.video['detect_language'] = langlist[self.source_language.currentText()][0]
        config.video['subtitle_language'] = langlist[self.target_language.currentText()][1]

        config.video['voice_role'] = self.voice_role.currentText()
        config.video['whisper_model'] = self.whisper_model.currentText()

        model = config.rootdir + f"/models/{config.video['whisper_model']}.pt"
        if not os.path.exists(model) or os.path.getsize(model) < 100:
            self.update_start("stop")
            QMessageBox.critical(self, transobj['downloadmodel'], f" ./models/{config.video['whisper_model']}.pt")
            self.statusLabel.setText(transobj['downloadmodel'] + f" ./models/{config.video['whisper_model']}.pt")
            return

        config.video['voice_autorate'] = self.voice_autorate.isChecked()
        config.video['subtitle_type'] = int(self.subtitle_type.currentIndex())

        # 如果既没有选择字幕也没有选择配音，将仅生成字幕文件
        if config.video['subtitle_type'] < 1 and (config.video['voice_role'] == 'No'):
            reply = QMessageBox.question(self, transobj['qingqueren'], transobj['only_srt'],
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            # 确定仅创建字幕
            if reply != QMessageBox.Yes:
                self.update_start("stop")
                return

        try:
            voice_rate = int(self.voice_rate.text().strip())
            config.video['voice_rate'] = f"+{voice_rate}%" if voice_rate >= 0 else f"-{voice_rate}%"
        except:
            pass
        try:
            voice_silence = int(self.voice_silence.text().strip())
            config.video['voice_silence'] = voice_silence
        except:
            pass
        self.save_setting()
        if not os.path.exists(config.rootdir+"/tmp"):
            os.mkdir(config.rootdir+"/tmp")
        config.current_status = 'ing'
        config.exec_compos = False
        # 如果已有字幕，则使用
        if txt:
            set_process(f"从字幕编辑区直接读入字幕")
            subname = f"{config.rootdir}/tmp/{noextname}/{noextname}.srt"
            os.makedirs(os.path.dirname(subname), exist_ok=True)
            with open(subname, 'w', encoding="utf-8") as f:
                f.write(txt)
        self.startbtn.setText(transobj['running'])
        self.open_targetdir.setDisabled(False)
        self.start(config.video['source_mp4'])

    # 存储本地数据
    def save_setting(self):
        self.settings.setValue("target_dir", config.video['target_dir'])
        self.settings.setValue("proxy", config.video['proxy'])
        self.settings.setValue("whisper_model", config.video['whisper_model'])
        self.settings.setValue("whisper_type", config.video['whisper_type'])
        self.settings.setValue("voice_rate", config.video['voice_rate'])
        self.settings.setValue("voice_silence", config.video['voice_silence'])
        self.settings.setValue("voice_autorate", config.video['voice_autorate'])
        self.settings.setValue("subtitle_type", config.video['subtitle_type'])
        self.settings.setValue("translate_type", config.video['translate_type'])
        self.settings.setValue("enable_cuda", config.video['enable_cuda'])
        self.settings.setValue("tts_type", config.video['tts_type'])
        self.settings.setValue("tencent_SecretKey", config.video['tencent_SecretKey'])
        self.settings.setValue("tencent_SecretId", config.video['tencent_SecretId'])

    # 判断是否存在字幕文件，如果存在，则读出填充字幕区
    def get_sub_toarea(self, noextname):
        sub_name = f"{config.rootdir}/tmp/{noextname}/{noextname}.srt"
        c = self.subtitle_area.toPlainText().strip()
        #     判断 如果右侧字幕区无字幕，并且已存在字幕文件，则读取
        if not c and os.path.exists(sub_name) and os.path.getsize(sub_name) > 0:
            with open(sub_name, 'r', encoding="utf-8") as f:
                self.subtitle_area.setPlainText(f.read().strip())
                return True
        # 右侧存在，则创建字幕
        if c:
            with open(sub_name, 'w', encoding="utf-8") as f:
                f.write(self.subtitle_area.toPlainText().strip())
                return True
        return False

    # 被调起或者从worker线程调用
    def start(self, mp4):
        self.update_start("ing")
        noextname = os.path.basename(mp4).split('.')[0]
        self.get_sub_toarea(noextname)

        self.btn_get_video.setDisabled(True)
        self.task = Worker(mp4.replace('\\', '/'), self)
        # self.task.update_ui.connect(self.update_data)
        self.task.start()
        self.statusLabel.setText(
            transobj['processingstatusbar'].replace('{var1}', f"视频{noextname}").replace('{var2}',
                                                                                        str(len(config.queue_mp4))))

    # receiver  update UI
    def update_data(self, json_data):
        d = json.loads(json_data)
        if d['type'] == "subtitle":
            self.subtitle_area.moveCursor(QTextCursor.End)
            self.subtitle_area.insertPlainText(d['text'])
        elif d['type'] == "logs":
            self.process.moveCursor(QTextCursor.Start)
            self.process.insertHtml(d['text'])
        elif d['type'] == 'stop' or d['type'] == 'end':
            self.update_start(d['type'])
            self.statusLabel.setText(d['type'])
            self.continue_compos.hide()
        elif d['type'] == 'wait_subtitle':
            # 显示出合成按钮
            self.continue_compos.show()
            self.continue_compos.setDisabled(False)
            self.continue_compos.setText(transobj['waitsubtitle'])
        elif d['type'] == 'update_subtitle':
            # 字幕编辑后启动合成
            self.update_subtitle()
        elif d['type'] == 'replace_subtitle':
            # 完全替换字幕区
            self.subtitle_area.clear()
            self.subtitle_area.insertPlainText(d['text'])
        elif d['type'] == 'check_queue':
            self.subtitle_area.clear()
            # 判断是否存在下一个mp4，如果存在，则继续执行
            if len(config.queue_mp4) > 0:
                # 重置状态
                config.current_status = 'ing'
                config.exec_compos = False
                config.subtitle_end = False
                self.continue_compos.hide()
                self.continue_compos.setText("")
                self.subtitle_area.clear()
                # 填充 输入框
                newmp4 = config.queue_mp4.pop(0)
                self.source_mp4.setText(newmp4)
                set_process(f"存在下一个视频待处理:{newmp4}")
                self.start(newmp4)
            else:
                set_process(f"全部执行结束")
                self.update_start('end')
                if self.task:
                    self.task.timeid = 0

    # update subtitle
    def update_subtitle(self):
        sub_name = self.task.sub_name
        try:
            if self.get_sub_toarea(self.task.noextname):
                config.subtitle_end = True
                config.exec_compos = True
                self.continue_compos.setDisabled(True)
                self.continue_compos.setText(transobj['waitforend'])
                return
            if not self.subtitle_area.toPlainText().strip() and not os.path.exists(sub_name):
                config.subtitle_end = False
                config.exec_compos = False
                self.continue_compos.setDisabled(True)
                self.continue_compos.setText('')
                set_process("[error]出错了，不存在有效字幕")
                return
        except Exception as e:
            set_process("[error]:写入字幕出错了：" + str(e))
            logger.error("[error]:写入字幕出错了：" + str(e))


if __name__ == "__main__":
    threading.Thread(target=get_edge_rolelist).start()
    threading.Thread(target=is_vlc).start()
    app = QApplication(sys.argv)
    main = MainWindow()
    try:
        if not os.path.exists(config.rootdir+ "/models"):
            os.mkdir(config.rootdir+ "/models")
        if not os.path.exists(config.rootdir+"/tmp"):
            os.mkdir(config.rootdir+"tmp")
        if shutil.which('ffmpeg') is None:
            QMessageBox.critical(main, transobj['anerror'], transobj["installffmpeg"])
    except Exception as e:
        QMessageBox.critical(main, transobj['anerror'], transobj['createdirerror'])

    if sys.platform == 'win32':
        import qdarkstyle

        app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))

    main.show()
    sys.exit(app.exec())
