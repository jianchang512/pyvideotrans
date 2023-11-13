# -*- coding: utf-8 -*-
import json
import shutil
import sys
import os
import threading
import time
import webbrowser

from PyQt5 import QtCore
from PyQt5.QtGui import QTextCursor, QIcon
from PyQt5.QtCore import pyqtSignal, QThread, QSettings, QProcess
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QFileDialog, QInputDialog, QWidget, QDialog, QLabel
import warnings
warnings.filterwarnings('ignore')
from videotrans.ui.deepl import Ui_deeplform
from videotrans.configure.config import langlist, transobj, logger, queue_logs
from videotrans.configure.language import english_code_bygpt
from videotrans.configure.tools import get_list_voices, get_large_audio_transcription, runffmpeg, delete_temp, dubbing, \
    show_popup, compos_video, set_proxy, set_process
from videotrans.configure import config
from videotrans.ui.chatgpt import Ui_chatgptform
from videotrans.ui.baidu import Ui_baiduform

from videotrans.util.tools import find_lib
if config.defaulelang == "zh":
    from videotrans.ui.cn import Ui_MainWindow
else:
    from videotrans.ui.en import Ui_MainWindow


# get edge tts voice role
def set_voice_list():
    config.voice_list = get_list_voices()


class LogsWorker(QThread):
    post_logs = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def run(self):
        while True:
            try:
                obj = queue_logs.get(True, 1)
                if "type" not in obj:
                    obj['type'] = 'logs'
                self.post_logs.emit(json.dumps(obj))
            except Exception as e:
                pass


# task process thread
class Worker(QThread):
    update_ui = pyqtSignal(str)
    # None wait manual ,nums wait
    timeid = 0

    def __init__(self, mp4path, parent=None):
        super().__init__(parent=parent)
        self.mp4path = mp4path.replace('\\', '/')

    # 执行入口
    def run(self):
        if not self.mp4path:
            set_process(transobj['selectvideodir'], "stop")
            return
        try:
            # 原始mp4视频地址
            mp4name = os.path.basename(self.mp4path)
            # 无扩展视频名，视频后缀(mp4,MP4)
            self.noextname = os.path.splitext(mp4name)[0]
            # 创建临时文件
            if not os.path.exists(f"{config.rootdir}/tmp/{self.noextname}"):
                os.makedirs(f"{config.rootdir}/tmp/{self.noextname}", exist_ok=True)
            # 分离出的音频文件
            self.a_name = f"{config.rootdir}/tmp/{self.noextname}/{self.noextname}.wav"
            self.sub_name = f"{config.rootdir}/tmp/{self.noextname}/{self.noextname}.srt"
            # 分离出音频
            if not os.path.exists(self.a_name) or os.path.getsize(self.a_name) == 0:
                set_process(f"{self.noextname} 从视频中抽离音频", "logs")
                runffmpeg([
                    "-y",
                    "-i",
                    f'"{self.mp4path}"',
                    "-ac",
                    "1",
                    f'"{self.a_name}"'
                ])
                # 单独提前分离出 novice.mp4
                novice_mp4 = config.rootdir + f'/tmp/{self.noextname}/novoice.mp4'
                ffmpegars = [
                    "-y",
                    "-i",
                    f'"{self.mp4path}"',
                    "-an",
                    f'"{novice_mp4}"'
                ]
                threading.Thread(target=runffmpeg, args=(ffmpegars,), kwargs={"asy": True}).start()
            try:
                # 识别、创建字幕文件、翻译
                if os.path.exists(self.sub_name) and os.path.getsize(self.sub_name) > 0:
                    set_process(f"{self.noextname} wait subtitle edit", "wait_subtitle")
                    config.subtitle_end = True
                else:
                    if os.path.exists(self.sub_name):
                        os.unlink(self.sub_name)
                    get_large_audio_transcription(self.noextname)
                    if config.current_status == 'ing':
                        set_process(f"{self.noextname} wait subtitle edit", "wait_subtitle")
                        config.subtitle_end = True
            except Exception as e:
                logger.error("error:" + str(e))
                set_process(f"文字识别和翻译出错:"+str(e))

            # 生成字幕后等待倒计时
            self.timeid = 0
            while True:
                if config.current_status == 'stop' or config.current_status == 'end':
                    set_process("已停止", 'stop')
                    raise Exception("You stop it")
                # 字幕未处理完
                if not config.subtitle_end:
                    time.sleep(1)
                    continue
                # 点击了合成按钮 开始合成
                if config.exec_compos:
                    self.wait_subtitle()
                    break
                #  没有进行合成指令， 自动超时，先去更新字幕文件，然后设置 config.exec_compos=True,等下下轮循环
                if not config.exec_compos and self.timeid is not None and self.timeid >= 60:
                    config.exec_compos = True
                    set_process("超时未修改字母，自动合成视频", 'update_subtitle')
                    continue
                # 字幕处理完毕，未超时
                time.sleep(1)
                # 字幕处理完成
                # 倒计时中
                if self.timeid is not None:
                    self.timeid += 1
                    set_process(f"{60 - self.timeid}秒后自动合并")
                    continue
                # 暂停，等待手动处理
                set_process(f"等待修改字幕")

        except Exception as e:
            logger.error(f"sp.py :" + str(e))
            set_process(f"[error]:{str(e)}")

    # 执行配音、合成
    def wait_subtitle(self):
        try:
            set_process(f"开始配音操作:{config.video['tts_type']}", 'logs')
            dubbing(self.noextname)
            set_process(f"开始将视频、音频、字幕合并", 'logs')
            compos_video(self.mp4path, self.noextname)
            set_process(f"任务处理结束,清理临时文件", 'logs')
            delete_temp(self.noextname)
            # 检测是否还有
            set_process("检测是否存在写一个任务", "check_queue")
        except Exception as e:
            logger.error("error:" + str(e))
            set_process(f"[error]:配音合并时出错:" + str(e), "logs")


# primary ui
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.initUI()
        self.setWindowIcon(QIcon("./icon.ico"))
        self.setWindowTitle(
            f"SP{'视频翻译配音' if config.defaulelang != 'en' else ' Video Translate & Dubbing'} V0.9.1 wonyes.org")

    def initUI(self):
        self.settings = QSettings("Jameson", "VideoTranslate")
        # 获取最后一次选择的目录
        self.last_dir = self.settings.value("last_dir", ".", str)
        # language code
        self.languagename = list(langlist.keys())
        # task thread
        self.task = None
        # init storage value
        config.video['baidu_appid'] = self.settings.value("baidu_appid", "")
        config.video['baidu_miyue'] = self.settings.value("baidu_miyue", "")
        config.video['deepl_authkey'] = self.settings.value("deepl_authkey", "")
        config.video['chatgpt_api'] = self.settings.value("chatgpt_api", "")
        config.video['chatgpt_key'] = self.settings.value("chatgpt_key", "")
        os.environ['OPENAI_API_KEY'] = config.video['chatgpt_key']
        config.video['chatgpt_model'] = self.settings.value("chatgpt_model", config.video['chatgpt_model'])
        config.video['chatgpt_template'] = self.settings.value("chatgpt_template", config.video['chatgpt_template'])
        config.video['translate_type'] = self.settings.value("translate_type", config.video['translate_type'])
        config.video['subtitle_type'] = self.settings.value("subtitle_type", config.video['subtitle_type'], int)
        config.video['proxy'] = self.settings.value("proxy", "", str)
        config.video['voice_rate'] = self.settings.value("voice_rate", config.video['voice_rate'], str)
        config.video['voice_silence'] = self.settings.value("voice_silence", config.video['voice_silence'], str)
        config.video['voice_autorate'] = self.settings.value("voice_autorate", config.video['voice_autorate'], bool)
        config.video['enable_cuda'] = self.settings.value("enable_cuda", config.video['enable_cuda'], bool)
        config.video['whisper_model'] = self.settings.value("whisper_model", config.video['whisper_model'], str)
        config.video['tts_type'] = self.settings.value("tts_type", config.video['tts_type'], str)
        if not config.video['tts_type']:
            config.video['tts_type'] = 'edgeTTS'

        self.splitter.setSizes([830, 350])

        # start
        self.startbtn.clicked.connect(self.check_start)
        # subtitle btn
        self.continue_compos.hide()
        self.continue_compos.clicked.connect(self.update_subtitle)

        # select and save
        self.btn_get_video.clicked.connect(self.get_mp4)
        self.btn_save_dir.clicked.connect(self.get_save_dir)
        self.proxy.setText(config.video['proxy'])

        # language
        self.source_language.addItems(self.languagename)
        self.source_language.setCurrentIndex(2)

        # 目标语言改变时，如果当前tts是 edgeTTS，则根据目标语言去修改显示的角色
        self.target_language.addItems(["-"] + self.languagename)
        self.target_language.currentTextChanged.connect(self.set_voice_role)

        #  translation type
        self.translate_type.addItems(["google", "baidu", "chatGPT", "DeepL", "baidu(noKey)"])
        self.translate_type.setCurrentText(config.video['translate_type'])
        self.translate_type.currentTextChanged.connect(self.set_translate_type)

        #         model
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

        self.subtitle_area.textChanged.connect(self.reset_timeid)

        # menubar
        self.actionbaidu_key.triggered.connect(self.set_baidu_key)
        self.actionchatgpt_key.triggered.connect(self.set_chatgpt_key)
        self.actiondeepL_key.triggered.connect(self.set_deepL_key)
        self.action_vlc.triggered.connect(lambda: self.open_url('vlc'))
        self.action_ffmpeg.triggered.connect(lambda: self.open_url('ffmpeg'))
        self.action_git.triggered.connect(lambda: self.open_url('git'))
        self.action_issue.triggered.connect(lambda: self.open_url('issue'))
        self.action_tool.triggered.connect(self.open_toolbox)
        self.action_clone.triggered.connect(lambda: show_popup(transobj['yinsekaifazhong'], transobj['yinsekelong']))

        # status
        self.statusLabel = QLabel(transobj['modelpathis'] + " /models")
        self.statusLabel.setStyleSheet("color:#e8bf46")
        self.statusBar.addWidget(self.statusLabel)
        self.statusBar.addPermanentWidget(QLabel("github.com/jianchang512/pyvideotrans"))

        #     日志
        self.task_logs = LogsWorker()
        self.task_logs.post_logs.connect(self.update_data)
        self.task_logs.start()

    def open_url(self, title):
        if title == 'vlc':
            webbrowser.open_new_tab("https://www.videolan.org/vlc/")
        elif title == 'ffmpeg':
            webbrowser.open_new_tab("https://www.ffmpeg.org/download.html")
        elif title == 'git':
            webbrowser.open_new_tab("https://github.com/jianchang512/pyvideotrans")
        elif title == 'issue':
            webbrowser.open_new_tab("https://github.com/jianchang512/pyvideotrans/issues")

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
            self.task.timeid = None if self.task.timeid is None or self.task.timeid > 0 else 0
            self.process.moveCursor(QTextCursor.Start)
            self.process.insertPlainText(transobj['waitsubtitle'])

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
            config.video['translate_type'] = name
        except Exception as e:
            QMessageBox.critical(self, transobj['anerror'], str(e))

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
            self.continue_compos.hide()
            self.btn_get_video.setDisabled(False)
            if self.task:
                self.task.requestInterruption()
                self.task.quit()
                self.task.wait()

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

    # set edge-ttss change voice role when target_language changed
    def set_voice_role(self, t):
        # 如果tts类型是 openaiTTS，则角色不变
        # 是edgeTTS时需要改变
        if config.video['tts_type'] != 'edgeTTS':
            return
        self.voice_role.clear()
        if t == '-':
            self.voice_role.addItems(['No'])
            return
        if not config.voice_list:
            self.target_language.setCurrentText('-')
            QMessageBox.critical(self, transobj['anerror'], transobj['waitrole'])
            return
        try:
            vt = langlist[t][0].split('-')[0]
            if vt not in config.voice_list:
                self.voice_role.addItems(['No'])
                return
            if len(config.voice_list[vt]) < 2:
                self.target_language.setCurrentText('-')
                QMessageBox.critical(self, transobj['anerror'], transobj['waitrole'])
                return
            self.voice_role.addItems(config.voice_list[vt])
        except:
            self.voice_role.addItems([it for item in list(config.voice_list.values()) for it in item])

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
            config.queue = fnames
            self.statusLabel.setText(f"Add {len(fnames) + 1} mp4 ")

    # output dir
    def get_save_dir(self):
        dirname = QFileDialog.getExistingDirectory(self, transobj['selectsavedir'], self.last_dir)
        dirname = dirname.replace('\\', '/')
        self.target_dir.setText(dirname)

    # start
    def check_start(self):
        if config.current_status == 'ing':
            question = show_popup(transobj['exit'], transobj['confirmstop'])
            if question == QMessageBox.AcceptRole:
                self.update_start('stop')
                return

        # clear
        self.process.clear()
        self.subtitle_area.clear()
        self.startbtn.setText(transobj['running'])
        config.video['source_mp4'] = self.source_mp4.text().replace('\\', '/')
        # 检测参数
        if not config.video['source_mp4'] or not os.path.exists(config.video['source_mp4']):
            self.update_start("stop")
            QMessageBox.critical(self, transobj['anerror'], transobj['selectvideodir'])
            return

        mp4dirname = os.path.dirname(config.video['source_mp4']).lower()
        target_dir = self.target_dir.text().strip().lower().replace('\\', '/')
        if not target_dir or mp4dirname == target_dir:
            target_dir = mp4dirname + "/_video_out"
            self.target_dir.setText(target_dir)

        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir)
            except Exception as e:
                QMessageBox.critical(self, transobj['anerror'], transobj['createdirerror'] + " -> " + target_dir)
                return

        config.video['target_dir'] = target_dir
        config.video['proxy'] = self.proxy.text().strip()
        if config.video['proxy']:
            os.environ['http_proxy'] = 'http://%s' % config.video['proxy'].replace("http://", '')
            os.environ['https_proxy'] = 'http://%s' % config.video['proxy'].replace("http://", '')
        else:
            set_proxy()

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
        elif config.video['translate_type'] == 'chatGPT':
            # chatGPT 翻译
            config.video['target_language_chatgpt'] = english_code_bygpt[self.languagename.index(target_language)]
            if not config.video['chatgpt_key']:
                QMessageBox.critical(self, transobj['anerror'], transobj['chatgptkeymust'])
                return
        elif config.video['translate_type'] == 'DeepL':
            # DeepL翻译
            if not config.video['deepl_authkey']:
                QMessageBox.critical(self, transobj['anerror'], transobj['deepl_authkey'])
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

        if config.video['subtitle_type'] < 1 and (config.video['voice_role'] == 'No'):
            self.update_start("stop")
            QMessageBox.critical(self, transobj['anerror'], transobj['subtitleandvoice_role'])
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
        self.settings.setValue("target_dir", config.video['target_dir'])
        self.settings.setValue("proxy", config.video['proxy'])
        self.settings.setValue("whisper_model", config.video['whisper_model'])
        self.settings.setValue("voice_rate", config.video['voice_rate'])
        self.settings.setValue("voice_silence", config.video['voice_silence'])
        self.settings.setValue("voice_autorate", config.video['voice_autorate'])
        self.settings.setValue("subtitle_type", config.video['subtitle_type'])
        self.settings.setValue("translate_type", config.video['translate_type'])
        self.settings.setValue("enable_cuda", config.video['enable_cuda'])
        self.settings.setValue("tts_type", config.video['tts_type'])
        if not os.path.exists(os.path.join(config.rootdir, "tmp")):
            os.mkdir(os.path.join(config.rootdir, "tmp"))
        config.current_status = 'ing'
        config.exec_compos = False
        self.start(config.video['source_mp4'])

    # 被调起或者从worker线程调用
    def start(self, mp4):
        self.btn_get_video.setDisabled(True)
        self.task = Worker(mp4.replace('\\', '/'), self)
        self.task.start()
        self.statusLabel.setText(
            transobj['processingstatusbar'].replace('{var1}', os.path.basename(mp4)).replace('{var2}',
                                                                                             str(len(config.queue))))

    # receiver  update UI
    def update_data(self, json_data):
        d = json.loads(json_data)
        if d['type'] == "subtitle":
            self.subtitle_area.moveCursor(QTextCursor.End)
            self.subtitle_area.insertPlainText(d['text'])
        elif d['type'] == "logs":
            self.process.moveCursor(QTextCursor.Start)
            self.process.insertPlainText(d['text'].strip()+"\n")
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
            # 判断是否存在下一个mp4，如果存在，则继续执行
            if len(config.queue) > 0:
                # 重置状态
                config.current_status = 'ing'
                config.exec_compos = False
                config.subtitle_end = False
                self.continue_compos.hide()
                self.continue_compos.setText("")
                self.subtitle_area.clear()
                # 填充 输入框
                newmp4 = config.queue.pop(0)
                self.source_mp4.setText(newmp4)
                self.start(newmp4)
            else:
                self.update_start('end')
                if self.task:
                    self.task.timeid = 0

    # update subtitle
    def update_subtitle(self):
        set_process(f"写入字幕：" + f"{config.rootdir}/tmp/{self.task.noextname}/{self.task.noextname}.srt")
        try:
            with open(f"{config.rootdir}/tmp/{self.task.noextname}/{self.task.noextname}.srt", "w",
                      encoding="utf-8") as f:
                c = self.subtitle_area.toPlainText().strip()
                if not c:
                    config.current_status = 'stop'
                    config.subtitle_end = False
                    config.exec_compos = False
                    self.process.moveCursor(QTextCursor.Start)
                    self.process.insertPlainText("not create subtitle")
                    return
                f.write(self.subtitle_area.toPlainText().strip())
            config.subtitle_end = True
            config.exec_compos = True
            self.continue_compos.setDisabled(True)
            self.continue_compos.setText(transobj['waitforend'])
        except Exception as e:
            set_process("[error]:写入字幕出错了：" + str(e))
            logger.error("[error]:写入字幕出错了：" + str(e))


# set baidu appid and secrot
class BaiduForm(QDialog, Ui_baiduform):  # <===
    def __init__(self, parent=None):
        super(BaiduForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon("./icon.ico"))


class DeepLForm(QDialog, Ui_deeplform):  # <===
    def __init__(self, parent=None):
        super(DeepLForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon("./icon.ico"))


# set chatgpt api and key
class ChatgptForm(QDialog, Ui_chatgptform):  # <===
    def __init__(self, parent=None):
        super(ChatgptForm, self).__init__(parent)
        self.setupUi(self)
        self.chatgpt_model.addItems(["gpt-3.5-turbo", "gpt-4-turbo", "gpt-4"])
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon("./icon.ico"))

def is_vlc():
    try:
        if find_lib() is None:
            config.is_vlc=False
        else:
            config.is_vlc=True
    except:
        config.is_vlc=False


if __name__ == "__main__":
    threading.Thread(target=set_voice_list).start()
    threading.Thread(target=is_vlc).start()
    app = QApplication(sys.argv)
    main = MainWindow()
    try:
        if not os.path.exists(os.path.join(config.rootdir, "models")):
            os.mkdir(os.path.join(config.rootdir, "models"))
        if not os.path.exists(os.path.join(config.rootdir, "tmp")):
            os.mkdir(os.path.join(config.rootdir, "tmp"))
        if shutil.which('ffmpeg') is None:
            QMessageBox.critical(main, transobj['anerror'], transobj["installffmpeg"])
    except Exception as e:
        QMessageBox.critical(main, transobj['anerror'], transobj['createdirerror'])

    if sys.platform == 'win32':
        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
    main.show()
    sys.exit(app.exec())
