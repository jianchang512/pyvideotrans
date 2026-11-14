# 单独一个线程用于检测 GPU 数量
import time
import traceback

from PySide6.QtCore import QThread, Signal
from videotrans.configure.config import logger, app_cfg
from videotrans.util.gpus import get_device_choices


class AiLoaderThread(QThread):
    gpu_io = Signal(str)

    def run(self):
        try:
            _st = time.time()
            from . import gpus
            _count = gpus.getset_gpu()
            logger.debug(f"找到 {_count} 个 GPUs, 耗时: {int(time.time() - _st)}s")
            app_cfg.dev_choices = get_device_choices()
            self.gpu_io.emit("end")
        except Exception as e:
            err = traceback.format_exc()
            self.gpu_io.emit(f'{e},{err}')
