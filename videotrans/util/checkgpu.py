# 单独一个线程用于检测 GPU 数量
import time
import traceback

from PySide6.QtCore import QThread, Signal
from videotrans.configure import config



class AiLoaderThread(QThread):
    gpu_io = Signal(str)

    def run(self):
        try:
            _st = time.time()
            from . import gpus
            gpus.getset_gpu()
            _devices=["auto"]
            if config.app_cfg.NVIDIA_GPU_NUMS>0:
                _devices.append("cuda")
                if config.app_cfg.NVIDIA_GPU_NUMS>1:
                    for i in range(config.app_cfg.NVIDIA_GPU_NUMS):
                        _devices.append(f"cuda:{i}")
            if config.app_cfg.VULKAN_LIST:
                for it in config.app_cfg.VULKAN_LIST:
                    _devices.append(f"vulkan:{it['index']}")
            if config.app_cfg.MPS_NUMS:
                _devices.append("mps")
                _devices.append("metal")
            config.ACCESS_DEVICES=_devices
            self.gpu_io.emit("end")
        except Exception as e:
            err = traceback.format_exc()
            self.gpu_io.emit(f'{e},{err}')
