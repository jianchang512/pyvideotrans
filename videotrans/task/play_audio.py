import os

# import pygame
from PySide6.QtCore import QThread, Signal as pyqtSignal

from videotrans.configure import config
from videotrans.tts import text_to_speech
from videotrans.util.tools import pygameaudio


class PlayMp3(QThread):
    mp3_ui=pyqtSignal(str)
    def __init__(self,obj,parent=None):
        super(PlayMp3, self).__init__(parent)
        self.obj=obj
    def run(self):
        try:
            if not os.path.exists(self.obj['voice_file']) or os.path.getsize(self.obj['voice_file'])==0:
                text_to_speech(text=self.obj['text'],role=self.obj['role'],tts_type=config.params['tts_type'],filename=self.obj['voice_file'], play=True,language=self.obj['language'])
            else:
                pygameaudio(self.obj['voice_file'])
        except Exception as e:
            self.mp3_ui.emit(str(e))

