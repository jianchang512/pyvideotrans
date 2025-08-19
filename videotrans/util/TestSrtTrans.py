from PySide6.QtCore import Signal, QThread


class TestSrtTrans(QThread):
    uito = Signal(str)

    def __init__(self, *, parent=None, translator_type=0):
        super().__init__(parent=parent)
        self.translator_type = translator_type

    def run(self):
        try:
            from videotrans import translator
            raw = "你好啊我的朋友"
            text = translator.run(translate_type=self.translator_type,
                                  text_list=raw,
                                  target_code="en",
                                  source_code="zh-cn",
                                  is_test=True
                                  )
            self.uito.emit(f"ok:{raw}\n{text}")
        except Exception as e:
            self.uito.emit(str(e))
