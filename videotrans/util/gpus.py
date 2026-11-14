# 1. 获取并缓存可用 gpu 数量 (CUDA + Vulkan)
# 2. 获取可用 cuda / vulkan 号
# 3. MacOSX 是否支持 mps
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

from videotrans.configure.config import app_cfg, logger, ROOT_DIR, settings

_VULKAN_DEVICES_CACHE: Optional[List[Dict[str, Any]]] = None

_CUDA_ACTIVATE=False

def get_vulkan_devices() -> List[Dict[str, Any]]:
    """Return list of available non-CPU Vulkan compute devices in ggml_vulkan order."""
    global _VULKAN_DEVICES_CACHE
    if _VULKAN_DEVICES_CACHE is not None:
        return _VULKAN_DEVICES_CACHE

    devices: List[Dict[str, Any]] = []

    # 1. Try audio.cpp --list-devices --json if available (exact ggml_vulkan indices + VRAM)
    audiocpp_bin = Path(ROOT_DIR) / "audio_cpp" / ("audiocpp_cli.exe" if platform.system() == "Windows" else "audiocpp_cli")
    if audiocpp_bin.is_file():
        try:
            proc = subprocess.run(
                [str(audiocpp_bin), "--list-devices", "--json"],
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
                        if d.get("backend") == "vulkan":
                            devices.append(d)
                    break
        except Exception as e:
            logger.debug(f"audiocpp_cli --list-devices failed: {e}")

    # 2. Fallback: check _pywhispercpp system_info or vulkaninfo
    if not devices:
        try:
            import _pywhispercpp as pw  # type: ignore
            info = pw.whisper_print_system_info() or ""
            # Check if libggml-vulkan is linked/loaded or vulkaninfo sees GPUs
            if "Vulkan" in info or Path(pw.__file__).parent.joinpath("libggml-vulkan.so.0").exists():
                pass
        except Exception:
            pass

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
            except Exception as e:
                logger.debug(f"vulkaninfo check failed: {e}")

    _VULKAN_DEVICES_CACHE = devices
    return devices


def is_vulkan_available() -> bool:
    """Return True if at least one Vulkan GPU is available."""
    return len(get_vulkan_devices()) > 0


def should_use_vulkan(device_name: Optional[str] = None, is_cuda: bool = True) -> bool:
    """Return True if inference should use the Vulkan compute backend."""
    if device_name is None:
        device_name = str(settings.get("device_name", "auto") or "auto")
    dev = str(device_name).strip().lower().split()[0]
    if dev in ("cpu", "mps") or dev.startswith("cuda"):
        return False
    if dev.startswith("vulkan"):
        return is_vulkan_available()
    if dev == "auto":
        return bool(is_cuda) and is_vulkan_available()
    return False


def resolve_torch_device(device_name: Optional[str] = None, is_cuda: bool = True) -> str:
    """Resolve a PyTorch/CTranslate2 device string without ever mapping 'vulkan*' to 'cuda'."""
    if device_name is None:
        device_name = str(settings.get("device_name", "auto") or "auto")
    dev = str(device_name).strip().lower().split()[0]
    if not is_cuda or dev == "cpu" or dev.startswith("vulkan"):
        return "cpu"
    if dev == "auto":
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return mps_or_cpu()
    return dev


def get_vulkan_device_index(device_name: Optional[str] = None) -> int:
    """Resolve the ggml_vulkan GPU index from device_name ('vulkan:1', 'auto', etc.)."""
    if device_name is None:
        device_name = str(settings.get("device_name", "auto") or "auto")
    device_name = str(device_name).strip().lower().split()[0]

    if ":" in device_name:
        try:
            return int(device_name.split(":", 1)[1])
        except ValueError:
            pass

    env_idx = os.environ.get("VULKAN_DEVICE_INDEX")
    if env_idx is not None and env_idx.isdigit():
        return int(env_idx)

    devices = get_vulkan_devices()
    if len(devices) > 1:
        # Prefer the Vulkan GPU with the largest total memory (e.g. Strix Halo 103GB APU over smaller dGPU)
        best = max(
            devices,
            key=lambda d: int((d.get("memory") or {}).get("total_bytes") or 0),
        )
        return int(best.get("index", 0))
    return 0


def get_device_choices() -> List[tuple[str, str]]:
    """Return (display_label, value) pairs for the UI Compute Device selector."""
    vk_devs = get_vulkan_devices()
    if not vk_devs and Path(f'{ROOT_DIR}/videotrans/devices.json').exists():
        try:
            vk_devs=json.loads(Path(f'{ROOT_DIR}/videotrans/devices.json').read_text(encoding="utf-8"))
        except (json.JSONDecodeError,Exception) as e:
            logger.exception(f'获取加速器缓存失败:{e}',exc_info=True)
    elif vk_devs:
        Path(f'{ROOT_DIR}/videotrans/devices.json').write_text(json.dumps(vk_devs,ensure_ascii=False),encoding="utf-8")
    choices: List[tuple[str, str]] = []
    if vk_devs:
        best_idx = get_vulkan_device_index("auto")
        best_desc = next((d.get("description") for d in vk_devs if int(d.get("index", 0)) == best_idx), f"Vulkan{best_idx}")
        choices.append((f"auto (Vulkan{best_idx}: {best_desc})", "auto"))
        choices.append((f"vulkan (Auto -> Vulkan{best_idx}: {best_desc})", "vulkan"))
        for d in vk_devs:
            idx = int(d.get("index", 0))
            desc = d.get("description") or f"Vulkan{idx}"
            mem_gb = int((d.get("memory") or {}).get("total_bytes") or 0) / (1024 ** 3)
            mem_str = f" [{mem_gb:.1f} GB]" if mem_gb > 0 else ""
            choices.append((f"vulkan:{idx} ({desc}{mem_str})", f"vulkan:{idx}"))
    else:
        choices.append(("auto", "auto"))
        choices.append(("vulkan", "vulkan"))
    if _CUDA_ACTIVATE>0:#真实存在可用cuda
        choices.extend([
            ("cuda", "cuda"),
            ("cuda:0", "cuda:0"),
            ("cuda:1", "cuda:1")
        ])
    if platform.system() == 'Darwin':
        choices.extend([
            ("mps", "mps"),
        ])
    return choices


def get_audiocpp_backend_args(device_name: Optional[str] = None) -> List[str]:
    """Return ['--backend', '<backend>', ...] arguments for audio.cpp CLI."""
    if device_name is None:
        device_name = str(settings.get("device_name", "auto") or "auto")
    device_name = str(device_name).strip().lower()

    if device_name == "cpu":
        return ["--backend", "cpu"]

    if device_name.startswith("vulkan") or (device_name == "auto" and is_vulkan_available()):
        idx = get_vulkan_device_index(device_name)
        return ["--backend", "vulkan", "--device", str(idx)]

    if device_name.startswith("cuda"):
        args = ["--backend", "cuda"]
        if ":" in device_name:
            args.extend(["--device", device_name.split(":", 1)[1]])
        return args

    return ["--backend", "best"]


# 获取可用的gpu数量 并缓存在 config.NVIDIA_GPU_NUMS 中，0=无可用显卡
#
# force_cpu: 未使用参数
#   True 强制使用 cpu 即强制设定没有显卡
def getset_gpu(force_cpu=False) -> int:
    global _CUDA_ACTIVATE
    if force_cpu:
        return 0
    # 尚未获取过时是 -1
    if app_cfg.NVIDIA_GPU_NUMS > -1:
        return app_cfg.NVIDIA_GPU_NUMS

    if platform.system() == 'Darwin':
        app_cfg.NVIDIA_GPU_NUMS = 0
        return 0

    gpu_nums = 0
    try:
        import torch
        if torch.cuda.is_available():
            _CUDA_ACTIVATE=True
            gpu_nums = torch.cuda.device_count()
    except Exception:
        pass

    if gpu_nums == 0:
        vk_devs = get_vulkan_devices()
        gpu_nums = len(vk_devs)
        if gpu_nums > 0:
            logger.debug(f'可用 Vulkan 显卡数: {gpu_nums} ({[d.get("description") for d in vk_devs]})')

    app_cfg.NVIDIA_GPU_NUMS = gpu_nums
    logger.debug(f'可用 GPU 显卡数 (CUDA/Vulkan): {app_cfg.NVIDIA_GPU_NUMS}')
    return app_cfg.NVIDIA_GPU_NUMS


# MacOSX 判断是否支持 mps
# mps: 支持
# cpu: 不支持，必须使用 cpu
def mps_or_cpu() -> str:
    if platform.system() != 'Darwin':
        return 'cpu'
    import torch
    if torch.backends.mps.is_built() and torch.backends.mps.is_available():
        return 'mps'
    return 'cpu'
