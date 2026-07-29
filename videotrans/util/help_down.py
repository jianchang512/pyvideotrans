import time
from pathlib import Path
import shutil, os
import zipfile
from videotrans.configure.config import  tr, logger,  app_cfg
from videotrans.configure.contants import FASTER_MODELS_DICT
from urllib.parse import urlparse
import threading
import tqdm
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
_original_http_get = None


def check_and_down_hf(model_id, repo_id, local_dir, callback=None, allow_list=None,token=None) -> bool:
    Path(local_dir).mkdir(exist_ok=True, parents=True)
    global _original_http_get
    from .help_misc import is_connect_hf
    ishf = is_connect_hf()
    if model_id and model_id in FASTER_MODELS_DICT and not ishf:
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
                          _nb_retries=5, _tqdm_bar=None, **kwargs):
        if expected_size is None:
            return _original_http_get(url, temp_file, proxies=proxies,
                                      resume_size=resume_size, headers=headers,
                                      expected_size=expected_size,
                                      displayed_filename=displayed_filename,
                                      _nb_retries=_nb_retries, _tqdm_bar=_tqdm_bar, **kwargs)

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
                local_files_only=True
            )
        except LocalEntryNotFoundError:

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
                    # local_dir_use_symlinks=False,
                    endpoint=os.environ.get('HF_ENDPOINT'),
                    tqdm_class=QtAwareTqdm if callback else None,
                    local_files_only=False,
                    # max_workers=1,
                    ignore_patterns=["*.msgpack", "*.h5", ".git*", "*.md"],
                    token=token,
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
        from videotrans.configure.excepts import DownloadModelsError
        raise DownloadModelsError(tr("download model error"))
    finally:
        hf_fd.http_get = _original_http_get
    return True


# 非 https开头的，则必须以 / 开头，根据是否可访问自动添加 huggingface.co或 hf-mirror.com
# 如果是 http开头，则直接使用
def down_file_from_hf(local_dir, urls=None, callback=None) -> bool:
    Path(local_dir).mkdir(parents=True, exist_ok=True)
    max_retries = 10
    from .help_misc import is_connect_hf
    from videotrans.configure.excepts import DownloadModelsError
    import requests
    endpoint = None
    # 复用底层 TCP 连接
    session = requests.Session()
    proxy = {"https": app_cfg.proxy} if app_cfg.proxy else None

    for index, url in enumerate(urls):
        try:
            filename = get_filename_from_url(url)
        except NameError:
            filename = url.split('/')[-1]  # fallback
            if '?' in filename:
                filename = filename.split('?')[0]

        final_file_path = Path(f'{local_dir}/{filename}')
        temp_file_path = Path(f'{local_dir}/{filename}.downloading')

        # 如果正式文件存在且有大小，说明之前已经 100% 成功下载过
        if final_file_path.exists() and final_file_path.stat().st_size > 0:
            if callback:
                callback(f'{filename}:100.00%')
            continue

        if not url.startswith('https://'):
            if not endpoint:
                is_connect_hf()
                endpoint = os.environ.get('HF_ENDPOINT')
            url = f'{endpoint}{url}'

        logger.debug(f'开始下载[{filename}]: {url}')

        retries = 0
        while retries < max_retries:
            try:
                headers = {}
                downloaded_size = 0

                # 检查临时文件是否存在以及已下载的大小
                if temp_file_path.exists():
                    downloaded_size = temp_file_path.stat().st_size
                    if downloaded_size > 0:
                        headers['Range'] = f'bytes={downloaded_size}-'

                if 'modelscope.cn' in url:
                    proxy = None
                with session.get(url, headers=headers, stream=True, timeout=(15, 30), verify=False,
                                 proxies=proxy) as response:
                    # 如果不是 200 (OK) 也不是 206 则抛出异常触发重试
                    if response.status_code not in (200, 206):
                        response.raise_for_status()

                    # 根据状态码自适应判断源站是否支持断点续传
                    if response.status_code == 206:
                        mode = 'ab'  # 追加
                        remaining_length = response.headers.get('content-length')
                        total_length = (downloaded_size + int(remaining_length)) if remaining_length else None
                    else:
                        mode = 'wb'  # 不覆盖
                        downloaded_size = 0
                        total_length = response.headers.get('content-length')
                        total_length = int(total_length) if total_length else None

                    with open(temp_file_path, mode) as dest_file_obj:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                dest_file_obj.write(chunk)
                                downloaded_size += len(chunk)
                                if callback:
                                    if total_length:
                                        file_percent = (downloaded_size / total_length) * 100
                                        callback(f'{filename}:{file_percent:.2f}%')
                                    else:
                                        # 源站无 content-length ，退化为显示已下载的数据量
                                        mb_size = downloaded_size / (1024 * 1024)
                                        callback(f'{filename}:{mb_size:.1f}MB')

                    # 确保下载没有中途悄悄结束
                    if total_length is not None and downloaded_size < total_length:
                        raise ConnectionError(f"文件截断：预期 {total_length} 字节，仅收到 {downloaded_size} 字节")

                    # 使用 replace 跨平台覆盖
                    temp_file_path.replace(final_file_path)
                    logger.debug(f'下载完成 {filename}')
                    break
            except Exception as e:
                retries += 1
                logger.warning(f'下载[{filename}]异常: {e}，正在进行重试 ({retries}/{max_retries})')
                if retries >= max_retries:
                    raise DownloadModelsError(
                        tr("downloading all files", local_dir) + f'\n[{url}]\n\n多次重试后仍然失败: {e}')

                time.sleep(min(2 ** retries, 30))
    return True


def down_zip(local_dir, zip_url, callback=None) -> bool:
    Path(local_dir).mkdir(parents=True, exist_ok=True)
    from videotrans.configure.excepts import DownloadModelsError
    import requests
    max_retries = 10

    proxy = None
    # modelscope.cn 阿里魔塔不使用代理
    if 'modelscope.cn' not in zip_url:
        proxy = {"https": app_cfg.proxy} if app_cfg.proxy else None
    try:
        filename = get_filename_from_url(zip_url)
    except NameError:
        filename = zip_url.split('/')[-1]
        if '?' in filename:
            filename = filename.split('?')[0]

    logger.debug(f'Download from {zip_url} to {local_dir}')

    # 文件名带 .downloading 后缀 实现“断点续传”
    temp_zip_path = Path(local_dir) / f"{filename}.downloading"
    session = requests.Session()
    retries = 0
    while retries < max_retries:
        try:
            headers = {}
            downloaded_size = 0

            # 检查是否有未完成的临时 zip 文件，有则尝试断点续传
            if temp_zip_path.exists():
                downloaded_size = temp_zip_path.stat().st_size
                if downloaded_size > 0:
                    headers['Range'] = f'bytes={downloaded_size}-'

            with session.get(zip_url, headers=headers, stream=True, timeout=(15, 30), proxies=proxy,
                             verify=False) as response:
                if response.status_code not in (200, 206):
                    response.raise_for_status()

                # 判断源站是否支持 206 Range 续传
                if response.status_code == 206:
                    mode = 'ab'  # 追加
                    remaining = response.headers.get('content-length')
                    total_length = (downloaded_size + int(remaining)) if remaining else None
                else:
                    mode = 'wb'  # 覆盖
                    downloaded_size = 0
                    total_length = response.headers.get('content-length')
                    total_length = int(total_length) if total_length else None

                with open(temp_zip_path, mode) as dest_file_obj:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            dest_file_obj.write(chunk)
                            downloaded_size += len(chunk)

                            if callback:
                                if total_length:
                                    file_percent = min(99.0, (downloaded_size / total_length) * 100)
                                    callback(f'{tr("Download Models")} {filename} {file_percent:.2f}%')
                                else:
                                    mb_size = downloaded_size / (1024 * 1024)
                                    callback(f'{tr("Download Models")} {filename} {mb_size:.1f}MB')

                # 确保 Zip 文件已被完全接收
                if total_length is not None and downloaded_size < total_length:
                    raise ConnectionError(f"Zip下载不完整：预期 {total_length} 字节，实际收到 {downloaded_size} 字节")
                break
        except Exception as e:
            retries += 1
            logger.warning(f'Zip下载[{filename}]发生异常: {e}，正在进行第 ({retries}/{max_retries}) 次重试...')
            if retries >= max_retries:
                msg = tr('model is missing. Please download it', local_dir)
                if callback:
                    callback(f'Error:{msg}')
                raise DownloadModelsError(f"{msg}\n[{zip_url}]\n多次重试后仍然失败: {e}")

            # 指数退避
            time.sleep(min(2 ** retries, 30))

    # === 校验并解压 Zip 文件 ===
    try:
        if callback:
            callback('Extracting zip...')
        with zipfile.ZipFile(temp_zip_path, 'r') as zf:
            zf.extractall(path=local_dir)
        if callback:
            callback('Downloaded end')
        logger.debug(f'下载并解压完毕:{filename}')

        if temp_zip_path.exists():
            temp_zip_path.unlink()

        return True

    except zipfile.BadZipFile as e:
        # 如果 Zip 损坏，立即删除坏文件
        if temp_zip_path.exists():
            temp_zip_path.unlink()
        msg = tr('model is missing. Please download it', local_dir)
        if callback:
            callback(f'Error: Corrupted zip file')
        raise DownloadModelsError(f"{msg}\n[{zip_url}]\n{e}")

    except Exception as e:
        msg = tr('model is missing. Please download it', local_dir)
        if callback:
            callback(f'Error:{msg}')
        raise DownloadModelsError(f"{msg}\n[{zip_url}]\n{e}")


# 从 modelscope.cn 下载完整模型
# 优先加载本地模型，失败则在线下载
_orig_download_file_lists = None
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
        from videotrans.configure.excepts import DownloadModelsError
        raise DownloadModelsError(tr("download model error") + f'{e}')
    finally:
        ms_sd._download_file_lists = _orig_download_file_lists
    return True
