import tempfile
import time
from pathlib import Path
import shutil, os
import zipfile
from videotrans.configure.config import ROOT_DIR, tr, logger, defaulelang,app_cfg
from videotrans.configure.contants import FASTER_MODELS_DICT
from urllib.parse import urlparse
import threading
import tqdm

# 全局锁对象防止同时下载模型，避免文件冲突或限流
download_lock = threading.Lock()

"""解析URL获取纯净文件名 (去除 ?query)"""
def get_filename_from_url(url) -> str:
    parsed = urlparse(url)
    return os.path.basename(parsed.path)


# 用于判断某个目录内是否存在指定类型的文件，存在则视为已存在
def file_exists(dirname, glob_patter='*.bin') -> bool:
    if isinstance(glob_patter, str):
        glob_patter = [glob_patter]
    for pat in glob_patter:
        for it in Path(dirname).glob(pat):
            return True
    return False



"""
若无法连接 huggingface.co
    针对 faster-whisper 系列模型， 使用 modelscope.cn 下载[https://modelscope.cn/collections/himyworld/faster-whisper]，速度更快，其他模型使用国内镜像 https://hf-mirror.com 下载(慢易报错429)
    
若可连接 huggingface.co ，则始终使用
"""

_original_http_get=None
def check_and_down_hf(model_id, repo_id, local_dir, callback=None, allow_list=None) -> bool:
    global _original_http_get
    from .help_misc import is_connect_hf
    if model_id in FASTER_MODELS_DICT and is_connect_hf() is False:
        logger.debug(f'从 modelscope.cn 下载模型 {model_id=}')
        return check_and_down_ms(FASTER_MODELS_DICT[
                                     model_id] if model_id != 'distil-large-v3.5' else 'iBoostAI/distil-whisper-distil-large-v3.5-ct2',
                                 callback=callback, local_dir=local_dir)

    import huggingface_hub.file_download as hf_fd
    if not _original_http_get:
        # ── 补丁 http_get: 注入 _ChunkTracker 绕过 tqdm ──
        _original_http_get = hf_fd.http_get
    import huggingface_hub
    from huggingface_hub.errors import LocalEntryNotFoundError

    _state = {"completed": 0, "total_files": 0}
    # ── 总进度 ──
    class QtAwareTqdm(tqdm.tqdm):
        def update(self, n=1):
            super().update(n)
            if not callback or not self.total or self.total <= 0:
                return
            _state["completed"] += n
            if _state["total_files"] == 0:
                _state["total_files"] = int(self.total)
            callback({"type": "batch", "current": int(self.n), "total": int(self.total)})



    def _patched_http_get(url, temp_file, *,
                          proxies=None, resume_size=0, headers=None,
                          expected_size=None, displayed_filename=None,
                          _nb_retries=5, _tqdm_bar=None):
        if expected_size is None:
            return _original_http_get(url, temp_file, proxies=proxies,
                                      resume_size=resume_size, headers=headers,
                                      expected_size=expected_size,
                                      displayed_filename=displayed_filename,
                                      _nb_retries=_nb_retries, _tqdm_bar=_tqdm_bar)

        class _ChunkTracker:
            def __init__(self):
                self.downloaded = resume_size

            def update(self, n):
                self.downloaded += n
                if callback:
                    pct = min(self.downloaded / expected_size * 100, 99.9)
                    name = displayed_filename or url.rsplit('/', 1)[-1].split('?')[0]
                    # 综合进度
                    completed = _state.get("completed", 0)
                    total = _state.get("total_files", 0)
                    # 单文件进度
                    callback({"type": "file", "percent": pct,
                              "filename": f'[{completed + 1}/{total}](hf) {name}' if total > 0 else name})
                    if total > 0:
                        smooth = (completed + pct / 100) / total * 100
                        callback({
                            "type": "batch",
                            "current": completed + 1,
                            "total": total,
                            "percent": min(smooth, 99.9),
                        })

        return _original_http_get(url, temp_file, proxies=proxies,
                                  resume_size=resume_size, headers=headers,
                                  expected_size=expected_size,
                                  displayed_filename=displayed_filename,
                                  _nb_retries=_nb_retries,
                                  _tqdm_bar=_ChunkTracker())

    hf_fd.http_get = _patched_http_get

    try:

        try:
            huggingface_hub.snapshot_download(
                repo_id=repo_id,
                local_dir=local_dir,
                etag_timeout=5,
                local_files_only=True
            )
        except LocalEntryNotFoundError:
            Path(local_dir).mkdir(exist_ok=True, parents=True)
            is_connect_hf()
            # 线程锁，避免同时多个下载或其他线程也在下载
            if callback:
                callback(' wait get download lock...')
            with download_lock:
                if callback:
                    callback('starting downloading...')
                logger.debug(f'获取到下载锁，开始从 hf下载 {repo_id}')
                huggingface_hub.snapshot_download(
                    repo_id=repo_id,
                    local_dir=local_dir,
                    local_dir_use_symlinks=False,
                    endpoint=os.environ.get('HF_ENDPOINT'),
                    etag_timeout=10,
                    tqdm_class=QtAwareTqdm if callback else None,
                    local_files_only=False,
                    max_workers=1,
                    ignore_patterns=["*.msgpack", "*.h5", ".git*", "*.md"],
                    allow_patterns=allow_list
                )

        junk_paths = [
            ".cache",
            "blobs",
            "refs",
            "snapshots",
            ".no_exist"
        ]

        for junk in junk_paths:
            full_path = Path(local_dir) / junk
            if full_path.exists():
                try:
                    if full_path.is_dir():
                        shutil.rmtree(full_path)
                    else:
                        os.remove(full_path)
                except OSError as e:
                    logger.exception(f"清理临时文件失败：{junk} {e}", exc_info=True)
    except Exception as e:
        msg = f'下载模型失败，你可以打开以下网址，将所有文件下载到\n {local_dir} 文件夹内\n' if defaulelang == 'zh' else f'The model download failed. You can try opening the following URL and downloading all files to the {local_dir} folder.'
        from videotrans.configure.excepts import DownloadModelsError
        raise DownloadModelsError(f'{msg}\n[https://huggingface.co/{repo_id}/tree/main]\n{e}')
    finally:
        hf_fd.http_get = _original_http_get
    return True


# 从 huggingface.co 下载单个文件
def down_file_from_hf(local_dir, urls=None, callback=None) -> bool:
    from .help_misc import is_connect_hf
    is_connect_hf()
    import requests
    endpoint = os.environ.get('HF_ENDPOINT')
    for index, url in enumerate(urls):
        try:
            if not url.startswith('https://'):
                url = f'{endpoint}{url}'
            filename = get_filename_from_url(url)
            with requests.get(f'{url}', stream=True, timeout=(30, 600)) as response:
                response.raise_for_status()
                total_length = response.headers.get('content-length')

                dest_file_obj = open(f'{local_dir}/{filename}', 'wb')

                try:
                    if total_length is None:
                        dest_file_obj.write(response.content)
                    else:
                        total_length = max(int(total_length), 1)
                        downloaded = 0
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                dest_file_obj.write(chunk)
                                downloaded += len(chunk)

                                # 计算进度
                                # 单文件进度 0-100
                                file_percent = (downloaded / total_length)
                                if callback:
                                    callback(f'{filename}:{file_percent * 100:.2f}%')
                finally:
                    dest_file_obj.close()  # 关闭实体文件句柄
        except Exception as e:
            from videotrans.configure.excepts import DownloadModelsError
            raise DownloadModelsError(
                tr("downloading all files", local_dir) + f'\n[https://huggingface.co{url}]\n\n{e}')
    return True


# 从 modelscope.cn 下载单个文件
def down_file_from_ms(local_dir, urls=None, callback=None) -> bool:
    Path(local_dir).mkdir(parents=True, exist_ok=True)
    import requests
    for index, url in enumerate(urls):
        filename = get_filename_from_url(url)
        file_abso_path = f'{local_dir}/{filename}'
        if Path(file_abso_path).exists():
            continue
        with requests.get(url, stream=True, timeout=(30, 600)) as response:
            response.raise_for_status()
            total_length = response.headers.get('content-length')
            dest_file_obj = open(file_abso_path, 'wb')
            try:
                if total_length is None:
                    dest_file_obj.write(response.content)
                else:
                    total_length = max(int(total_length), 1)
                    downloaded = 0
                    last_send = time.time()
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            dest_file_obj.write(chunk)
                            downloaded += len(chunk)
                            file_percent = min((downloaded / total_length) * 100, 100)
                            if time.time() - last_send > 3:
                                last_send = time.time()
                            if callback:
                                callback(
                                    {"type": "file", "percent": file_percent, "filename": f"{filename}",
                                     "current": index + 1, "total": 5})

            finally:
                dest_file_obj.close()
    return True


# 从 modelscope.cn下载zip并解压 到指定目录
def down_zip(local_dir, zip_url, callback=None) -> bool:
    import requests
    try:
        filename = get_filename_from_url(zip_url)
        with requests.get(zip_url, stream=True, timeout=(30, 600)) as response:
            response.raise_for_status()
            total_length = response.headers.get('content-length')

            # 决定写入目标：如果是需要解压的，写入临时文件；否则直接写入目标文件
            dest_file_obj = tempfile.TemporaryFile()  # 内存/临时磁盘，自动删除
            try:
                if total_length is None:
                    dest_file_obj.write(response.content)
                else:
                    total_length = max(int(total_length), 1)
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            dest_file_obj.write(chunk)
                            downloaded += len(chunk)

                            # 计算进度
                            # 单文件进度 0-100
                            file_percent = min(99.0, downloaded * 100 / total_length)
                            if callback:
                                callback(f'{tr("Download Models")} {filename} {file_percent:.2f}%')
                if callback:
                    callback(f'Extracting zip...')
                dest_file_obj.seek(0)  # 回到文件头
                with zipfile.ZipFile(dest_file_obj) as zf:
                    zf.extractall(path=local_dir)
                if callback:
                    callback('Downloaded end')
            finally:
                dest_file_obj.close()
    except Exception as e:
        msg = tr('model is missing. Please download it', local_dir)
        if callback:
            callback(f'Error:{msg}')
        from videotrans.configure.excepts import DownloadModelsError
        raise DownloadModelsError(f"{msg}\n[{zip_url}]\n{e}")
    return True


# 从 modelscope.cn 下载完整模型
# 优先加载本地模型，失败则在线下载
_orig_download_file_lists=None
def check_and_down_ms(model_id, callback=None, local_dir=None) -> bool:
    global _orig_download_file_lists
    import modelscope.hub.snapshot_download as ms_sd
    if not _orig_download_file_lists:
        _orig_download_file_lists = ms_sd._download_file_lists
    from modelscope.hub.callback import TqdmCallback
    from modelscope.hub.snapshot_download import snapshot_download

    _state = {"completed": 0, "total_files": 0}


    def _patched_dfl(repo_files, *args, **kwargs):
        # 简单统计非 tree 条目数
        _state["total_files"] = sum(1 for f in repo_files if f.get('Type') != 'tree')
        return _orig_download_file_lists(repo_files, *args, **kwargs)

    ms_sd._download_file_lists = _patched_dfl

    # 回调类：追踪字节，不依赖 str(tqdm)
    class Pro(TqdmCallback):
        def __init__(self, *args):
            super().__init__(*args)
            self._downloaded = 0

        def update(self, size):
            super().update(size)
            self._downloaded += size
            if not callback:
                return
            try:
                pct = min(self._downloaded / max(self.file_size, 1) * 100, 99.9)
                # 格式: "[已下载数/总数] 文件名 进度%"
                callback(
                    f"[{_state['completed'] + 1}/"
                    f"{max(_state['total_files'], 1)}](ms) "
                    f"{self.filename} {pct:.1f}%"
                )
            except Exception:
                pass

        def end(self):
            _state["completed"] += 1
            super().end()



    try:
        try:
            # 如果本地加载失败，则在线下载
            snapshot_download(model_id=model_id, local_files_only=True, progress_callbacks=[Pro], local_dir=local_dir)
            if callback:
                callback(f'{model_id} exists')
        except ValueError:
            # 线程锁，避免同时多个下载或其他线程也在下载
            if callback:
                callback('wait get download lock...')
            with download_lock:
                if callback:
                    callback('starting downloading...')
                logger.debug(f'获取到下载锁，开始从 ms 下载 {model_id}')
            snapshot_download(model_id=model_id, progress_callbacks=[Pro], local_dir=local_dir)
        else:
            return True
    except Exception as e:
        local_dir = f'{ROOT_DIR}/models/models/{model_id}/' if not local_dir else local_dir
        msg = f'下载模型失败，你可以打开以下网址，将所有文件下载到\n {local_dir} 文件夹内\n' if defaulelang == 'zh' else f'The model download failed. You can try opening the following URL and downloading all files to the {local_dir} folder.'
        from videotrans.configure.excepts import DownloadModelsError
        raise DownloadModelsError(f'{msg}\n[https://modelscope.cn/models/{model_id}/tree/main]\n{e}')
    finally:
        ms_sd._download_file_lists = _orig_download_file_lists
    return True
