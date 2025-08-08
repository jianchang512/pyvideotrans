from PySide6.QtCore import QThread, Signal

from videotrans import tts
from videotrans.configure import config


class ListenVoice(QThread):
        uito = Signal(str)

        def __init__(self, *, parent=None, queue_tts=None, language=None, tts_type=None):
            super().__init__(parent=parent)
            self.queue_tts = queue_tts
            self.tts_type=tts_type
            self.language=language

        def run(self):
            try:
                config.box_tts='ing'
                tts.run(
                    queue_tts=self.queue_tts,
                    language=self.language,
                    play=True,
                    is_test=True
                )
                self.uito.emit("ok")
            except Exception as e:
                self.uito.emit(str(e)[:120])
