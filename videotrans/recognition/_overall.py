import threading
import time, json, shutil
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from dataclasses import dataclass
from videotrans.configure import config

from videotrans.recognition._base import BaseRecogn

import requests
from videotrans.util import tools
from huggingface_hub import snapshot_download
from pydub import AudioSegment
from videotrans.process import openai_whisper, faster_whisper

"""
faster-whisper
内置的本地大模型不重试
"""
_MODELS= {
    "tiny.en": "Systran/faster-whisper-tiny.en",
    "tiny": "Systran/faster-whisper-tiny",
    "base.en": "Systran/faster-whisper-base.en",
    "base": "Systran/faster-whisper-base",
    "small.en": "Systran/faster-whisper-small.en",
    "small": "Systran/faster-whisper-small",
    "medium.en": "Systran/faster-whisper-medium.en",
    "medium": "Systran/faster-whisper-medium",
    "large-v1": "Systran/faster-whisper-large-v1",
    "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3",
    "large": "Systran/faster-whisper-large-v3",
    "distil-large-v2": "Systran/faster-distil-whisper-large-v2",
    "distil-medium.en": "Systran/faster-distil-whisper-medium.en",
    "distil-small.en": "Systran/faster-distil-whisper-small.en",
    "distil-large-v3": "Systran/faster-distil-whisper-large-v3",
    "distil-large-v3.5": "distil-whisper/distil-large-v3.5-ct2",
    "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    "turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
}


@dataclass
class FasterAll(BaseRecogn):
    def __post_init__(self):
        super().__post_init__()
        local_dir = f'{config.ROOT_DIR}/models/models--'
        if self.model_name in _MODELS:
            local_dir += _MODELS[self.model_name].replace('/', '--')
        else:
            local_dir += self.model_name.replace('/', '--')
        self.local_dir = local_dir
        self.audio_duration=len(AudioSegment.from_wav(self.audio_file))
        # 切分
        if int(config.settings.get('batch_size', 8))>1:
            self._vad_split()

    def _exec(self):
        if self._exit():
            return
        self.error = ''
        self._signal(text="STT starting, hold on...")
        if self.recogn_type == 1:  # openai-whisper
            raws = self._openai()
        else:
            raws = self._faster()
        return raws

    def _openai(self):
        # 起一个进程
        logs_file = f'{config.TEMP_DIR}/{self.uuid}/openai-{self.detect_language}-{time.time()}.log'
        kwars = {
            "prompt": config.settings.get(
                f'initial_prompt_{self.detect_language}') if self.detect_language != 'auto' else None,
            "detect_language": self.detect_language,
            "model_name": self.model_name,
            "ROOT_DIR": config.ROOT_DIR,
            "logs_file": logs_file,
            "defaulelang": config.defaulelang,
            "is_cuda": self.is_cuda,
            "no_speech_threshold": float(config.settings.get('no_speech_threshold', 0.5)),
            "condition_on_previous_text": config.settings.get('condition_on_previous_text', False),
            "speech_timestamps": self.speech_timestamps,
            "audio_file": self.audio_file,
            "TEMP_ROOT": config.TEMP_ROOT,
            "jianfan": self.jianfan,
            "batch_size":int(config.settings.get('batch_size', 8)),
            "audio_duration":self.audio_duration
        }
        threading.Thread(target=self._process, args=(logs_file,), daemon=True).start()
        raws = []
        with ProcessPoolExecutor(max_workers=1) as executor:
            # 提交任务，并显式传入参数，确保子进程拿到正确的参数
            future = executor.submit(
                openai_whisper,
                **kwars
            )
            # .result() 会阻塞当前线程直到子进程计算完毕，并返回结果
            raws = future.result()
        if isinstance(raws, str):
            raise RuntimeError(raws)
        return raws

    # 获取进度
    def _process(self, logs_file):
        last_mtime = 0
        while 1:
            _p = Path(logs_file)
            if _p.is_file() and _p.stat().st_mtime != last_mtime:
                last_mtime = _p.stat().st_mtime
                _tmp = json.loads(_p.read_text(encoding='utf-8'))
                self._signal(text=_tmp.get('text'), type=_tmp.get('type', 'logs'))
                if _tmp.get('type', '') == 'error':
                    return
            time.sleep(0.5)

    def _faster(self):
        self._signal(text=f"load {self.model_name}")
        

        logs_file = f'{config.TEMP_DIR}/{self.uuid}/faster-{self.detect_language}-{time.time()}.log'
        kwars = {
            "prompt": config.settings.get(
                f'initial_prompt_{self.detect_language}') if self.detect_language != 'auto' else None,
            "detect_language": self.detect_language,
            "model_name": self.model_name,
            "ROOT_DIR": config.ROOT_DIR,
            "logs_file": logs_file,
            "defaulelang": config.defaulelang,
            "is_cuda": self.is_cuda,
            "no_speech_threshold": float(config.settings.get('no_speech_threshold', 0.5)),
            "condition_on_previous_text": config.settings.get('condition_on_previous_text', False),
            "speech_timestamps": self.speech_timestamps,
            "audio_file": self.audio_file,
            "TEMP_ROOT": config.TEMP_ROOT,
            "local_dir": self.local_dir,
            "compute_type": config.settings.get('cuda_com_type', 'default'),
            "batch_size": int(config.settings.get('batch_size', 8)),
            "beam_size": int(config.settings.get('beam_size', 5)),
            "best_of": int(config.settings.get('best_of', 5)),
            "jianfan": self.jianfan,
            "audio_duration":self.audio_duration
        }
        # 获取进度
        threading.Thread(target=self._process, args=(logs_file,), daemon=True).start()
        raws = []
        with ProcessPoolExecutor(max_workers=1) as executor:
            # 提交任务，并显式传入参数，确保子进程拿到正确的参数
            future = executor.submit(
                faster_whisper,
                **kwars
            )
            # .result() 会阻塞当前线程直到子进程计算完毕，并返回结果
            raws = future.result()
        if isinstance(raws, str):
            raise RuntimeError(raws)
        return raws

    # 在下载默认模型 large-v3-turbo时，针对国内无法连接huggingface.co，且镜像站不稳定的情况，使用 modelscope.cn替换
    def _faster_turbo_from_modelscope(self, local_dir):
        print('阿里镜像下载')
        urls = [
            'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/config.json',
            'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/preprocessor_config.json',
            'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/tokenizer.json',
            'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/vocabulary.json',
            'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/model.bin',
        ]
        self._signal(text=f"downloading large-v3-turbo from modelscope.cn")
        for index, url in enumerate(urls):
            filename = os.path.basename(url)
            print(filename)
            self._signal(text=f"start downloading {index + 1}/5 from modelscope.cn")
            with requests.get(url, stream=True, timeout=60) as response:
                response.raise_for_status()

                total_length = response.headers.get('content-length')
                dest_file_obj = open(f'{local_dir}/{filename}', 'wb')
                try:
                    if total_length is None:
                        dest_file_obj.write(response.content)
                    else:
                        total_length = int(total_length)
                        downloaded = 0
                        last_send = time.time()
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                dest_file_obj.write(chunk)
                                downloaded += len(chunk)
                                file_percent = min((downloaded / total_length) * 100, 100)
                                if time.time() - last_send > 3:
                                    last_send = time.time()
                                    self._signal(text=f"downloading {index + 1}/5 {file_percent:.2f}%")
                finally:
                    dest_file_obj.close()
            self._signal(text=f"end downloading {index + 1}/5 from modelscope.cn")
        return local_dir

    def _progress_callback(self, data):
        msg_type = data.get("type")
        percent = data.get("percent")
        filename = data.get("filename")

        if msg_type == "file":

            # 标签显示当前文件名
            self._signal(text=f"{filename} {percent:.2f}%")

        else:
            # === 情况 B：这是总文件计数 (Fetching 4 files) ===
            # 不要更新进度条！否则会由 100% 突然跳回 25%
            # 建议只在某个副标签显示总进度，或者干脆忽略
            current_file_idx = data.get("current")
            total_files = data.get("total")

            self._signal(text=f"{current_file_idx}/{total_files} files")

    # 下载模型，首先测试 huggingface.co 连通性，不可用则回退镜像 hf-mirror.com
    def _get_modeldir_download(self):
        if self.recogn_type == 1: return

        self._signal(text="Checking if the model exists")
        if self.model_name in _MODELS:
            repo_id = _MODELS[self.model_name]
        else:
            repo_id = self.model_name

        Path(self.local_dir).mkdir(exist_ok=True, parents=True)
        # 已存在
        is_file = False
        if [it for it in Path(self.local_dir).glob('*.bin')] or [it for it in
                                                                 Path(self.local_dir).glob('*.safetensors')]:
            is_file = True
        if is_file:
            self._signal(text="The model already exists.")
            return True

        try:
            requests.head('https://huggingface.co', timeout=5)
        except Exception:
            print(f'无法连接 huggingface.co, 使用镜像替换: hf-mirror.com, {self.model_name=}')
            endpoint = 'https://hf-mirror.com'
            if self.model_name in ['large-v3-turbo', 'turbo']:
                try:
                    # 针对 large-v3-turbo 模型使用 modelscope.cn 下载
                    return self._faster_turbo_from_modelscope(self.local_dir)
                except Exception as e:
                    print(f'阿里镜像下载 失败:{e}')
                    # 失败继续使用镜像尝试
        else:
            print('可以使用 huggingface.co')
            endpoint = 'https://huggingface.co'

        # 不存在，判断缓存中是否存在
        # 用于兼容处理旧版本模型目录
        rs = self._is_model_cached(self.model_name, f"{config.ROOT_DIR}/models")
        if isinstance(rs, str) and Path(rs).exists():
            # 移动
            for item in Path(rs).iterdir():
                if item.is_dir():
                    continue
                try:
                    shutil.move(str(item), self.local_dir)
                    print(f"Moved: {item.name}")
                except shutil.Error as e:
                    print(f"{e}")
            try:
                shutil.rmtree(f'{self.local_dir}/blobs')
                shutil.rmtree(f'{self.local_dir}/refs')
                shutil.rmtree(f'{self.local_dir}/snapshots')
            except:
                pass
            self._signal(text="The model already exists.")
            return True
        # 不存在，需要下载
        self._signal(text=f"Downloading the model from {endpoint} ...")
        try:
            MyTqdmClass = tools.create_tqdm_class(self._progress_callback)
            snapshot_download(
                repo_id=repo_id,
                local_dir=self.local_dir,
                local_dir_use_symlinks=False,
                endpoint=endpoint,
                etag_timeout=5,
                tqdm_class=MyTqdmClass,
                ignore_patterns=["*.msgpack", "*.h5", ".git*", "*.md"]
            )
            self._signal(text="Downloaded end")
        except Exception as e:
            msg = f'下载模型失败，你可以打开以下网址，将 .bin/.txt/.json 文件下载到\n {self.local_dir} 文件夹内\n' if config.defaulelang == 'zh' else f'The model download failed. You can try opening the following URL and downloading the .bin/.txt/.json files to the {self.local_dir} folder.'
            raise RuntimeError(f'{msg}\n[https://huggingface.co/{repo_id}/tree/main]\n{e}')
        else:
            junk_paths = [
                ".cache",
                "blobs",
                "refs",
                "snapshots",
                ".no_exist"
            ]

            for junk in junk_paths:
                full_path = Path(self.local_dir) / junk
                if full_path.exists():
                    try:
                        if full_path.is_dir():
                            shutil.rmtree(full_path)
                        else:
                            os.remove(full_path)
                        print(f"clear cache: {junk}")
                    except Exception as e:
                        print(f"{junk} {e}")
            return True

    def _is_model_cached(self, repo_id: str, cache_dir: str = ''):
        try:
            # 将 repo_id 转换为缓存目录的命名格式
            if repo_id in _MODELS:
                org_name, model_name = _MODELS[repo_id].split('/')
                repo_cache_dir = Path(cache_dir) / f"models--{org_name}--{model_name}"
            else:
                repo_cache_dir = Path(cache_dir) / f"models--" / repo_id.replace('/', '--')

            # 检查是否存在 refs/main 文件以获取当前版本的哈希值
            refs_main_file = repo_cache_dir / "refs" / "main"
            if not refs_main_file.exists():
                return False

            with open(refs_main_file, 'r') as f:
                target_hash = f.read().strip()

            # 检查对应的 snapshots 目录
            snapshot_dir = repo_cache_dir / "snapshots" / target_hash
            if not snapshot_dir.exists():
                return False

            # 检查关键文件：config.json 和 model.bin
            for it in ["config.json", "model.bin", "tokenizer.json", "vocabulary"]:
                if it == 'vocabulary':
                    if not self._is_file_valid(snapshot_dir / 'vocabulary.txt') and not self._is_file_valid(
                            snapshot_dir / 'vocabulary.json'):
                        return False
                    continue
                if not self._is_file_valid(snapshot_dir / it):
                    return False
            return str(snapshot_dir)
        except Exception:
            return False

    def _is_file_valid(self, file_path) -> bool:
        try:
            if not file_path.exists():
                return False

            # 如果是符号链接，获取真实路径
            if file_path.is_symlink():
                real_path = file_path.resolve()
                # 确保解析后的路径仍然存在
                if not real_path.exists():
                    return False
                file_path = real_path

            # 检查文件大小
            return file_path.stat().st_size > 0

        except (OSError, ValueError):
            return False
