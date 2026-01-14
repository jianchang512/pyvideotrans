# 下载模型，首先测试 huggingface.co 连通性，不可用则回退镜像 hf-mirror.com
import tempfile
import time
from pathlib import Path
import shutil, os, requests
import zipfile
from huggingface_hub import snapshot_download

from videotrans.configure import config
from .help_misc import create_tqdm_class
from urllib.parse import urlparse
def get_filename_from_url(url):
    """解析URL获取纯净文件名 (去除 ?query)"""
    parsed = urlparse(url)
    return os.path.basename(parsed.path)

# 从 huggingface 下载单个文件
"""
urls_dict={
            f'{name}.onnx':f'{url}/{name}.onnx?download=true',
            f'{name}.onnx.json':f'{url}/{name}.onnx.json?download=true',
        }
"""


def down_file_from_hf(local_dir, urls_dict=None, callback=None) -> bool:
    try:
        requests.head('https://huggingface.co', timeout=3)
    except Exception:
        print(f'无法连接 huggingface.co, 使用镜像替换: hf-mirror.com')
        endpoint = 'https://hf-mirror.com'
    else:
        print('可以使用 huggingface.co')
        endpoint = 'https://huggingface.co'
    for filename, url in urls_dict.items():
        try:
            with requests.get(f'{endpoint}{url}', stream=True, timeout=60) as response:
                response.raise_for_status()
                total_length = response.headers.get('content-length')

                dest_file_obj = open(f'{local_dir}/{filename}', 'wb')

                try:
                    if total_length is None:
                        dest_file_obj.write(response.content)
                    else:
                        total_length = int(total_length)
                        downloaded = 0
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                dest_file_obj.write(chunk)
                                downloaded += len(chunk)

                                # 计算进度
                                # 单文件进度 0-100
                                file_percent = (downloaded / total_length)
                                if callback:
                                    callback(f'Downloading {filename}:{file_percent * 100:.2f}%')
                finally:
                    dest_file_obj.close()  # 关闭实体文件句柄
        except Exception as e:
            raise RuntimeError(
                config.tr("downloading all files", local_dir) + f'\n[https://huggingface.co{url}]\n\n{e}')
    return True


# 用于判断某个目录内是否存在指定类型的文件，存在则视为已存在
def file_exists(dirname, glob_patter='*.bin') -> bool:
    if isinstance(glob_patter,str):
        glob_patter=[glob_patter]
    for pat in glob_patter:
        for it in Path(dirname).glob(pat):
            return True
    return False


# 从 huggingface.co 下载模型
def get_modeldir_download(model_name, repo_id, local_dir, callback=None) -> bool:
    Path(local_dir).mkdir(exist_ok=True, parents=True)
    if config.defaulelang == 'zh' and model_name in ['large-v3-turbo', 'turbo']:
        try:
            # 针对 large-v3-turbo 模型使用 modelscope.cn 下载,若失败继续从 huggingface下载
            faster_turbo_from_modelscope(local_dir, callback=callback)
        except Exception as e:
            config.logger.exception(f'从 modelscope.cn 下载 {model_name} 模型失败', exc_info=True)
        else:
            return True
    try:
        requests.head('https://huggingface.co', timeout=3)
    except Exception:
        print(f'无法连接 huggingface.co, 使用镜像替换: hf-mirror.com, {model_name=}')
        endpoint = 'https://hf-mirror.com'
    else:
        print('可以使用 huggingface.co')
        endpoint = 'https://huggingface.co'

    try:
        if callback:
            callback = create_tqdm_class(callback)
        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            local_dir_use_symlinks=False,
            endpoint=endpoint,
            etag_timeout=5,
            tqdm_class=callback,
            ignore_patterns=["*.msgpack", "*.h5", ".git*", "*.md"]
        )
    except Exception as e:
        msg = f'下载模型失败，你可以打开以下网址，将所有文件下载到\n {local_dir} 文件夹内\n' if config.defaulelang == 'zh' else f'The model download failed. You can try opening the following URL and downloading all files to the {local_dir} folder.'
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
                    print(f"clear cache: {junk}")
                except Exception as e:
                    print(f"{junk} {e}")
        return True


# 在下载默认模型 large-v3-turbo时，针对国内无法连接huggingface.co，且镜像站不稳定的情况，使用 modelscope.cn替换
def faster_turbo_from_modelscope(local_dir, callback=None) -> bool:
    urls = [
        'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/config.json',
        'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/preprocessor_config.json',
        'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/tokenizer.json',
        'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/vocabulary.json',
        'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/model.bin',
    ]
    try:
        for index, url in enumerate(urls):
            filename = os.path.basename(url)
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
                                if callback:
                                    callback(
                                        {"type": "file", "percent": file_percent, "filename": f"Download {filename}",
                                         "current": index + 1, "total": 5})

                finally:
                    dest_file_obj.close()
    except Exception as e:
        msg = config.tr('downloading all files', local_dir)
        url = 'https://modelscope.cn/models/himyworld/videotrans/tree/master/large-v3-turbo'
        raise RuntimeError(f"{msg}\n[{url}]\n{e}")
    return True


# 下载zip并解压 到指定目录
def down_zip(local_dir, zip_url, callback=None) -> bool:
    try:
        filename=get_filename_from_url(zip_url)
        with requests.get(zip_url, stream=True, timeout=60) as response:
            response.raise_for_status()
            total_length = response.headers.get('content-length')

            # 决定写入目标：如果是需要解压的，写入临时文件；否则直接写入目标文件
            dest_file_obj = tempfile.TemporaryFile()  # 内存/临时磁盘，自动删除

            if total_length is None:
                dest_file_obj.write(response.content)
            else:
                total_length = int(total_length)
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        dest_file_obj.write(chunk)
                        downloaded += len(chunk)

                        # 计算进度
                        # 单文件进度 0-100
                        file_percent = min(99.0, downloaded * 100 / total_length)
                        if callback:
                            callback(f'Downloading {filename} {file_percent:.2f}%')

            if callback:
                callback(f'Extracting zip')
            dest_file_obj.seek(0)  # 回到文件头
            with zipfile.ZipFile(dest_file_obj) as zf:
                zf.extractall(path=local_dir)
            if callback:
                callback('Download & extract end')
            dest_file_obj.close()
    except Exception as e:
        msg = config.tr('model is missing. Please download it', local_dir)
        raise RuntimeError(f"{msg}\n[{zip_url}]\n{e}")
    return True
