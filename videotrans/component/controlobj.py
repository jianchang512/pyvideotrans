import os

from PySide6.QtWidgets import QPlainTextEdit


class TextGetdir(QPlainTextEdit):
    def __init__(self, parent=None):
        super(TextGetdir, self).__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        file = event.mimeData().text()
        ext = file.split(".")[-1]
        if ext not in ["srt"]:
            event.ignore()
        event.accept()

    def dropEvent(self, event):
        file = event.mimeData().text().replace('file:///', '')
        if file.endswith(".srt") and os.path.exists(file):
            with open(file, "r", encoding="utf-8") as f:
                self.setPlainText(f.read().strip())
