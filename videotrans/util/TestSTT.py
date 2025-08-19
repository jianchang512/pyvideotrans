from PySide6.QtCore import QThread, Signal


class TestSTT(QThread):
    uito = Signal(str)

    def __init__(self, *, parent=None, recogn_type=0, model_name=''):
        super().__init__(parent=parent)
        self.recogn_type = recogn_type
        self.model_name = model_name

    def run(self):
        try:
            from videotrans import recognition
            from videotrans.configure import config
            from videotrans.util import tools
            config.box_recogn = 'ing'
            res = recognition.run(
                audio_file=config.ROOT_DIR + '/videotrans/styles/no-remove.mp3',
                cache_folder=config.SYS_TMP,
                recogn_type=self.recogn_type,
                model_name=self.model_name,
                detect_language="zh-cn"
            )
            srt_str = tools.get_srt_from_list(res)
            self.uito.emit(f"ok:{srt_str}")
        except Exception as e:
            self.uito.emit(str(e))
