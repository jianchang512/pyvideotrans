# 1. 获取并缓存可用 gpu 数量 (CUDA + Vulkan)
# 2. 获取可用 cuda / vulkan 号
# 3. MacOSX 是否支持 mps

import platform
import shutil
import subprocess
from typing import Dict, List, Any
from videotrans.configure.config import app_cfg, logger, settings



def get_vulkan_devices() -> List[Dict[str, Any]]:
    """Return list of available non-CPU Vulkan compute devices in ggml_vulkan order."""

    devices: List[Dict[str, Any]] = []
    if shutil.which("vulkaninfo"):
        try:
            proc = subprocess.run(
                ["vulkaninfo", "--summary"],
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="ignore",
            )
            out = proc.stdout or ""
            idx = 0

            for block in out.split("GPU"):
                if "deviceType" in block and "PHYSICAL_DEVICE_TYPE_CPU" not in block:
                    name = f"Vulkan{idx}"
                    for line in block.splitlines():
                        if "deviceName" in line and "=" in line:
                            name = line.split("=", 1)[1].strip()
                            break
                    devices.append({
                        "backend": "vulkan",
                        "index": idx,
                        "name": f"Vulkan{idx}",
                        "description": name,
                        "memory": {"total_bytes": 0},
                    })
                    idx += 1
            logger.debug(f'Vulkan可用信息:{devices}')
        except Exception as e:
            logger.debug(f"vulkaninfo check failed: {e}")
    return devices


# 获取可用的gpu数量 并缓存在 config.NVIDIA_GPU_NUMS 中，0=无可用显卡
#
# force_cpu: 未使用参数
#   True 强制使用 cpu 即强制设定没有显卡
def getset_gpu():
    # 尚未获取过时是 -1
    if app_cfg.NVIDIA_GPU_NUMS > -1:
        return

    app_cfg.NVIDIA_GPU_NUMS=0
    app_cfg.MPS_NUMS=0
    import torch
    if platform.system() == 'Darwin':
        try:
            app_cfg.MPS_NUMS = 1 if torch.backends.mps.is_built() and torch.backends.mps.is_available() else 0
            logger.debug(f'MPS可用？{app_cfg.MPS_NUMS=}')
        except Exception:
            pass
        return

    try:
        if torch.cuda.is_available():
            app_cfg.NVIDIA_GPU_NUMS = torch.cuda.device_count()
            logger.debug(f'可用 NVIDIA 显卡数: {app_cfg.NVIDIA_GPU_NUMS}')
    except Exception:
        pass

    app_cfg.VULKAN_LIST=get_vulkan_devices()
    return

# 用于 faster-whisper /openai-whisper 的设备名， cpu/cuda/mps
# 如果明确指定了设备名如 cuda/mps 且可用，则返回该名，否则优先cuda/mps，保底cpu
def whisper_device(device:str=None,is_cuda:bool=False,allow_mps=False):
    device=device or settings.get('device_name','auto') or 'auto'
    prefix=device.split(":")[0].lower()

    if not is_cuda or prefix not in ['auto','cuda','mps','metal','vulkan']:
        return "cpu"

    if prefix=='cuda' and app_cfg.NVIDIA_GPU_NUMS>0:return device
    if allow_mps and app_cfg.MPS_NUMS>0 and prefix in ['mps','metal']:return "mps"

    if app_cfg.NVIDIA_GPU_NUMS>0: return "cuda"
    if allow_mps and app_cfg.MPS_NUMS>0: return "mps"
    return "cpu"


# 用于 transfomers 推理，返回 auto/cpu/cuda/mps
# 如果明确指定了设备名如 cuda/cpu/mps 且可用，则返回该名，否则优先cuda/mps，保底 auto
def transformers_device(device:str=None,is_cuda:bool=False):
    device=device or settings.get('device_name','auto') or 'auto'
    prefix=device.split(":")[0].lower()
    if not is_cuda or prefix not in ['cuda','mps','metal','auto','vulkan']:
        return 'cpu'

    if prefix in ['cuda','vulkan'] and app_cfg.NVIDIA_GPU_NUMS>0:
        return device if prefix=='cuda' else 'cuda'
    if prefix in ['mps','metal'] and app_cfg.MPS_NUMS>0:
        return "mps"

    return "auto"

# 用于 audio.cpp 和 llamp.cpp whisper.cpp
# return cuda/best/cpu/vulkan
# 如果明确指定了设备名如 cuda/cpu/metal/vulkan 且可用，则返回该名，否则优先cuda/metal，其次vulkan，保底 best
def cpp_device(device:str=None,is_cuda:bool=False):
    device=device or settings.get('device_name','auto') or 'auto'
    prefix=device.split(":")[0].lower()
    if not is_cuda or prefix not in ['auto','cuda','mps','metal','vulkan','best']:
        return 'cpu'

    if prefix=='cuda' and app_cfg.NVIDIA_GPU_NUMS>0:
        return device
    if prefix=='vulkan' and app_cfg.VULKAN_LIST:
        return device
    if prefix in ['mps','metal'] and app_cfg.MPS_NUMS>0:
        return "metal"
    return 'best'


def exists_hard():
    return app_cfg.NVIDIA_GPU_NUMS > 0 or app_cfg.MPS_NUMS>0 or app_cfg.VULKAN_LIST