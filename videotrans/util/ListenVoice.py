from PySide6.QtCore import QThread, Signal


class ListenVoice(QThread):
    uito = Signal(str)

    def __init__(self, *, parent=None, queue_tts=None, language=None, tts_type=None):
        super().__init__(parent=parent)
        self.queue_tts = queue_tts
        self.tts_type = tts_type
        self.language = language

    def run(self):
        try:
            from videotrans import tts
            from videotrans.configure import config
            config.box_tts = 'ing'
            tts.run(
                queue_tts=self.queue_tts,
                language=self.language,
                play=True,
                is_test=True
            )
            self.uito.emit("ok")
        except Exception as e:
            from videotrans.configure._except import get_msg_from_except
            import traceback
            except_msg=get_msg_from_except(e)
            msg = f'{except_msg}:' + traceback.format_exc()
            self.uito.emit(msg)
