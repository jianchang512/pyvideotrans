import shutil

from videotrans.configure._i18n import tr
from videotrans.configure._paths import IPC_STATUS_FILE
from videotrans.configure.config import app_cfg, CPU_NUMS

import json
import os
import platform
import random
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from videotrans import logger
from videotrans.configure import config
from videotrans.configure._paths import ROOT_DIR
from videotrans.configure.constants import AUDIOCPP_ASR_MODELS
from videotrans.util.help_role import get_audiocpp_rolelist


_os = platform.system()
_IS_WINDOWS = _os == "Windows"

# 只有"需要重启"的线程会拿到这把锁；健康时所有线程走快路径直接返回。
_START_LOCK = threading.Lock()

# /health 探测超时。2s 。
_HEALTH_TIMEOUT = 2


def _port_is_free(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def _pick_port(retries: int = 20) -> int:
    for _ in range(retries):
        port = random.randint(8899, 10500)
        if _port_is_free(port):
            return port
    raise RuntimeError("未能在 8899-10500 范围内找到空闲端口，请检查系统端口占用")


def _read_tail(path: Optional[Path], limit: int = 2000) -> str:
    if not path:
        return ""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - limit))
            return f.read().decode(errors="ignore")
    except Exception:
        return ""


@dataclass
class Audio_Server:
    proc: Any = None
    port: int = 0
    api_endpoint: Optional[str] = None
    status: bool = False
    cfg_file: Optional[str] = None
    model_cfg: Dict = field(default_factory=dict)

    # 内部状态
    _device:str=None
    _log_fp: Any = field(default=None, repr=False)
    _log_path: Optional[Path] = field(default=None, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # ---------------- 探测----------------
    def is_activate(self) -> bool:
        """
        纯读探测，不修改任何状态、不杀进程，可被任意线程并发调用。
        失败时只返回 False，由 start() 负责清理与重启。
        """
        if not self.api_endpoint:
            return False
        # 快判：进程已经退出，无需 HTTP 探测
        if self.proc is None or self.proc.poll() is not None:
            logger.debug("[Audio.cpp] 进程不存在或已退出，需要重启")
            return False
        try:
            r = requests.get(f"{self.api_endpoint}/health", timeout=_HEALTH_TIMEOUT)
            if r.status_code == 200:
                logger.debug(f"[Audio.cpp]: running on {self._device}  {self.api_endpoint}")
                return True
            logger.debug(f"[Audio.cpp] /health 返回 {r.status_code}")
        except requests.RequestException as e:
            logger.debug(f"[Audio.cpp] /health 探测失败: {e}")
        return False

    # ---------------- 幂等停止 ----------------
    def quit(self) -> None:
        """幂等、线程安全、永不抛异常。"""
        with self._lock:
            proc, self.proc = self.proc, None
            self.status = False
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.warning(f"[Audio.cpp] terminate 超时，强制 kill pid={proc.pid}")
                        proc.kill()
                        proc.wait(timeout=5)
                except Exception as e:
                    logger.warning(f"[Audio.cpp] 停止进程异常: {e}")

            if self._log_fp:
                try:
                    self._log_fp.close()
                except Exception:
                    pass
                self._log_fp = None


    def _create_cfg(self) -> None:
        from videotrans.util.gpus import cpp_device
        device = cpp_device(is_cuda=True)
        device_index = 0
        if ":" in device:
            device, device_index = device.split(":", 1)

        cfg = {
            "host": "127.0.0.1",
            "port": self.port,
            "backend": device,
            "device": int(device_index) if str(device_index).isnumeric() else 0,
            "threads": int(min(max(1, CPU_NUMS), 8)),
            "lazy_load": True,
            "idle_unload_ms": 120000,
            "max_loaded_models": 1,
            "models": [],
        }
        self._device=f'{cfg["backend"]}:{cfg["device"]}'
        logger.debug(f'[Audio.cpp server]:{cfg=}')

        data = get_audiocpp_rolelist() | AUDIOCPP_ASR_MODELS
        for name, it in data.items():
            model = {
                "id": name,
                "family": name,
                "task": it.get("type", "asr"),
                "path": f'{ROOT_DIR}/models/{it["file"]}',
                "mode": "offline",
                "default_request_options": {},
            }
            if model["task"] in ("tts", "clon"):
                if it.get("is_seed"):
                    model["default_request_options"] = {"seed": 42}

                model["default_voice_preset"] = {
                    "voice_ref": f'{ROOT_DIR}/f5-tts/en_female_1.wav',
                    "reference_text": "Genes of intracellular calcium metabolism and blood pressure control in primary hypertension.",
                }
            elif model["task"] == "asr":
                if "audio_chunk_mode" in it:
                    model["default_request_options"]["audio_chunk_mode"] = it.get("audio_chunk_mode")
                if "max_tokens" in it:
                    model["default_request_options"]["max_tokens"] = int(it.get("max_tokens"))
            cfg["models"].append(model)

        self.model_cfg = cfg
        cfg_path = Path(config.TEMP_ROOT) / f"audioserver-{self.port}.json"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
        self.cfg_file = str(cfg_path)

    # ---------------- 就绪等待 ----------------
    def _wait_ready(self, timeout: float = 30.0, interval: float = 0.5) -> bool:
        deadline = time.monotonic() + timeout
        attempt = 0
        while time.monotonic() < deadline:
            attempt += 1
            # 子进程提前退出 → 立即失败
            if self.proc and self.proc.poll() is not None:
                raise RuntimeError(
                    f"Audio.cpp 进程异常退出 (code={self.proc.returncode})\n"
                    f"日志: {self._log_path}\n--- 日志尾部 ---\n{_read_tail(self._log_path)}"
                )
            try:
                r = requests.get(f"{self.api_endpoint}/health", timeout=2)
                if r.status_code == 200:
                    logger.debug(f"Audio.cpp 启动成功[第{attempt}次探测] {self.api_endpoint}")
                    return True
            except requests.RequestException:
                pass
            time.sleep(interval)
        return False

    # ---------------- 启动（非线程安全，由外层 _START_LOCK 保护） ----------------
    def start(self) -> bool:
        if self.is_activate():
            return True
        from videotrans.util.gpus import get_audiobin
        exe = get_audiobin(name="server")
        exe_parent=f'{ROOT_DIR}/audio_cpp' if exe!="audiocpp_server" else ROOT_DIR

        # 清理上一次可能残留的进程/句柄（restart 情形）
        self.quit()

        self.port = _pick_port()
        self.api_endpoint = f"http://127.0.0.1:{self.port}"
        self._create_cfg()

        cmd = [str(exe), "--no-ui", "--config", self.cfg_file]
        logger.debug(f"启动 Audio.cpp server... cmd={cmd}")

        log_path = Path(config.TEMP_ROOT) / f"audioserver-{self.port}.log"
        self._log_path = log_path
        self._log_fp = open(log_path, "wb")

        kwargs: Dict[str, Any] = {}
        if _IS_WINDOWS:
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        try:
            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=self._log_fp,
                stderr=subprocess.STDOUT,
                cwd=str(exe_parent),
                **kwargs,
            )
            if self._wait_ready():
                self.status = True
                return True
        except Exception:
            self.quit()
            raise

        self.quit()
        raise RuntimeError(
            f"Audio.cpp 启动超时 (cmd={cmd})\n"
            f"日志: {log_path}\n--- 日志尾部 ---\n{_read_tail(log_path)}"
        )


def activate_audiocpp_server(trk=None) -> bool:
    """
    业务线程唯一入口：
    - 服务健康：快速返回 True（不拿锁、不重启）。
    - 服务不在/已死/探测失败：拿锁、幂等创建、重启。
    - 启动失败：抛异常，业务侧 try/except。
    """
    srv: Optional[Audio_Server] = getattr(config, "AUDIO_SERVER_CFG", None)

    # 健康直接返回
    if srv is not None and srv.is_activate():
        return True

    # 串行化"创建 + 重启"
    if trk and hasattr(trk,'signal'):
        trk.signal(text="Starting Audio.cpp server...")
    with _START_LOCK:
        srv = getattr(config, "AUDIO_SERVER_CFG", None)
        if srv is None:
            srv = Audio_Server()
            config.AUDIO_SERVER_CFG = srv

        # 可能在上一个持锁线程里已经恢复
        if srv.is_activate():
            return True

        srv.start()
    if trk and hasattr(trk,'signal'):
        trk.signal(text="Start Audio.cpp server succeed...")
    logger.debug(f"Audio.cpp 已就绪[{srv._device}]: api={srv.api_endpoint}")
    return True


# 下载 audiocpp
# 1. windows首选cuda，若存在n卡或不存在vulkan设备，则下载cuda版本。 其他下载vulkan版本，检测vulkan版本是否--list-device可用，若报错，仍重新下载cuda版
# 2. linux上仅下载 Vulkan 版本
# 3. macos仅下载 arm64版本
def download_audiocpp_check(callback=None):
    from videotrans.configure.constants import AUDIO_CPP_MAC_HF,AUDIO_CPP_LINUX_VULKAN_HF,AUDIO_CPP_WIN_VULKAN_HF,AUDIO_CPP_WIN_HF
    from videotrans.util.help_down import down_zip
    ext=".exe" if _os=='Windows' else ''
    p=Path(f'{ROOT_DIR}/audio_cpp/audiocpp_server{ext}')
    if p.exists():return

    # Darwin Linux 允许使用 环境变量中的 audio.cpp 作为后备
    if _os in ['Darwin','Linux']:
        if shutil.which("audiocpp_cli") and shutil.which("audiocpp_server"):
            return
        down_zip(str(p.parent), AUDIO_CPP_MAC_HF if _os=='Darwin' else AUDIO_CPP_LINUX_VULKAN_HF, callback=callback)
        return


    # 不存在n卡 但是 存在vulkan设备，下载vulkan版本，下载后需检测，若无法运行，需再次下载cuda版本
    if app_cfg.NVIDIA_COUNT==0 and app_cfg.VULKAN_LIST:
        down_zip(str(p.parent),AUDIO_CPP_WIN_VULKAN_HF,callback=callback)
        # 判断是否可运行
        from videotrans.util.gpus import is_support
        if p.exists() and is_support(backend="vulkan") in [True,False]:
            return
        try:
            # 不可用
            app_cfg.AUDIOCPP_REAL_VULKAN=False
            shutil.rmtree(str(p.parent),ignore_errors=True)
        except OSError:
            pass
    #其他情况，或 vulkan 无法运行时，重新下载 cuda 版本
    down_zip(str(p.parent),AUDIO_CPP_WIN_HF,callback=callback)
    return

# No retry for failures. When the acceleration fails due to the audio.cpp and Vulkan versions on Windows, fallback to CPU still has a high probability of failure
def exec_audiocpp(cmd):
    from videotrans.util.gpus import get_audiobin
    cmd[0]=get_audiobin(name="cli")
    if "--threads" not in cmd:
        cmd.extend(["--threads", str(min(8,max(CPU_NUMS, 1))) ])
    logger.debug(f'audio.cpp start: {cmd=}')
    rc, stdout, stderr, aborted = _run_audiocpp_proc(cmd)
    if aborted:
        return True

    if rc != 0:
        logger.error(f'audio.cpp 执行失败:{stdout=},{stderr=},{cmd=}')
        if "Access is denied" in f"{stdout}{stderr}" or "could not open" in f"{stdout}{stderr}":
            raise RuntimeError('audio.cpp '+tr('Insufficient permissions'))
        if "mem_buffer" in f"{stdout}{stderr}":
            raise RuntimeError(tr('OOMerror'))

        if "no gguf model source in builtin model spec for family" in f'{stdout}{stderr}':
            raise RuntimeError(tr("You may need to upgrade audio.cpp. Please delete the {} folder, then re-execute the automatic download of the latest audio.cpp, or manually update audio_cpp",cmd[0]))

        raise RuntimeError(
            f'proc.returncode={rc},{stderr=}\n{stdout=}\n{cmd=}'
        )
    return True


# cli 命令行用于执行 人声背景分离、降噪 等操作
def _run_audiocpp_proc(cmd):
    # 可能用户自行编译或将 audiocpp_cli 加入了环境变量，可全局使用
    cwd= ROOT_DIR if cmd[0] in ["audiocpp_cli","audiocpp_server"] else f"{ROOT_DIR}/audio_cpp"

    proc = subprocess.Popen(
        cmd,
        encoding="utf-8",
        errors='ignore',
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if _os == 'Windows' else 0,
        cwd=cwd,
    )
    while True:
        try:
            stdout, stderr = proc.communicate(timeout=0.1)
            return proc.returncode, stdout, stderr, False
        except subprocess.TimeoutExpired:
            if app_cfg.exit_soft or Path(IPC_STATUS_FILE).exists():
                proc.kill()
                proc.communicate()
                return 0, "", "", True

