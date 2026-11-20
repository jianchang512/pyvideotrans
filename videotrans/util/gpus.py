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
    if app_cfg.VULKAN_LIST:
        return app_cfg.VULKAN_LIST

    devices: List[Dict[str, Any]] = []

    # 1. Try audio.cpp --list-devices --json if available (exact ggml_vulkan indices + VRAM)
    # Windows audio.cpp cuda12.4 & audio.cpp-vulkan
    # audiocpp_bin_list = [
    #     Path(ROOT_DIR) / "audio_cpp" / "audiocpp_cli.exe",
    #     Path(ROOT_DIR) / "audio_cpp_vulkan" / "audiocpp_cli.exe"
    # ] if platform.system() == "Windows" else [ Path(ROOT_DIR) / "audio_cpp" / "audiocpp_cli" ]
    # for audiocpp_bin in audiocpp_bin_list:
    #     if audiocpp_bin.is_file():
    #         try:
    #             proc = subprocess.run(
    #                 [str(audiocpp_bin), "--list-devices", "--json"],
    #                 capture_output=True,
    #                 text=True,
    #                 timeout=10,
    #                 encoding="utf-8",
    #                 errors="ignore",
    #             )
    #             for line in (proc.stdout or "").splitlines():
    #                 line = line.strip()
    #                 if line.startswith("{") and '"devices"' in line:
    #                     data = json.loads(line)
    #                     for d in data.get("devices", []):
    #                         if d.get("backend") == "vulkan":
    #                             devices.append(d)
    #                     break
    #         except Exception as e:
    #             logger.debug(f"audiocpp_cli --list-devices failed: {e}")

    # 2. Fallback: check _pywhispercpp system_info or vulkaninfo
    # if not devices:
        # try:
        #     import _pywhispercpp as pw  # type: ignore
        #     info = pw.whisper_print_system_info() or ""
        #     # Check if libggml-vulkan is linked/loaded or vulkaninfo sees GPUs
        #     if "Vulkan" in info or Path(pw.__file__).parent.joinpath("libggml-vulkan.so.0").exists():
        #         pass
        # except Exception:
        #     pass

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
    app_cfg.VULKAN_LIST=devices
    return devices

#
# def is_vulkan_available() -> bool:
#     """Return True if at least one Vulkan GPU is available."""
#     return len(app_cfg.VULKAN_LIST) > 0
#

#
# def get_vulkan_device_index(device_name: Optional[str] = None) -> int:
#     """Resolve the ggml_vulkan GPU index from device_name ('vulkan:1', 'auto', etc.)."""
#     if device_name is None:
#         device_name = str(settings.get("device_name", "auto") or "auto")
#     device_name = str(device_name).strip().lower().split()[0]
#
#     if ":" in device_name:
#         try:
#             return int(device_name.split(":", 1)[1])
#         except ValueError:
#             pass
#
#     env_idx = os.environ.get("VULKAN_DEVICE_INDEX")
#     if env_idx is not None and env_idx.isdigit():
#         return int(env_idx)
#
#     devices = get_vulkan_devices()
#     if len(devices) > 1:
#         # Prefer the Vulkan GPU with the largest total memory (e.g. Strix Halo 103GB APU over smaller dGPU)
#         best = max(
#             devices,
#             key=lambda d: int((d.get("memory") or {}).get("total_bytes") or 0),
#         )
#         return int(best.get("index", 0))
#     return 0
#
# # 废弃
# def get_device_choices() -> List[tuple[str, str]]:
#     """Return (display_label, value) pairs for the UI Compute Device selector."""
#     choices: List[tuple[str, str]] = [(f"auto", "auto")]
#     if platform.system() == 'Darwin':
#         # Macos M Metal or mps
#         choices.extend([
#             ("metal", "metal"),
#             ("mps", "mps"),
#         ])
#     elif torch.cuda.is_available():
#         choices.extend([
#             ("cuda", "cuda"),
#             ("cuda:0", "cuda:0"),
#             ("cuda:1", "cuda:1")
#         ])
#     vk_devs = get_vulkan_devices()
#     if vk_devs:
#         best_idx = get_vulkan_device_index("auto")
#         best_desc = next((d.get("description") for d in vk_devs if int(d.get("index", 0)) == best_idx), f"Vulkan{best_idx}")
#         choices.append((f"vulkan (Auto -> Vulkan{best_idx}: {best_desc})", "vulkan"))
#         for d in vk_devs:
#             idx = int(d.get("index", 0))
#             desc = d.get("description") or f"Vulkan{idx}"
#             mem_gb = int((d.get("memory") or {}).get("total_bytes") or 0) / (1024 ** 3)
#             mem_str = f" [{mem_gb:.1f} GB]" if mem_gb > 0 else ""
#             choices.append((f"vulkan:{idx} ({desc}{mem_str})", f"vulkan:{idx}"))
#
#
#     return choices


# 获取可用的gpu数量 并缓存在 config.NVIDIA_GPU_NUMS 中，0=无可用显卡
#
# force_cpu: 未使用参数
#   True 强制使用 cpu 即强制设定没有显卡
def getset_gpu(force_cpu=False):
    if force_cpu:
        return
    # 尚未获取过时是 -1
    if app_cfg.NVIDIA_GPU_NUMS > -1:
        return

    app_cfg.NVIDIA_GPU_NUMS=0
    app_cfg.MPS_NUMS=0
    import torch
    if platform.system() == 'Darwin':
        app_cfg.MPS_NUMS = 1 if torch.backends.mps.is_built() and torch.backends.mps.is_available() else 0
        logger.debug(f'MPS可用？{app_cfg.MPS_NUMS=}')
        return

    try:
        if torch.cuda.is_available():
            app_cfg.NVIDIA_GPU_NUMS = torch.cuda.device_count()
            logger.debug(f'可用 NVIDIA 显卡数: {app_cfg.NVIDIA_GPU_NUMS}')
    except Exception:
        pass

    get_vulkan_devices()
    return True

# 用于 faster-whisper /openai-whisper 的设备名， cpu/cuda
# 如果 allow_mps=True,且 app_cfg.MPS_NUMS>0则返回 mps
def whisper_device(device:str=None,is_cuda:bool=False,allow_mps=False):
    device=device or settings.get('device_name','auto')
    if is_cuda and app_cfg.NVIDIA_GPU_NUMS>0:
        return device if device and device.startswith('cuda') else "cuda"
    if allow_mps and app_cfg.MPS_NUMS>0:
        return "mps"
    return "cpu"


# 用于 transfomers 推理，返回 auto/cpu/cuda/mps
def transformers_device(device:str=None,is_cuda:bool=False):
    device=device or settings.get('device_name','auto')
    if device in ['metal'] or device.startswith('vulkan'):return 'auto'

    if is_cuda and app_cfg.NVIDIA_GPU_NUMS>0:
        return device if device.startswith('cuda') else "cuda"

    return "auto"

# 用于 audio.cpp 和 llamp.cpp whisper.cpp
# return cuda/best/cpu/vulkan
def cpp_device(device:str=None,is_cuda:bool=False):
    if not is_cuda:return "cpu"
    device=device or settings.get('device_name','auto')
    is_start_vulkan=device and device.startswith('vulkan')
    is_start_cuda=device and device.startswith('cuda')
    if not is_start_cuda and not is_start_vulkan and device not in ['cpu','best','auto','metal']:
        return 'cpu'
    if app_cfg.NVIDIA_GPU_NUMS>0:
        return device if is_start_cuda else 'cuda'
    if app_cfg.VULKAN_LIST:
        return device if is_start_vulkan else 'vulkan'
    if app_cfg.MPS_NUMS>0:
        return "metal"
    return 'cpu'


def exists_hard():
    return app_cfg.NVIDIA_GPU_NUMS > 0 or app_cfg.MPS_NUMS>0 or app_cfg.VULKAN_LIST