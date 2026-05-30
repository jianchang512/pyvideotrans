# 下载模型，首先测试 huggingface.co 连通性，不可用则回退镜像 hf-mirror.com
import tempfile
import time
from pathlib import Path
import shutil, os, requests
import zipfile
from videotrans.configure.config import ROOT_DIR, tr, logger, defaulelang
from videotrans.configure.contants import FASTER_MODELS_DICT
from .help_misc import create_tqdm_class
from urllib.parse import urlparse

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


def is_connect_hf():
    if os.environ.get('HF_ENDPOINT')=='https://hf-mirror.com':
        return False
    try:
        requests.head('https://huggingface.co', timeout=3)
    except Exception as e:
        logger.warning(f'无法连接 huggingface.co, 使用镜像替换: hf-mirror.com\n{e}')
        os.environ['HF_ENDPOINT']='https://hf-mirror.com'
        return False
    else:
        logger.info('可以使用 huggingface.co')
        os.environ['HF_ENDPOINT']='https://huggingface.co'
        return True


# 从 huggingface.co 下载完整模型，先本地下载，失败则在线下载
def check_and_down_hf(model_id, repo_id, local_dir, callback=None,allow_list=None) -> bool:
    try:
        if model_id in FASTER_MODELS_DICT and (defaulelang == 'zh' or is_connect_hf() is False):
            if model_id == 'turbo':
                model_id = 'large-v3-turbo'
            elif model_id == 'distil-large-v3.5-ct2':
                model_id = 'distil-large-v3.5'
            elif model_id == 'large':
                model_id = 'large-v3'

            URL_PRE = f'https://modelscope.cn/models/himyworld/fasterwhisper/resolve/master/{model_id}/'

            if model_id in ['large-v3', 'large-v3-turbo', 'distil-large-v3', 'distil-large-v3.5']:
                all_urls = ["vocabulary.json", "preprocessor_config.json"]
            else:
                all_urls = ["vocabulary.txt"]
            all_urls += ["config.json", "tokenizer.json", "model.bin", ]
            return down_file_from_ms(local_dir, urls=[f'{URL_PRE}{u}' for u in all_urls], callback=callback)
        import huggingface_hub
        from huggingface_hub.errors import LocalEntryNotFoundError
        try:
            huggingface_hub.snapshot_download(
                repo_id=repo_id,
                local_dir=local_dir,
                etag_timeout=5,
                local_files_only=True
            )
        except LocalEntryNotFoundError:
            Path(local_dir).mkdir(exist_ok=True, parents=True)
            MyTqdmClass = None
            if callback:
                MyTqdmClass = create_tqdm_class(callback)

            is_connect_hf()
            huggingface_hub.snapshot_download(
                repo_id=repo_id,
                local_dir=local_dir,
                local_dir_use_symlinks=False,
                endpoint=os.environ.get('HF_ENDPOINT'),
                etag_timeout=10,
                tqdm_class=MyTqdmClass,
                local_files_only=False,
                max_workers=1,
                ignore_patterns=["*.msgpack", "*.h5", ".git*", "*.md"],
                allow_patterns=allow_list
            )
        else:
            return True
    except Exception as e:
        msg = f'下载模型失败，你可以打开以下网址，将所有文件下载到\n {local_dir} 文件夹内\n' if defaulelang == 'zh' else f'The model download failed. You can try opening the following URL and downloading all files to the {local_dir} folder.'
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
            full_path = Path(local_dir) / junk
            if full_path.exists():
                try:
                    if full_path.is_dir():
                        shutil.rmtree(full_path)
                    else:
                        os.remove(full_path)
                except OSError as e:
                    logger.exception(f"清理临时文件失败：{junk} {e}",exc_info=True)
    return True


# 从 huggingface 下载单个文件
def down_file_from_hf(local_dir, urls=None, callback=None) -> bool:
    is_connect_hf()
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
            raise RuntimeError(
                tr("downloading all files", local_dir) + f'\n[https://huggingface.co{url}]\n\n{e}')
    return True


# 从 modelscope.cn 下载单个文件
def down_file_from_ms(local_dir, urls=None, callback=None) -> bool:
    Path(local_dir).mkdir(parents=True, exist_ok=True)
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


# 下载zip并解压 到指定目录
def down_zip(local_dir, zip_url, callback=None) -> bool:
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
        raise RuntimeError(f"{msg}\n[{zip_url}]\n{e}")
    return True


# 从 modelscope.cn 下载完整模型
def check_and_down_ms(model_id, callback=None, local_dir=None) -> bool:
    from modelscope.hub.callback import TqdmCallback
    from modelscope.hub.snapshot_download import snapshot_download
    class Pro(TqdmCallback):
        def __init__(self, *args):
            super().__init__(*args)

        def update(self, size):
            super().update(size)
            try:
                _str = str(self.progress).split('%')[0] + '%'
                if callback:
                    callback(_str)
            except Exception:
                pass

    try:
        try:
            # 如果本地加载失败，则在线下载
            snapshot_download(model_id=model_id, local_files_only=True, progress_callbacks=[Pro], local_dir=local_dir)
            if callback:
                callback(f'{model_id} exists')
        except ValueError:
            if callback:
                callback(f'{model_id}')
            snapshot_download(model_id=model_id, progress_callbacks=[Pro], local_dir=local_dir, max_workers=1)
        else:
            return True
    except Exception as e:
        local_dir = f'{ROOT_DIR}/models/models/{model_id}/' if not local_dir else local_dir
        msg = f'下载模型失败，你可以打开以下网址，将所有文件下载到\n {local_dir} 文件夹内\n' if defaulelang == 'zh' else f'The model download failed. You can try opening the following URL and downloading all files to the {local_dir} folder.'
        raise RuntimeError(f'{msg}\n[https://modelscope.cn/models/{model_id}/tree/main]\n{e}')
    return True
