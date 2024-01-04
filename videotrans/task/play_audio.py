import os

# import pygame
from PyQt5.QtCore import QThread, pyqtSignal

from videotrans.configure import config
from videotrans.util.tools import text_to_speech, pygameaudio


class PlayMp3(QThread):
    mp3_ui=pyqtSignal(str)
    def __init__(self,obj,parent=None):
        super(PlayMp3, self).__init__(parent)
        self.obj=obj
    def run(self):
        if not os.path.exists(self.obj['voice_file']) or os.path.getsize(self.obj['voice_file'])==0:
            text_to_speech(text=self.obj['text'],role=self.obj['role'],tts_type=config.params['tts_type'],filename=self.obj['voice_file'], play=True)
        else:
            pygameaudio(self.obj['voice_file'])

