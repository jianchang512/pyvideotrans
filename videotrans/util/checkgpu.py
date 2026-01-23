import time

from PySide6.QtCore import QThread


class AiLoaderThread(QThread):
    def run(self):
        print("preload transformers/torch/ctranslate2...")
        try:
            _st=time.time()
            from . import gpus
            _count=gpus.getset_gpu()
            print(f"preload set gpus: CUDA={_count}, cost={int(time.time()-_st)}s")
        except Exception as e:
            import traceback
            print(traceback.format_exc())

