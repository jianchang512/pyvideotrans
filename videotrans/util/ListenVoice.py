from PySide6.QtCore import QThread, Signal

from videotrans.configure._i18n import tr


class ListenVoice(QThread):
    uito = Signal(str)

    def __init__(self, *, parent=None, queue_tts=None, language=None, tts_type=None):
        super().__init__(parent=parent)
        self.queue_tts = queue_tts
        self.tts_type = tts_type
        self.language = language

    def run(self):
        try:
            if self.queue_tts[0]['role']=='clone':
                self.uito.emit(tr("The original sound clone cannot be auditioned"))
                return
            from videotrans import tts
            tts.run(
                queue_tts=self.queue_tts,
                language=self.language,
                play=True,
                is_test=True,
                tts_type=self.tts_type
            )
            self.uito.emit("ok")
        except Exception as e:
            from videotrans.configure.excepts import get_msg_from_except
            import traceback
            except_msg=get_msg_from_except(e)
            msg = f'{except_msg}:\n{self.queue_tts[0]}\n' + traceback.format_exc()
            self.uito.emit(msg)
