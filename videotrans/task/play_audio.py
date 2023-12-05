import os

import pygame
from PyQt5.QtCore import QThread, pyqtSignal

from videotrans.util.tools import text_to_speech, pygameaudio


class PlayMp3(QThread):
    mp3_ui=pyqtSignal(str)
    def __init__(self,obj,parent=None):
        super(PlayMp3, self).__init__(parent)
        self.obj=obj
    def run(self):
        if not os.path.exists(self.obj['voice_file']) or os.path.getsize(self.obj['voice_file'])==0:
            text_to_speech(text=self.obj['text'],role=self.obj['role'],tts_type=self.obj['tts_type'],filename=self.obj['voice_file'], play=True)
        else:
            pygameaudio(self.obj['voice_file'])
        #self.play_mp3()
    def play_mp3(self):
        try:
            print(f"{self.obj['voice_file']=}")
            #pygame.init()
            #pygame.mixer.init()
            pygame.mixer.music.load(self.obj['voice_file'])
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                # 等待音乐播放完成
                pygame.time.Clock().tick(1)

        except pygame.error as e:
            print("Error: ", e)
        pygame.quit()

