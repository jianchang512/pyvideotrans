import platform
import re
import time
import tempfile

from pathlib import Path

from PySide6.QtCore import QTimer

from videotrans.configure.config import tr, app_cfg
from videotrans.configure import contants
from videotrans.configure.contants import LISTEN_TEXT
from videotrans.util.help_misc import open_url, show_error


class WinActionBaseMiscMixin:

    def about(self):
        if app_cfg.child_forms.get('information'):
            app_cfg.child_forms.get('information').show()
            return

        from videotrans.component.set_form import InfoForm
        def open():
            app_cfg.child_forms['information'] = InfoForm()
            app_cfg.child_forms['information'].show()

        QTimer.singleShot(200, open)

    def check_cuda(self, state):
        res = state
        if platform.system() == 'Darwin':
            self.cfg['is_cuda'] = False
            return
        if state and app_cfg.NVIDIA_GPU_NUMS == 0:
            show_error(tr('nocuda'))
            self.main.enable_cuda.setChecked(False)
            self.main.enable_cuda.setDisabled(True)
            res = False
        self.cfg['is_cuda'] = res

    def check_voice_autorate(self, state):
        if state:
            self.main.remove_silent_mid.setVisible(False)
            self.main.align_sub_audio.setVisible(False)
        elif not self.main.video_autorate.isChecked():
            self.main.remove_silent_mid.setVisible(True)
            self.main.align_sub_audio.setVisible(True)

    def check_video_autorate(self, state):
        if state:
            self.main.remove_silent_mid.setVisible(False)
            self.main.align_sub_audio.setVisible(False)
        elif not self.main.voice_autorate.isChecked():
            self.main.remove_silent_mid.setVisible(True)
            self.main.align_sub_audio.setVisible(True)

    def check_txt(self, txt=''):
        if txt and not re.search(r'\d{1,2}:\d{1,2}:\d{1,2}(.\d+)?\s*?-->\s*?\d{1,2}:\d{1,2}:\d{1,2}(.\d+)?', txt):
            show_error(
                tr("Subtitle format is not correct, please re-import the subtitle or delete the imported subtitle."))
            return False
        return True

    def cuda_isok(self):
        if not self.main.enable_cuda.isChecked() or platform.system() == 'Darwin':
            self.cfg['is_cuda'] = False
            return True

        if app_cfg.NVIDIA_GPU_NUMS == 0:
            self.cfg['is_cuda'] = False
            show_error(tr("nocuda"))
            return False
        self.cfg['is_cuda'] = True
        return True

    def listen_voice_fun(self):
        from videotrans import translator
        from videotrans.util.ListenVoice import ListenVoice
        lang = translator.get_code(show_text=self.main.target_language.currentText())
        if not lang:
            return show_error(
                tr("Please select the target language first"))

        text = LISTEN_TEXT.get(f'{lang}')
        if not text:
            return show_error(tr("The voice is not support listen"))
        role = self.main.voice_role.currentText()
        if not role or role == 'No':
            return show_error(tr('mustberole'))

        voice_dir = tempfile.gettempdir() + '/pyvideotrans'
        if not Path(voice_dir).exists():
            Path(voice_dir).mkdir(parents=True, exist_ok=True)
        rate = int(self.main.voice_rate.value())
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"

        volume = int(self.main.volume_rate.value())
        volume = f'+{volume}%' if volume >= 0 else f'{volume}%'
        pitch = int(self.main.pitch_rate.value())
        pitch = f'+{pitch}Hz' if pitch >= 0 else f'{volume}Hz'

        voice_file = f"{voice_dir}/{time.time()}.wav"
        obj = {
            "text": text,
            "rate": rate,
            "role": role,
            "filename": voice_file,
            "tts_type": self.main.tts_type.currentIndex(),
            "language": lang,
            "volume": volume,
            "pitch": pitch,
        }
        if role == 'clone':
            show_error(
                tr("The original sound clone cannot be auditioned"))
            return
        raw_text = self.main.listen_btn.text()
        def feed(d):
            self.main.listen_btn.setDisabled(False)
            self.main.listen_btn.setText(raw_text)
            if d != "ok":
                show_error(d)

        self.main.listen_btn.setDisabled(True)
        self.main.listen_btn.setText('load...')
        wk = ListenVoice(parent=self.main, queue_tts=[obj], language=lang, tts_type=obj['tts_type'])
        wk.uito.connect(feed)
        wk.start()

    def show_listen_btn(self, role):
        voice_role = self.main.voice_role.currentText()
        from videotrans import tts
        _tip = tts.clone_tips(self.main.tts_type.currentIndex(), voice_role, self.main.recogn_type.currentIndex())
        if _tip:
            self.main.show_tips.setText(_tip)
        if role == 'No' or voice_role == 'clone':
            self.main.listen_btn.hide()
            return
        if self.main.app_mode in ['biaozhun']:
            self.main.listen_btn.show()
            self.main.listen_btn.setDisabled(False)

    def check_name(self):
        if self.main.app_mode != 'tiqu':
            for it in self.queue_mp4:
                if Path(it).suffix.lower() in contants.AUDIO_EXITS:
                    self.main.app_mode = 'tiqu'
                    break
        return True

    def lawalert(self):
        from videotrans.ui.lawalert import Ui_lawalert
        self.law = Ui_lawalert(self.main)
        self.law.show()
        self.law.raise_()
        self.law.activateWindow()

    def open_url(self, title):
        open_url(title)
