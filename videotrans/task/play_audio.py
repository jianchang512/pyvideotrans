import os

# import pygame
from PySide6.QtCore import QThread, Signal as pyqtSignal

from videotrans.configure import config
from videotrans.tts import text_to_speech
from videotrans.util import tools
from videotrans.util.tools import pygameaudio
from pathlib import Path

class PlayMp3(QThread):
    mp3_ui=pyqtSignal(str)
    def __init__(self,obj,parent=None):
        super(PlayMp3, self).__init__(parent)
        self.obj=obj
    def run(self):
        try:
            if not tools.vail_file(self.obj['voice_file']):
                print(self.obj)
                print(f'play role={self.obj["role"]}')
                text_to_speech(
                    text=self.obj['text'],
                    role=self.obj['role'],
                    tts_type=self.obj['tts_type'],
                    filename=self.obj['voice_file'],
                    play=True,
                    volume=self.obj['volume'],
                    pitch=self.obj['pitch'],
                    language=self.obj['language'])
            else:
                pygameaudio(self.obj['voice_file'])
        except Exception as e:
            print(f'play {str(e)}')
            self.mp3_ui.emit(str(e))

