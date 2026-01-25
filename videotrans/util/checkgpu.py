# 单独一个线程用于检测 GPU 数量
import time

from PySide6.QtCore import QThread, Signal


class AiLoaderThread(QThread):
    gpu_io = Signal(str)

    def run(self):
        try:
            _st = time.time()
            from . import gpus
            _count = gpus.getset_gpu()
            print(f"Found {_count} GPUs, cost={int(time.time() - _st)}s")
            self.gpu_io.emit("end")
        except Exception:
            import traceback
            err = traceback.format_exc()
            self.gpu_io.emit(err)
