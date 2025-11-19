# 从日志队列获取日志
from PySide6.QtCore import QThread, Signal as pyqtSignal

from videotrans.configure import config
from videotrans.separate import run_sep
from videotrans.task.simple_runnable_qt import run_in_threadpool
from videotrans.util import tools
import time
from pathlib import Path


class SeparateWorker(QThread):
    finish_event = pyqtSignal(str)

    def __init__(self, *, file=None, out=None, parent=None, uuid=None):
        super().__init__(parent=parent)
        self.file = file
        self.uuid = uuid
        self.out = out

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
        print(f'{config.TEMP_HOME=}')
        try:
            
            print(f'1 {self.file=}')
            p=Path(self.file)
            print(f'{p.suffix.lower()=}')
            # 如果不是wav，需要先转为wav
            if  p.suffix.lower()!= '.wav':
                newfile = config.TEMP_HOME + f'/sep-{time.time()}.wav'
                cmd = [
                    "-y",
                    "-i",
                    self.file,
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "44100",
                    newfile
                ]
                
                tools.runffmpeg(cmd)
                self.file = newfile
            print(f'2 {self.file=}')
            print(f'{self.out=}')
            tools.set_process(uuid=self.uuid)
            run_in_threadpool(self.getqueulog)
            run_sep(self.file, f"{self.out}/vocal-{p.stem}.wav", f"{self.out}/instrument-{p.stem}.wav")
        except Exception as e:
            print(e)
            msg = f"error:separate vocal and background music:{str(e)}"
            self.finish_event.emit(msg)
        else:
            self.finish_event.emit('succeed')
