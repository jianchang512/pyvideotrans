import gc
import platform
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Optional
from pathlib import Path
from videotrans.configure.config import logger, settings, ROOT_DIR
from videotrans.configure.constants import HYMT2_GGUF_HF
from videotrans.translator._base import BaseTrans
from videotrans.util.gpus import should_use_vulkan, get_vulkan_device_index, resolve_torch_device
import torch


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@dataclass
class HYOBJ:
    hymt2_tokenizer: Any = None
    hymt2_model: Any = None
    server_proc: Optional[subprocess.Popen] = None
    server_url: str = ""
    use_vulkan: bool = False


@dataclass(repr=False)
class HYMT2(BaseTrans):
    hy: Any = None

    def __post_init__(self):
        super().__post_init__()
        self.local_dir = f'{ROOT_DIR}/models/models--tencent--Hy-MT2-1.8B'
        self.hy = HYOBJ()

    def _download(self):
        from videotrans.util.help_down import (
            check_and_down_hf,
            check_and_down_ms,
            down_file_from_hf,
            down_llamacpp_bin,
        )
        from videotrans.util.help_misc import is_connect_hf

        if should_use_vulkan(is_cuda=self.is_cuda):
            if down_llamacpp_bin(process_callback=self._process_callback):
                gguf_file = Path(f"{self.local_dir}/Hy-MT2-1.8B-Q8_0.gguf")
                if not gguf_file.exists():
                    down_file_from_hf(
                        self.local_dir,
                        [HYMT2_GGUF_HF],
                        self._process_callback,
                    )
                vk_idx = get_vulkan_device_index()
                port = _get_free_port()
                srv_bin = "llama-server.exe" if platform.system() == "Windows" else "llama-server"
                srv_path = f"{ROOT_DIR}/llama_cpp/{srv_bin}"
                cmd = [
                    srv_path,
                    "-m",
                    str(gguf_file),
                    "--device",
                    f"Vulkan{vk_idx}",
                    "-ngl",
                    "99",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "-c",
                    "16384",
                ]
                logger.debug(f"HY-MT2 starting llama-server on Vulkan{vk_idx}: {cmd=}")
                self.hy.server_proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                    cwd=f"{ROOT_DIR}/llama_cpp",
                )
                self.hy.server_url = f"http://127.0.0.1:{port}"
                self.hy.use_vulkan = True
                import requests
                for _ in range(60):
                    if self.hy.server_proc.poll() is not None:
                        raise RuntimeError(f"HY-MT2 llama-server exited early with code {self.hy.server_proc.returncode}")
                    try:
                        r = requests.get(f"{self.hy.server_url}/health", timeout=1)
                        if r.status_code == 200:
                            logger.debug(f"HY-MT2: running on Vulkan{vk_idx} via llama-server ({self.hy.server_url})")
                            return True
                    except Exception:
                        pass
                    time.sleep(0.5)
                raise RuntimeError("HY-MT2 llama-server failed to become healthy within 30s")

        if is_connect_hf():
            check_and_down_hf(
                "Hy-MT2-1.8B",
                'tencent/Hy-MT2-1.8B',
                self.local_dir,
                callback=self._process_callback)
        else:
            check_and_down_ms(
                'Tencent-Hunyuan/Hy-MT2-1.8B',
                local_dir=self.local_dir,
                callback=self._process_callback)

        from transformers import AutoModelForCausalLM, AutoTokenizer

        # Load tokenizer
        self.hy.hymt2_tokenizer = AutoTokenizer.from_pretrained(self.local_dir, trust_remote_code=True)

        # Load model
        device = resolve_torch_device(settings.get('device_name', 'auto'), is_cuda=self.is_cuda)
        self.hy.hymt2_model = AutoModelForCausalLM.from_pretrained(
            self.local_dir,
            device_map=device,
            dtype='auto',
            trust_remote_code=True,
        )
        logger.debug(f'HY2-MT:running on {self.hy.hymt2_model.device}')
        self.hy.hymt2_model.eval()
        return True

    def _item_task(self, data: str) -> str:
        if self._exit(): return
        text = data

        prompt = Path(f'{ROOT_DIR}/videotrans/prompts/text/hymt.txt').read_text(encoding="utf-8").replace("{lang}", self.target_code).replace('{batch_input}', text)

        if self.hy and self.hy.use_vulkan and self.hy.server_url:
            import requests
            resp = requests.post(
                f"{self.hy.server_url}/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 8092,
                    "temperature": 0.1,
                },
                timeout=300,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

        messages = [{"role": "user", "content": prompt}]
        inputs = self.hy.hymt2_tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to(
            self.hy.hymt2_model.device)

        with torch.no_grad():
            outputs = self.hy.hymt2_model.generate(
                **inputs,
                max_new_tokens=8092,
            )
        response = self.hy.hymt2_tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
        return response.strip()

    def _unload(self):
        try:
            if self.hy and self.hy.server_proc is not None:
                try:
                    self.hy.server_proc.terminate()
                    self.hy.server_proc.wait(timeout=5)
                except Exception:
                    try:
                        self.hy.server_proc.kill()
                    except Exception:
                        pass
                self.hy.server_proc = None
            if self.hy:
                self.hy.hymt2_model = None
                self.hy.hymt2_tokenizer = None
            self.hy = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except BaseException:
            pass
