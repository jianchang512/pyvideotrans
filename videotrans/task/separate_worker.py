# 从日志队列获取日志
import json
import os

from PySide6.QtCore import QThread, Signal as pyqtSignal

from videotrans.configure import config
from videotrans.separate import st
from videotrans.util import tools


class SeparateWorker(QThread):
    finish_event = pyqtSignal(str)

    def __init__(self, *,basename=None, file=None,out=None,parent=None):
        super().__init__(parent=parent)
        self.basename=basename
        self.file=file
        self.out=out

    def run(self):
        try:
            # 如果不是wav，需要先转为wav
            if not self.file.lower().endswith('.wav'):
                newfile = os.path.join(config.homedir, f'tmp/{self.basename}.wav').replace('\\', '/')
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
                tools.runffmpeg(cmd, is_box=True)
                self.file = newfile
            st.start(self.file,self.out,"win")
            #gr = st.uvr(model_name="HP2", save_root=self.out, inp_path=self.file,source="win")
            
            if config.separate_status=='ing':
                self.finish_event.emit("succeed")
            else:
                self.finish_event.emit("end")
        except Exception as e:
            if config.separate_status=='ing':
                msg=f"separate vocal and background music:{str(e)}"
                self.finish_event.emit(msg)
        finally:
            config.separate_status='stop'

