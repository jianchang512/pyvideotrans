# -*- coding: utf-8 -*-
import json
import sys
import os
import threading
import time

from PyQt5 import QtCore
from PyQt5.QtGui import QTextCursor, QIcon
from PyQt5.QtCore import pyqtSignal, QThread, QSettings
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QFileDialog, QInputDialog, QWidget, QDialog

import warnings

import configure.tools
from configure.chatgpt import Ui_chatgptform

warnings.filterwarnings('ignore')

from configure.config import langlist, transobj, logger
from configure.language import english_code_bygpt
from configure.tools import get_list_voices, get_large_audio_transcription, runffmpeg, delete_temp, dubbing
from configure import config
from configure.baidu import Ui_baiduform

if config.defaulelang == "zh":
    from configure.cn import Ui_MainWindow
else:
    from configure.en import Ui_MainWindow


# get edge tts voice role
def set_voice_list():
    config.voice_list = get_list_voices()


# task process thread
class Worker(QThread):
    update_ui = pyqtSignal(str)
    # None wait manual ,nums wait
    timeid = 0

    def run(self):
        if not config.video['source_mp4']:
            self.postmessage(transobj['selectvideodir'], "stop")
            return
        self.running(config.video['source_mp4'])
        self.postmessage(f"{self.mp4name} wait subtitle edit :", "wait_subtitle")
        self.wait_subtitle()

    def wait_subtitle(self):
        self.timeid = 0
        while True:
            if not config.wait_subtitle_edit:
                time.sleep(1)
                if self.timeid is not None:
                    self.postmessage(f"{self.mp4name} after {60 - self.timeid}s auto Composing video:", "logs")
                    self.timeid += 1
                if self.timeid is None or self.timeid < 60:
                    if self.timeid is None:
                        self.postmessage(f"{self.mp4name} wait manual Composing video:", "logs")
                    continue
            try:
                # timeout auto
                config.wait_subtitle_edit = True
                self.postmessage(f"{self.mp4name}", "update_subtitle")
                dubbing(self.a_name, self.mp4name, self.sub_name, self.postmessage)
                self.postmessage(f"{self.mp4name} end", "end")
                break
            except Exception as e:
                logger.error("Get_large_audio_transcription error:" + str(e))
                sys.exit()

        self.postmessage(f"{self.mp4name} end", "end")
        delete_temp(self.dirname, self.noextname)

    # post message to main thread
    def postmessage(self, text, type):
        self.update_ui.emit(json.dumps({"text": f"{text}\n", "type": type}))

    # running fun
    def running(self, p):
        # p is full source mp4 filepath
        self.dirname = os.path.dirname(p)
        # remove whitespace
        mp4nameraw = os.path.basename(p)
        self.mp4name = mp4nameraw.replace(" ", '')
        if mp4nameraw != self.mp4name:
            os.rename(p, os.path.join(os.path.dirname(p), self.mp4name))
        #  no ext video name,eg. 1123.mp4 to convert 1123
        self.noextname = os.path.splitext(self.mp4name)[0]
        # subtitle filepath
        self.sub_name = f"{self.dirname}/{self.noextname}.srt"
        # split audio wav
        self.a_name = f"{self.dirname}/{self.noextname}.wav"
        self.postmessage(f"{self.mp4name} start", "logs")
        if os.path.exists(self.sub_name):
            os.unlink(self.sub_name)

        if not os.path.exists(self.a_name):
            self.postmessage(f"{self.mp4name} split audio", "logs")
            runffmpeg(f"-y -i {self.dirname}/{self.mp4name} -acodec pcm_s16le -ac 1 -f wav {self.a_name}")

        # main
        try:
            get_large_audio_transcription(self.a_name, self.mp4name, self.sub_name, self.postmessage)
        except Exception as e:
            logger.error("Get_large_audio_transcription error:" + str(e))
            sys.exit()


# primary ui
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.initUI()

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
        config.video['chatgpt_api'] = self.settings.value("chatgpt_api", "")
        config.video['chatgpt_key'] = self.settings.value("chatgpt_key", "")
        config.video['chatgpt_model'] = self.settings.value("chatgpt_model", config.video['chatgpt_model'])
        config.video['chatgpt_template'] = self.settings.value("chatgpt_template", config.video['chatgpt_template'])
        config.video['translate_type'] = self.settings.value("translate_type", config.video['translate_type'])
        config.video['subtitle_type'] = self.settings.value("subtitle_type", config.video['subtitle_type'], int)
        config.video['proxy'] = self.settings.value("proxy", "", str)
        config.video['target_dir'] = self.settings.value("target_dir", "", str)
        config.video['voice_rate'] = self.settings.value("voice_rate", config.video['voice_rate'], str)
        config.video['voice_silence'] = self.settings.value("voice_silence", config.video['voice_silence'], str)
        config.video['voice_autorate'] = self.settings.value("voice_autorate", config.video['voice_autorate'], bool)
        config.video['whisper_model'] = self.settings.value("whisper_model", config.video['whisper_model'], str)

        self.splitter.setSizes([830, 350])

        # start
        self.startbtn.clicked.connect(self.start)
        # subtitle btn
        self.nextbtn.hide()

        # select and save
        self.btn_get_video.clicked.connect(self.get_mp4)
        self.btn_save_dir.clicked.connect(self.get_save_dir)
        self.target_dir.setText(config.video['target_dir'])
        self.proxy.setText(config.video['proxy'])

        # language
        self.source_language.addItems(self.languagename)
        self.source_language.setCurrentIndex(2)
        self.target_language.addItems(["-"] + self.languagename)
        self.target_language.currentTextChanged.connect(self.set_voice_role)

        #  translation type
        self.translate_type.addItems(["google", "baidu", "chatGPT", "baidu(noKey)"])
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
        self.voice_role.addItems(['No'])

        # subtitle 0 no 1=embed subtitle 2=softsubtitle
        self.subtitle_type.addItems([transobj['nosubtitle'], transobj['embedsubtitle'], transobj['softsubtitle']])
        self.subtitle_type.setCurrentIndex(config.video['subtitle_type'])

        # menubar
        self.actionbaidu_key.triggered.connect(self.set_baidu_key)
        self.actionchatgpt_key.triggered.connect(self.set_chatgpt_key)

        # status
        self.statusBar.showMessage(transobj['modelpathis'] + config.rootdir + "/models")

        self.setWindowIcon(QIcon("./icon.ico"))

    # stop auto comping video
    def reset_timeid(self):
        self.task.timeid = None

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
                QMessageBox.information(self, transobj['anerror'], transobj['baidukeymust'])
                return
            if name == "chatGPT" and not config.video["chatgpt_key"]:
                QMessageBox.information(self, transobj['anerror'], transobj['chatgptkeymust'])
                return
            config.video['translate_type'] = name
        except Exception as e:
            QMessageBox.information(self, transobj['anerror'], str(e))

    # check model is exits
    def check_whisper_model(self, name):
        if not os.path.exists(config.rootdir + f"/models/{name}.pt"):
            self.statusBar.showMessage(transobj['downloadmodel'] + f" ./models/{name}.pt")
            QMessageBox.information(self, transobj['downloadmodel'], f"./models/{name}.pt")
        else:
            self.statusBar.showMessage(transobj['modelpathis'] + f" ./models/{name}.pt")

    # start or stop ,update start button text and stop worker thread
    def update_start(self, type):
        config.current_status = type
        self.startbtn.setText(transobj[type])
        if type == 'stop' or type == 'end':
            config.wait_subtitle_edit = False
            if self.task:
                self.task.requestInterruption()
                self.task.quit()
                self.task.wait()

    # change voice role when target_language changed
    def set_voice_role(self, t):
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
        fname, _ = QFileDialog.getOpenFileName(self, transobj['selectmp4'], self.last_dir, "Video files(*.mp4)")
        self.source_mp4.setText(fname)
        self.settings.setValue("last_dir", os.path.dirname(fname))

    # output dir
    def get_save_dir(self):
        dirname = QFileDialog.getExistingDirectory(self, transobj['selectsavedir'], self.last_dir)
        self.target_dir.setText(dirname)

    # start
    def start(self):
        if config.current_status == 'ing':
            self.update_start('stop')
            return
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
            os.makedirs(target_dir)

        config.video['target_dir'] = target_dir
        config.video['proxy'] = self.proxy.text().strip()
        if config.video['proxy']:
            os.environ['http_proxy'] = 'http://%s' % config.video['proxy'].replace("http://", '')
            os.environ['https_proxy'] = 'http://%s' % config.video['proxy'].replace("http://", '')

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
        elif config.video['translate_type'] == 'baidu':
            # baidu language code
            config.video['target_language'] = langlist[target_language][2]
            if not config.video['baidu_appid'] or not config.video['baidu_miyue']:
                QMessageBox.critical(self, transobj['anerror'], transobj['baikeymust'])
                return
        elif config.video['translate_type'] == 'chatGPT':
            config.video['target_language_chatgpt'] = english_code_bygpt[self.languagename.index(target_language)]
            if not config.video['chatgpt_key']:
                QMessageBox.critical(self, transobj['anerror'], transobj['chatgptkeymust'])
                return

        if config.video['source_language'] == config.video['target_language']:
            self.update_start("stop")
            QMessageBox.critical(self, transobj['anerror'], transobj['sourenotequaltarget'])
            return

        config.video['detect_language'] = langlist[self.source_language.currentText()][0]
        config.video['subtitle_language'] = langlist[self.target_language.currentText()][1]

        config.video['voice_role'] = self.voice_role.currentText()
        config.video['whisper_model'] = self.whisper_model.currentText()

        model = config.rootdir + f"/models/{config.video['whisper_model']}.pt"
        if not os.path.exists(model) or os.path.getsize(model) < 100:
            self.update_start("stop")
            QMessageBox.critical(self, transobj['downloadmodel'], f" ./models/{config.video['whisper_model']}.pt")
            self.statusBar.showMessage(transobj['downloadmodel'] + f" ./models/{config.video['whisper_model']}.pt")
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
        if not os.path.exists(os.path.join(config.rootdir, "tmp")):
            os.mkdir(os.path.join(config.rootdir, "tmp"))
        config.current_status = 'ing'
        config.wait_subtitle_edit = False
        print(config.video)
        self.task = Worker()
        self.task.update_ui.connect(self.update_data)
        self.task.start()

    # receiver  update UI
    def update_data(self, json_data):
        d = json.loads(json_data)
        if d['type'] == "subtitle":
            self.subtitle_area.moveCursor(QTextCursor.End)
            self.subtitle_area.insertPlainText(d['text'])
        elif d['type'] == "logs":
            self.process.moveCursor(QTextCursor.Start)
            self.process.insertPlainText(d['text'])
        elif d['type'] == 'stop' or d['type'] == 'end':
            self.update_start(d['type'])
            self.statusBar.showMessage(d['type'])
            self.nextbtn.hide()
        elif d['type'] == 'wait_subtitle':
            self.nextbtn.show()
            self.nextbtn.clicked.connect(self.nextstart)
            self.nextbtn.setDisabled(False)
            self.nextbtn.setText(transobj['waitsubtitle'])
            self.subtitle_area.textChanged.connect(self.reset_timeid)
        elif d['type'] == 'update_subtitle':
            self.update_subtitle()
        elif d['type'] == 'replace_subtitle':
            self.subtitle_area.clear()
            self.subtitle_area.insertPlainText(d['text'])

    # update subtitle
    def update_subtitle(self):
        with open(self.task.sub_name, "w", encoding="utf-8") as f:
            f.write(self.subtitle_area.toPlainText())
        config.wait_subtitle_edit = True
        self.nextbtn.setDisabled(True)
        self.nextbtn.setText(transobj['waitforend'])

    # nextbtn action
    def nextstart(self):
        self.update_subtitle()


# set baidu appid and secrot
class BaiduForm(QDialog, Ui_baiduform):  # <===
    def __init__(self, parent=None):
        super(BaiduForm, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon("./icon.ico"))


# set chatgpt api and key
class ChatgptForm(QDialog, Ui_chatgptform):  # <===
    def __init__(self, parent=None):
        super(ChatgptForm, self).__init__(parent)
        self.setupUi(self)
        self.chatgpt_model.addItems(["gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-4", "gpt-4v"])
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon("./icon.ico"))


if __name__ == "__main__":
    threading.Thread(target=set_voice_list).start()
    app = QApplication(sys.argv)
    main = MainWindow()
    try:
        if not os.path.exists(os.path.join(config.rootdir, "models")):
            os.mkdir(os.path.join(config.rootdir, "models"))
        if not os.path.exists(os.path.join(config.rootdir, "tmp")):
            os.mkdir(os.path.join(config.rootdir, "tmp"))
    except Exception as e:
        QMessageBox.critical(main, transobj['anerror'], transobj['createdirerror'])
    if sys.platform == 'win32':
        import qdarkstyle
        import pywinstyles

        app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
        pywinstyles.apply_style(main, "win7")
    main.show()
    sys.exit(app.exec())
