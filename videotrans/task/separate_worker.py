# 从日志队列获取日志
import threading

from PySide6.QtCore import QThread, Signal as pyqtSignal

from videotrans.configure import config
from videotrans.separate import st
from videotrans.util import tools


class SeparateWorker(QThread):
    finish_event = pyqtSignal(str)

    def __init__(self, *, basename=None, file=None, out=None, parent=None, uuid=None):
        super().__init__(parent=parent)
        self.basename = basename
        self.file = file
        self.out = out
        self.uuid = uuid

    def getqueulog(self):
        while 1:
            if config.exit_soft:
                return
            if self.uuid in config.stoped_uuid_set:
                return
            q = config.uuid_logs_queue.get(self.uuid)
            if not q:
                continue
            try:
                data = q.get(True, 0.5)
                if data:
                    self.finish_event.emit('logs:' + data['text'])
            except Exception:
                pass

    def run(self):
        try:
            # 如果不是wav，需要先转为wav
            if not self.file.lower().endswith('.wav'):
                newfile = config.TEMP_HOME + f'/{self.basename}.wav'
                cmd = [
                    "-y",
                    "-i",
                    self.file,
                    "-ac",
                    "1",
                    "-ar",
                    "44100",
                    newfile
                ]
                if self.basename.split('.')[-1].lower() in ['mp4', 'mov', 'mkv', 'mpeg']:
                    cmd.insert(3, '-vn')
                tools.runffmpeg(cmd)
                self.file = newfile
            tools.set_process(uuid=self.uuid)
            threading.Thread(target=self.getqueulog).start()
            st.start(self.file, self.out, "win", uuid=self.uuid)
        except Exception as e:
            msg = f"separate vocal and background music:{str(e)}"
            self.finish_event.emit(msg)
        else:
            self.finish_event.emit('succeed')
