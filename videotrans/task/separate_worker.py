# 从日志队列获取日志
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal as pyqtSignal

from videotrans.configure.config import tr, settings, logger
from videotrans.configure import config
from videotrans.process.prepare_audio import vocal_bgm
from videotrans.process.signelobj import GlobalProcessManager
from videotrans.util import tools


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
            self.finish_event.emit(f'logs:{tr("Separating vocals and background music, which may take a longer time")} ...')
            # 如果不是wav，需要先转为wav
            if  p.suffix.lower()!= '.wav':
                newfile = config.TEMP_DIR + f'/sep-{time.time()}.wav'
                cmd = [
                    "-y",
                    "-i",
                    self.file,
                    "-vn",
                    "-ac",
                    "2",
                    "-ar",
                    "44100",
                    newfile
                ]
                tools.runffmpeg(cmd)
                self.file = newfile
            tools.set_process(text='start separate...',uuid=self.uuid)
            kw={"input_file":self.file,"vocal_file":self.vocal,"instr_file":f"{self.out}/instrument-{p.stem}.wav","uvr_models":settings.get('uvr_models')}
            future=GlobalProcessManager.submit_task_cpu(
                        vocal_bgm,
                        **kw
                    )
            rs,err=future.result(timeout=7200*2)
            self.finish_event.emit('error:'+err if rs is False else 'succeed')
        except Exception as e:
            logger.exception(f'分离人声背景声失败{e}',exc_info=True)
            msg = f"error:separate vocal and background music:{str(e)}"
            self.error=msg
            self.finish_event.emit(msg)
