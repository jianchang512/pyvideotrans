# 检测 windows/darwin/linux 系统中 nvidia cuda mps vulkan 等支持情况
# 环境差异大，兼容问题突出
# 即便存在nvidia卡，仍需cuda环境配置正确+torch版本正确方可使用
# 即便存在vulkan设备仍需audio.cpp执行获取到方可使用，可能丢失某些so/dll导致有设备但无法使用
# 首选用户明确指定的硬件(如果可用并且正确)
# 次选最佳硬件: cuda/vulkan/mps/cpu
# transformers 保底 auto，其他cpu
# audio.cpp 需最终执行一次 --list-devices 确定能检测到设备方可视为可用

import json
import platform
import re
import shutil
import subprocess
from typing import Dict, List, Any
from pathlib import Path
from videotrans.configure.config import app_cfg, logger, settings,ROOT_DIR
import traceback
from PySide6.QtCore import QThread, Signal
from videotrans.configure import config
from videotrans.util.help_audiocpp import is_support

_os=platform.system()
_DEVICES_LIST=['auto','cuda','mps','metal','vulkan','best']

class AiLoaderThread(QThread):
    gpu_io = Signal(str)
    def run(self):
        try:
            check_hardware_availability()
            self.gpu_io.emit("end")
        except Exception as e:
            err = traceback.format_exc()
            self.gpu_io.emit(f'{e},{err}')


def get_vulkan_devices() -> Dict[str, str]:
    """Return list of available non-CPU Vulkan compute devices in ggml_vulkan order."""
    if _os=='Darwin' or not shutil.which("vulkaninfo"):
        logger.warning('无可用 vulkan 设备')
        return []
    devices: Dict[str, str] = {}
    try:
        proc = subprocess.run(
            ["vulkaninfo", "--summary"],
            capture_output=True,
            text=True,
            timeout=20,
            encoding="utf-8",
            errors="ignore",
        )
        out = proc.stdout or ""
        idx = 0
        for block in re.split(r"\bGPU\d*?:",out):
            if "deviceType" in block and "PHYSICAL_DEVICE_TYPE_CPU" not in block:
                name = f"Vulkan:{idx}"
                for line in block.splitlines():
                    if "deviceName" in line and "=" in line:
                        name = line.split("=", 1)[1].strip()
                        break
                _order=f':{idx}' if idx>0 else ''
                devices[f'{name}{_order}']=f'vulkan:{idx}'
                idx += 1
        logger.debug(f'检测到 Vulkan 可用信息:{devices}')
    except Exception as e:
        logger.error(f"vulkaninfo check failed: {e}")
    return devices



def check_hardware_availability():
    app_cfg.NVIDIA_CUDA_NUMS=0
    app_cfg.MPS_NUMS=0
    devices={config.tr("auto"):"auto"}
    import torch
    if _os == 'Darwin':
        app_cfg.AUDIOCPP_REAL_CUDA=False
        app_cfg.AUDIOCPP_REAL_VULKAN=False
        try:
            if torch.backends.mps.is_built() and torch.backends.mps.is_available():
                app_cfg.MPS_NUMS = 1
                devices["Metal"]="mps"
        except Exception:
            pass
    else:
        # 先判断是否存在n卡
        from pynvml import nvmlInit, nvmlDeviceGetCount, NVMLError
        try:
            nvmlInit()
            app_cfg.NVIDIA_COUNT=nvmlDeviceGetCount()
            logger.debug(f'检测到 nvidia 显卡 {app_cfg.NVIDIA_COUNT} 张')
        except NVMLError:
            # 无nvidia卡
            logger.warning(f'检测到 nvidia 显卡 0 张')
        except Exception:
            pass

        try:
            # 再判断是否torch中可用
            if app_cfg.NVIDIA_COUNT>0 and torch.cuda.is_available():
                app_cfg.NVIDIA_CUDA_NUMS= torch.cuda.device_count()
                for i in range(app_cfg.NVIDIA_CUDA_NUMS):
                    try:
                        _info=torch.cuda.get_device_properties(i)

                        _order=f':{i}' if i>0 else ''
                        _name=f'{_info.name}{_order}({_info.total_memory/1024/1024/1024:.2f}G)'
                        devices[_name]=f'cuda:{i}'
                    except Exception:
                        devices[f'cuda:{i}']=f'cuda:{i}'
            logger.debug(f'检测到可用 NVIDIA CUDA 核: {app_cfg.NVIDIA_CUDA_NUMS}')
        except Exception:
            pass

        app_cfg.VULKAN_LIST=get_vulkan_devices()
    # 准备硬件选择数据用于高级选项


    if app_cfg.VULKAN_LIST:
        devices.update(app_cfg.VULKAN_LIST)


    devices.update({"CPU":"cpu"})
    config.ACCESS_DEVICES=devices
    logger.debug(f'{config.ACCESS_DEVICES=}')


# 用于 faster-whisper /openai-whisper 的设备名， cpu/cuda/mps
# 如果明确指定了设备名如 cuda/mps 且可用，则返回该名，否则优先cuda/mps，保底cpu
def whisper_device(device:str=None,is_cuda:bool=False,allow_mps=False):
    prefix,idx=_format_device(device)

    if not is_cuda or prefix not in _DEVICES_LIST:
        return "cpu"

    if app_cfg.NVIDIA_CUDA_NUMS>0:
        return f'cuda:{idx}' if 0<idx<app_cfg.NVIDIA_CUDA_NUMS else 'cuda'

    if allow_mps and app_cfg.MPS_NUMS>0:
        return "mps"

    return "cpu"


# 用于 transfomers 推理，返回 auto/cpu/cuda/mps
# 如果明确指定了设备名如 cuda/cpu/mps 且可用，则返回该名，否则优先cuda/mps，保底 auto
def transformers_device(device:str=None,is_cuda:bool=False):
    prefix,idx=_format_device(device)
    if not is_cuda or prefix not in _DEVICES_LIST:
        return 'cpu'

    if prefix in ['cuda','vulkan'] and app_cfg.NVIDIA_CUDA_NUMS>0:
        return f'cuda:{idx}' if 0<idx<app_cfg.NVIDIA_CUDA_NUMS else 'cuda'

    if prefix in ['mps','metal'] and app_cfg.MPS_NUMS>0:
        return "mps"

    return "auto"


# 用于 audio.cpp 和 llamp.cpp whisper.cpp
# return cuda/best/cpu/vulkan
# 如果明确指定了设备名如 cuda/cpu/metal/vulkan 且可用，则返回该名，否则优先cuda/metal，其次vulkan，保底 best
def cpp_device(device:str=None,is_cuda:bool=False):
    prefix,idx=_format_device(device)

    # 如果设备指定错误 或 明确指定 cpu
    if not is_cuda or prefix not in _DEVICES_LIST:
        return 'cpu'

    # darwin上只要存在 metal就使用
    if _os=='Darwin':
        return "metal" if real_metal_exists() else "cpu"

    # 如果明确指定 vulkan 并且存在 vulkan
    if prefix=='vulkan' and real_vulkan_exists():
        return f'{prefix}:{idx}' if 0 < idx < len(app_cfg.VULKAN_LIST) else 'vulkan'
    # 其他情况存在 可用n卡则使用
    if real_cuda_exists():
        return f'cuda:{idx}' if 0 < idx < app_cfg.NVIDIA_COUNT else 'cuda'
    # 存在 vulkan
    if real_vulkan_exists():return 'vulkan'
    return 'cpu'


# 在 实际使用 audio.cpp + vulkan 执行之前，需再次通过 audio.cpp --list-devices 判断是否真实存在可用的vulkan，vulkaninfo 可检测到，但实际可能因为驱动老旧、缺失库文件，而无法加速

def real_vulkan_exists():
    # mac或 vulkaninfo 不可用
    if app_cfg.AUDIOCPP_REAL_VULKAN is not None:
        return app_cfg.AUDIOCPP_REAL_VULKAN

    if _os=='Darwin' or not app_cfg.VULKAN_LIST:
        app_cfg.AUDIOCPP_REAL_VULKAN=False


    app_cfg.AUDIOCPP_REAL_VULKAN=is_support(backend="vulkan") is True
    return app_cfg.AUDIOCPP_REAL_VULKAN


# 仅 windows 版本支持cuda，linux使用vulkan，macos使用metal
def real_cuda_exists():
    if app_cfg.AUDIOCPP_REAL_CUDA is not None:
        return app_cfg.AUDIOCPP_REAL_CUDA

    if _os=='Darwin' or app_cfg.NVIDIA_COUNT<1:
        app_cfg.AUDIOCPP_REAL_CUDA=False
        return False

    app_cfg.AUDIOCPP_REAL_CUDA=is_support(backend="cuda") is True
    return app_cfg.AUDIOCPP_REAL_CUDA

def real_metal_exists():
    if app_cfg.AUDIOCPP_REAL_METAL is not None:
        return app_cfg.AUDIOCPP_REAL_METAL

    app_cfg.AUDIOCPP_REAL_METAL=_os=='Darwin' and is_support(backend="metal") is True
    return app_cfg.AUDIOCPP_REAL_METAL




# 是否存在 cuda mps vulkan 任意可用硬件
def exists_hard():
    return app_cfg.NVIDIA_COUNT >0 or app_cfg.NVIDIA_CUDA_NUMS > 0  or app_cfg.MPS_NUMS>0 or app_cfg.VULKAN_LIST

def _format_device(device=None):
    device=device or config.get_select_device()
    idx=0
    prefix=device
    if ':' in device:
        prefix,idx=device.split(":",1)
    prefix=prefix.lower()
    try:
        idx=int(idx) if str(idx).isnumeric() else 0
    except ValueError:
        idx=0
    return prefix,idx
