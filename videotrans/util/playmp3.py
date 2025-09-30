
import pygame
from PySide6.QtCore import QThread


class AudioPlayer(QThread):
    def __init__(self, filepath):
        super().__init__()
        pygame.mixer.init()
        self.sound = pygame.mixer.Sound(filepath)

    def run(self):
        self.sound.play()
        while pygame.mixer.get_busy():
            pygame.time.Clock().tick(10)
