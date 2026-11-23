# 1. 获取并缓存可用 gpu 数量 (CUDA + Vulkan)
import json
import platform
import shutil
import subprocess
from typing import Dict, List, Any
from pathlib import Path
from videotrans.configure.config import app_cfg, logger, settings,ROOT_DIR
import traceback
from PySide6.QtCore import QThread, Signal
from videotrans.configure import config

_os=platform.system()


class AiLoaderThread(QThread):
    gpu_io = Signal(str)

    def run(self):
        try:
            getset_gpu()
            devices=["auto"]
            if config.app_cfg.NVIDIA_GPU_NUMS>0:
                devices.append("cuda")
                if config.app_cfg.NVIDIA_GPU_NUMS>1:
                    for i in range(config.app_cfg.NVIDIA_GPU_NUMS):
                        devices.append(f"cuda:{i}")
            if config.app_cfg.VULKAN_LIST:
                for it in config.app_cfg.VULKAN_LIST:
                    devices.append(f"vulkan:{it['index']}")
            if config.app_cfg.MPS_NUMS:
                devices.append("mps")
                devices.append("metal")
            devices.append("cpu")
            config.ACCESS_DEVICES=devices
            self.gpu_io.emit("end")
        except Exception as e:
            err = traceback.format_exc()
            self.gpu_io.emit(f'{e},{err}')


def get_vulkan_devices() -> List[Dict[str, Any]]:
    """Return list of available non-CPU Vulkan compute devices in ggml_vulkan order."""
    if _os=='Darwin':return []
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
    if _os == 'Darwin':
        app_cfg.AUDIOCPP_REAL_CUDA=False
        app_cfg.AUDIOCPP_REAL_VULKAN=False
        try:
            import torch
            app_cfg.MPS_NUMS = 1 if torch.backends.mps.is_built() and torch.backends.mps.is_available() else 0
            logger.debug(f'MPS可用？{app_cfg.MPS_NUMS=}')
        except Exception:
            pass
        return

    try:
        if subprocess.run(["nvidia-smi"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,).returncode != 0:
            app_cfg.NVIDIA_GPU_NUMS=0
            app_cfg.AUDIOCPP_REAL_CUDA=False
        else:
            import torch
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

    if app_cfg.NVIDIA_GPU_NUMS>0:
        return device if prefix=='cuda' else 'cuda'

    if allow_mps and app_cfg.MPS_NUMS>0:
        return "mps"

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

    if real_cuda_exists():
        return device if prefix=='cuda' else 'cuda'

    if real_vulkan_exists():
        return device if prefix=='vulkan' else 'vulkan'

    if real_metal_exists():
        return "metal"

    return 'cpu'


# 在 实际使用 audio.cpp + vulkan 执行之前，需再次通过 audio.cpp --list-devices 判断是否真实存在可用的vulkan，vulkaninfo 可检测到，但实际可能因为驱动老旧、缺失库文件，而无法加速

def real_vulkan_exists():
    # mac或 vulkaninfo 不可用
    if app_cfg.AUDIOCPP_REAL_VULKAN is not None:
        return app_cfg.AUDIOCPP_REAL_VULKAN

    if _os=='Darwin' or not app_cfg.VULKAN_LIST:
        app_cfg.AUDIOCPP_REAL_VULKAN=False


    app_cfg.AUDIOCPP_REAL_VULKAN=_is_support(backend="vulkan")
    return app_cfg.AUDIOCPP_REAL_VULKAN


# 仅 windows 版本支持cuda，linux使用vulkan，macos使用metal
def real_cuda_exists():
    if app_cfg.AUDIOCPP_REAL_CUDA is not None:
        return app_cfg.AUDIOCPP_REAL_CUDA

    if _os=='Darwin' or not shutil.which("nvidia-smi"):
        app_cfg.AUDIOCPP_REAL_CUDA=False
    else:
        app_cfg.AUDIOCPP_REAL_CUDA=_is_support(backend="cuda")
    return app_cfg.AUDIOCPP_REAL_CUDA

def real_metal_exists():
    if app_cfg.AUDIOCPP_REAL_METAL is not None:
        return app_cfg.AUDIOCPP_REAL_METAL

    if _os!='Darwin':
        app_cfg.AUDIOCPP_REAL_METAL=False
    else:
        app_cfg.AUDIOCPP_REAL_METAL=_is_support(backend="metal")
    return app_cfg.AUDIOCPP_REAL_METAL

# 可能 audiocpp_cli 不存在 但 audiocpp_server 存在
def _get_audio_bin(is_vulkan=False):
    cli_name='audiocpp_cli.exe' if _os=='Windows' else 'audiocpp_cli'
    server_name='audiocpp_server.exe' if _os=='Windows' else 'audiocpp_server'
    # windows下 vulkan 默认放在 audio_cpp_vulkan 文件夹内
    if is_vulkan and _os=='Windows' and Path(f'{ROOT_DIR}/audio_cpp_vulkan/{cli_name}').exists():
        audio_cli_file=f'{ROOT_DIR}/audio_cpp_vulkan/{cli_name}'
        audio_server_file=f'{ROOT_DIR}/audio_cpp_vulkan/{server_name}'
    else:
        audio_cli_file=f'{ROOT_DIR}/audio_cpp/{cli_name}'
        audio_server_file=f'{ROOT_DIR}/audio_cpp/{server_name}'


    if not Path(audio_cli_file).exists():
        if Path(audio_server_file).exists():
            return audio_server_file

        if shutil.which('audiocpp_cli'):
            return "audiocpp_cli"
        if shutil.which('audiocpp_server'):
            return "audiocpp_server"
    return False

def _is_support(backend="vulkan"):
    audio_cli_file=_get_audio_bin(is_vulkan=backend=="vulkan")
    if not audio_cli_file:
        return False
    try:
        proc = subprocess.run(
            [audio_cli_file, "--list-devices", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="ignore",
        )
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if line.startswith("{") and '"devices"' in line:
                data = json.loads(line)
                for d in data.get("devices", []):
                    if d.get("backend") == backend:
                        return True
                return False
    except Exception as e:
        logger.debug(f"audiocpp_cli --list-devices failed: {e}")
    return False

# 是否存在 cuda mps vulkan 任意可用硬件
def exists_hard():
    return app_cfg.NVIDIA_GPU_NUMS > 0 or app_cfg.MPS_NUMS>0 or app_cfg.VULKAN_LIST