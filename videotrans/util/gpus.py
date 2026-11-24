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
import shutil
import subprocess
from typing import Dict, List, Any
from pathlib import Path
from videotrans.configure.config import app_cfg, logger, settings,ROOT_DIR
import traceback
from PySide6.QtCore import QThread, Signal
from videotrans.configure import config

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


def get_vulkan_devices() -> List[Dict[str, Any]]:
    """Return list of available non-CPU Vulkan compute devices in ggml_vulkan order."""
    if _os=='Darwin' or not shutil.which("vulkaninfo"):
        logger.warning('无可用 vulkan 设备')
        return []
    devices: List[Dict[str, Any]] = []
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
                })
                idx += 1
        logger.debug(f'检测到 Vulkan 可用信息:{devices}')
    except Exception as e:
        logger.error(f"vulkaninfo check failed: {e}")
    return devices



def check_hardware_availability():
    app_cfg.NVIDIA_CUDA_NUMS=0
    app_cfg.MPS_NUMS=0
    if _os == 'Darwin':
        app_cfg.AUDIOCPP_REAL_CUDA=False
        app_cfg.AUDIOCPP_REAL_VULKAN=False
        try:
            import torch
            app_cfg.MPS_NUMS = 1 if torch.backends.mps.is_built() and torch.backends.mps.is_available() else 0
            logger.debug(f'Darwin: {app_cfg.MPS_NUMS=}')
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
            if app_cfg.NVIDIA_COUNT>0:
                import torch
                app_cfg.NVIDIA_CUDA_NUMS=torch.cuda.device_count() if torch.cuda.is_available() else 0
            logger.debug(f'检测到可用 NVIDIA CUDA 核: {app_cfg.NVIDIA_CUDA_NUMS}')
        except Exception:
            pass

        app_cfg.VULKAN_LIST=get_vulkan_devices()
    # 准备硬件选择数据用于高级选项
    devices=["auto"]
    if config.app_cfg.NVIDIA_CUDA_NUMS>0:
        devices.append("cuda")
        if config.app_cfg.NVIDIA_CUDA_NUMS>1:
            for i in range(config.app_cfg.NVIDIA_CUDA_NUMS):
                devices.append(f"cuda:{i}")
    if config.app_cfg.VULKAN_LIST:
        for it in config.app_cfg.VULKAN_LIST:
            devices.append(f"vulkan:{it['index']}")
    if config.app_cfg.MPS_NUMS:
        devices.append("mps")

    devices.append("cpu")
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

    if _os!='Darwin':
        app_cfg.AUDIOCPP_REAL_METAL=False
    else:
        app_cfg.AUDIOCPP_REAL_METAL=is_support(backend="metal") is True
    return app_cfg.AUDIOCPP_REAL_METAL


def get_audiobin(name="server"):
    audio_bin=f'{ROOT_DIR}/audio_cpp/audiocpp_{name}'
    if _os=='Windows':
        audio_bin=f'{audio_bin}.exe'
    if not Path(audio_bin).exists():
        # Darwin Linux 允许使用 环境中 audiocpp
        if _os=='Windows' or (not shutil.which('audiocpp_cli') and shutil.which('audiocpp_server')):
            raise FileNotFoundError(f'No File: {audio_bin}')
        audio_bin=f"audiocpp_{name}"
    return audio_bin

# 判断 audiocpp_server 是否真的支持 cuda/vulkan, 虽然有n卡、cuda存在、能检测到vulkan设备，但未必能被audiocpp_server识别到，因此需判断
def is_support(backend="vulkan"):
    try:
        """
        like 
        {"schema_version":1,"devices":[{"backend":"cuda","registry":"CUDA","index":0,"name":"CUDA0","description":"Tesla T4","type":"gpu","pci_bus_id":"0000:00:04.0","memory":{"free_bytes":15527116800,"total_bytes":15637086208},"caps":{"async":true,"host_buffer":true,"buffer_from_host_ptr":false,"events":true}},{"backend":"cpu","registry":"CPU","index":0,"name":"CPU","description":"Intel(R) Xeon(R) CPU @ 2.00GHz","type":"cpu","pci_bus_id":null,"memory":{"free_bytes":11799359488,"total_bytes":13605818368},"caps":{"async":false,"host_buffer":false,"buffer_from_host_ptr":true,"events":false}}]}


        """
        proc = subprocess.run(
            [get_audiobin(), "--list-devices", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="ignore",
        )
        if proc.returncode!=0:
            logger.error(f'检测 audio.cpp 支持的 [{backend}] 硬件设备时出错:{proc.returncode=},{proc.stderr=},{proc.stdout=}')
            return proc.returncode
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if not line.startswith("{") or '"devices"' not in line:
                continue
            data = json.loads(line)
            for d in data.get("devices", []):
                if d.get("backend") == backend:
                    return True
    except Exception as e:
        logger.error(f"audiocpp_cli --list-devices failed: {e}")
    return False

# 是否存在 cuda mps vulkan 任意可用硬件
def exists_hard():
    return app_cfg.NVIDIA_COUNT >0 or app_cfg.NVIDIA_CUDA_NUMS > 0  or app_cfg.MPS_NUMS>0 or app_cfg.VULKAN_LIST

def _format_device(device=None):
    device=device or settings.get('device_name','auto') or 'auto'
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
