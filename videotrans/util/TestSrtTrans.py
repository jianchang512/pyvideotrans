from typing import List

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
            text:List[dict] = translator.run(translate_type=self.translator_type,
                                  text_list=[{"text":raw,"line":1,"time":"00:00:00,000 --> 00:00:05,000"}],
                                  target_code="en",
                                  source_code="zh-cn",
                                  is_test=True
                                  )
            print(f'{text=}')
            self.uito.emit(f"ok:{raw}\n{text[0]['text']}")
        except Exception as e:
            from videotrans.configure._except import get_msg_from_except
            import traceback
            except_msg=get_msg_from_except(e)
            msg = f'{except_msg}:' + traceback.format_exc()
            self.uito.emit(msg)

