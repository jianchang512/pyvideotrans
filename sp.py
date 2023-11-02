import json
import re
import shutil
import subprocess
import sys
import os
import threading
from PyQt5.QtGui import QTextCursor, QIcon
from config import langlist, transobj, logger
import config
from tools import get_list_voices, get_large_audio_transcription, runffmpeg

from PyQt5.QtCore import pyqtSignal, QThread, QSettings
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QFileDialog
import qdarkstyle
import pywinstyles
import warnings

warnings.filterwarnings('ignore')

if config.defaulelang == "zh":
    from cn import Ui_MainWindow
else:
    from en import Ui_MainWindow


# get edge tts voice role
def set_voice_list():
    config.voice_list = get_list_voices()


# task process thread
class Worker(QThread):
    update_ui = pyqtSignal(str)

    def run(self):
        print("sowshisls")
        if not config.video['source_mp4']:
            self.update_ui.emit(json.dumps({"text": transobj['selectvideodir'] + "\n", "type": "stop"}))
            return
        return self.running(config.video['source_mp4'])

    # post message to main thread
    def postmessage(self, text, type):
        self.update_ui.emit(json.dumps({"text": f"{text}\n", "type": type}))

    # running fun
    def running(self, p):
        dirname = os.path.dirname(p)
        # remove whitespace
        mp4nameraw = os.path.basename(p)
        mp4name = mp4nameraw.replace(" ", '')
        if mp4nameraw != mp4name:
            os.rename(p, os.path.join(os.path.dirname(p), mp4name))
        #  no ext video name,eg. 1123  mp4
        noextname = os.path.splitext(mp4name)[0]
        # subtitle filepath
        sub_name = f"{dirname}/{noextname}.srt"
        # split audio wav
        a_name = f"{dirname}/{noextname}.wav"
        self.postmessage(f"{mp4name} start", "logs")
        if os.path.exists(sub_name):
            os.unlink(sub_name)

        if not os.path.exists(a_name):
            self.postmessage(f"{mp4name} split audio", "logs")
            # os.system(f"ffmpeg -i {dirname}/{mp4name} -acodec pcm_s16le -f s16le -ac 1  -f wav {a_name}")
            runffmpeg("-i", f"{dirname}/{mp4name}", "-acodec", "pcm_s16le", "-f", "s16le", "-ac", "1", "-f", "wav",
                      f"{a_name}")
        # remove background music ouput a_name{voial}.wav
        if config.video['voice_role'] != 'No' and config.video['remove_background']:
            if self.isInterruptionRequested():
                return
            from spleeter.separator import Separator
            separator = Separator('spleeter:2stems', multiprocess=False)
            separator.separate_to_file(a_name, destination=dirname, filename_format="{filename}{instrument}.{codec}")
            a_name = f"{dirname}/{noextname}vocals.wav"

        # main
        try:
            get_large_audio_transcription(a_name, mp4name, sub_name, self.postmessage)
        except Exception as e:
            logger.error(str(e))
            exit(1)
        self.postmessage(f"{mp4name} end", "end")
        # del temp files
        shutil.rmtree(os.path.join(config.rootdir, "tmp"))

        if os.path.exists(f"{dirname}/{noextname}vocals.wav"):
            os.unlink(f"{dirname}/{noextname}vocals.wav")
        if os.path.exists(f"{dirname}/{noextname}accompaniment.wav"):
            os.unlink(f"{dirname}/{noextname}accompaniment.wav")
        if os.path.exists(f"{dirname}/##{noextname}vocals_tmp"):
            shutil.rmtree(f"{dirname}/##{noextname}vocals_tmp")
        if os.path.exists(f"{dirname}/{noextname}.wav"):
            os.unlink(f"{dirname}/{noextname}.wav")
        if os.path.exists(f"{dirname}/##{noextname}_tmp"):
            shutil.rmtree(f"{dirname}/##{noextname}_tmp")


# UI
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.initUI()

    def initUI(self):
        self.settings = QSettings("Jameson", "VideoTranslate")
        # 获取最后一次选择的目录
        self.last_dir = self.settings.value("last_dir", ".", str)
        self.task = None

        self.splitter.setSizes([830, 350])
        self.languagename = list(langlist.keys())

        self.startbtn.clicked.connect(self.start)

        self.btn_get_video.clicked.connect(self.get_mp4)
        self.btn_save_dir.clicked.connect(self.get_save_dir)

        self.source_language.addItems(self.languagename)
        self.target_language.addItems(["-"] + self.languagename)
        self.target_language.currentTextChanged.connect(self.set_voice_role)

        self.voice_role.addItems(['No'])
        self.whisper_model.addItems(['base', 'small', 'medium', 'large'])
        self.whisper_model.setCurrentText(
            self.settings.value("whisper_model", config.video['whisper_model'], str))

        self.proxy.setText(self.settings.value("target_dir", "", str))
        self.proxy.setText(self.settings.value("proxy", "", str))

        self.voice_rate.setText(self.settings.value("voice_rate", config.video['voice_rate'], str))
        self.voice_silence.setText(self.settings.value("voice_silence", config.video['voice_silence'], str))

        self.voice_autorate.setChecked(
            self.settings.value('voice_autorate', config.video['voice_autorate'], bool))
        self.remove_background.setChecked(
            self.settings.value('remove_background', config.video['remove_background'], bool))
        self.insert_subtitle.setChecked(
            self.settings.value('insert_subtitle', config.video['insert_subtitle'], bool))
        self.source_language.setCurrentIndex(2)
        self.setWindowIcon(QIcon("./icon.ico"))

    # start or stop ,update start button text and stop worker thread
    def update_start(self, type):
        config.current_status = type
        self.startbtn.setText(transobj[type])
        if (type == 'stop' or type == 'end') and self.task:
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
            return
        try:
            vt = langlist[t][0].split('-')[0]
            print(f"{t=},{vt=}")
            if vt not in config.voice_list:
                self.voice_role.addItems(['No'])
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
        config.current_status = 'ing'
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

        config.video['source_language'] = langlist[self.source_language.currentText()][0]
        target_language = self.target_language.currentText()
        if '-' == target_language:
            self.update_start("stop")
            QMessageBox.critical(self, transobj['anerror'], transobj['shoundselecttargetlanguage'])
            return

        config.video['target_language'] = langlist[target_language][0]

        if config.video['source_language'] == config.video['target_language']:
            self.update_start("stop")
            QMessageBox.critical(self, transobj['anerror'], transobj['sourenotequaltarget'])
            return

        config.video['detect_language'] = langlist[self.source_language.currentText()][0]
        config.video['subtitle_language'] = langlist[self.target_language.currentText()][1]

        config.video['voice_role'] = self.voice_role.currentText()
        config.video['whisper_model'] = self.whisper_model.currentText()

        config.video['voice_autorate'] = self.voice_autorate.isChecked()
        config.video['remove_background'] = self.remove_background.isChecked()
        config.video['insert_subtitle'] = self.insert_subtitle.isChecked()

        if not config.video['insert_subtitle'] and (config.video['voice_role'] == 'No'):
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
        print(config.video)
        self.settings.setValue("target_dir", config.video['target_dir'])
        self.settings.setValue("proxy", config.video['proxy'])
        self.settings.setValue("whisper_model", config.video['whisper_model'])
        self.settings.setValue("voice_rate", config.video['voice_rate'])
        self.settings.setValue("voice_silence", config.video['voice_silence'])
        self.settings.setValue("voice_autorate", config.video['voice_autorate'])
        self.settings.setValue("remove_background", config.video['remove_background'])
        self.settings.setValue("insert_subtitle", config.video['insert_subtitle'])
        if not os.path.exists(os.path.join(config.rootdir, "tmp")):
            os.mkdir(os.path.join(config.rootdir, "tmp"))
        self.task = Worker()
        self.task.update_ui.connect(self.update_data)
        self.task.start()

    # update UI
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


if __name__ == "__main__":
    # Edge TTS support voice role
    threading.Thread(target=set_voice_list).start()
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt5'))
    main = MainWindow()

    pywinstyles.apply_style(main, "win7")

    main.show()
    sys.exit(app.exec())
