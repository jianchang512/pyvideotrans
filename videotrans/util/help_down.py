# 下载模型，首先测试 huggingface.co 连通性，不可用则回退镜像 hf-mirror.com
import time
from pathlib import Path
import shutil,os,requests

from huggingface_hub import snapshot_download

from videotrans.configure import config
from .help_misc import create_tqdm_class

# 用于判断某个目录内是否存在指定类型的文件，存在则视为已存在
def file_exists(dirname,glob_patter='*.bin'):
    for it in Path(dirname).glob(glob_patter):
        return True
    return False

def get_modeldir_download(model_name,repo_id,local_dir,callback=None):
    Path(local_dir).mkdir(exist_ok=True, parents=True)
    # 已存在
    if file_exists(local_dir,glob_patter='*.bin') or file_exists(local_dir,glob_patter='*.safetensors') or file_exists(local_dir,glob_patter='*.onnx'):
        return True

    try:
        requests.head('https://huggingface.co', timeout=5)
    except Exception:
        print(f'无法连接 huggingface.co, 使用镜像替换: hf-mirror.com, {model_name=}')
        endpoint = 'https://hf-mirror.com'
        if model_name in ['large-v3-turbo', 'turbo']:
            try:
                # 针对 large-v3-turbo 模型使用 modelscope.cn 下载
                return faster_turbo_from_modelscope(local_dir,callback=callback)
            except Exception as e:
                print(f'阿里镜像下载 失败:{e}')
                # 失败继续使用镜像尝试
    else:
        print('可以使用 huggingface.co')
        endpoint = 'https://huggingface.co'

    # 不存在，需要下载
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
def faster_turbo_from_modelscope(local_dir,callback=None):
    print('阿里镜像下载')
    import requests
    urls = [
        'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/config.json',
        'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/preprocessor_config.json',
        'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/tokenizer.json',
        'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/vocabulary.json',
        'https://modelscope.cn/models/himyworld/videotrans/resolve/master/large-v3-turbo/model.bin',
    ]
    for index, url in enumerate(urls):
        filename = os.path.basename(url)
        print(filename)
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
                    if callback:
                        callback({"type":"file","percent":f'[{(index+1)*100/5:.2f}%]',"filename":filename,"current":index+1,"total":5})
                    last_send = time.time()
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            dest_file_obj.write(chunk)
                            downloaded += len(chunk)
                            file_percent = min((downloaded / total_length) * 100, 100)
                            if time.time() - last_send > 3:
                                last_send = time.time()

            finally:
                dest_file_obj.close()
    return local_dir
