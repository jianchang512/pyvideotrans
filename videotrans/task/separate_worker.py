# 从日志队列获取日志
from PySide6.QtCore import QThread, Signal as pyqtSignal

from videotrans.configure import config
from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
from videotrans.process.prepare_audio import vocal_bgm
from videotrans.process.signelobj import GlobalProcessManager
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
        self.vocal=None
        self.error=None

    def run(self):
        try:
            p=Path(self.file)
            self.vocal=f"{self.out}/vocal-{p.stem}.wav"
            # 如果不是wav，需要先转为wav
            if  p.suffix.lower()!= '.wav':
                newfile = TEMP_DIR + f'/sep-{time.time()}.wav'
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
            tools.set_process(uuid=self.uuid)
            kw={"input_file":self.file,"vocal_file":self.vocal,"instr_file":f"{self.out}/instrument-{p.stem}.wav","TEMP_DIR":TEMP_DIR}
            future=GlobalProcessManager.submit_task_cpu(
                        vocal_bgm,
                        **kw
                    )
            rs,err=future.result()
            if rs is False:
                self.finish_event.emit(err)
        except Exception as e:
            msg = f"error:separate vocal and background music:{str(e)}"
            self.error=msg
            self.finish_event.emit(msg)
        else:
            self.finish_event.emit('succeed')
