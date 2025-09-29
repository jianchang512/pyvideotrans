# _MODELS 是从 faster-whisper.utils.py 中复制的，未导入，避免间接引入 huggingface_hub
_MODELS = {
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
    "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    "turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
}


# 获取模型的文件夹，对于不完整的体系删除
def get_faster_model_cache(model_id: str, cache_dir: str = '') -> str:
    # 不存在则是其他自定义添加的模型，无需检测
    if model_id not in _MODELS:
        return f'{cache_dir}/{model_id}'
    return f"{cache_dir}/models--" + _MODELS[model_id].replace('/', '--')


# 如果非 faster-whiser 模型，则统统需要联网检测，无需检测缓存，当做缓存不存在

def _is_model_cached(repo_id: str, cache_dir: str = '') -> bool:
    """
    检查指定的模型是否已经存在于本地缓存中。
    只检查 main 分支，只验证 config.json 和 model.bin 文件。

    Args:
        repo_id (str): 模型的标识符，例如 "Systran/faster-whisper-tiny"。
        cache_dir (str): 缓存目录的根路径，默认为 "./models"。

    Returns:
        bool: 如果 config.json 和 model.bin 都存在且非空，返回True；否则返回False。
    """
    from pathlib import Path
    try:
        # 将 repo_id 转换为缓存目录的命名格式
        if '/' in repo_id:
            return False
        if repo_id not in _MODELS:
            return False
        org_name, model_name = _MODELS[repo_id].split('/')
        repo_cache_dir = Path(cache_dir) / f"models--{org_name}--{model_name}"

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
        for it in ["config.json", "model.bin", "tokenizer.json","vocabulary"]:
            if it =='vocabulary':
                if not _is_file_valid(snapshot_dir / 'vocabulary.txt') and not _is_file_valid(snapshot_dir / 'vocabulary.json'):
                    return False
                continue
            if not _is_file_valid(snapshot_dir / it):
                return False

        # 检查两个文件是否存在且非空
        return True
    except Exception:
        return False


def _is_file_valid(file_path) -> bool:
    """
    检查文件是否存在且非空，处理符号链接情况。

    Args:
        file_path (Path): 文件路径

    Returns:
        bool: 文件存在且非空返回True
    """
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


def _check_huggingface_connect(ROOT_DIR: str, proxy: str = None, defaulelang: str = 'zh'):
    import os, requests
    from pathlib import Path
    if defaulelang == 'zh' and not Path(ROOT_DIR + "/huggingface.lock").exists() and not proxy:
        # 中文界面，无锁定huggingface.lock 无代理，需判断能否连接 huggingface.co，如果不能，则使用国内镜像
        os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
        os.environ["HF_HUB_DISABLE_XET"] = "1"
        if os.environ.get('HTTPS_PROXY'):
            os.environ.pop('HTTPS_PROXY')
        if os.environ.get('HTTP_PROXY'):
            os.environ.pop('HTTP_PROXY')
        with open(f'{ROOT_DIR}/logs/test-huggingface.txt', "a", encoding='utf-8') as f:
            f.write(
                f"{proxy=},{os.environ.get('HTTPS_PROXY')=},{os.environ.get('HF_ENDPOINT')=},{os.environ.get('HF_HUB_DISABLE_XET')=}\n")
        return

    try:
        requests.get(
            'https://huggingface.co/api/resolve-cache/models/Systran/faster-whisper-tiny/d90ca5fe260221311c53c58e660288d3deb8d356/config.json',
            proxies=None if not proxy else {"http": proxy, "https": proxy}, timeout=5)
    except Exception as e:
        os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
        os.environ["HF_HUB_DISABLE_XET"] = "1"
    else:
        os.environ['HF_ENDPOINT'] = 'https://huggingface.co'
        if os.environ.get("HF_HUB_DISABLE_XET"):
            os.environ.pop("HF_HUB_DISABLE_XET")

    if proxy:
        os.environ['HTTPS_PROXY'] = proxy
        os.environ['HTTP_PROXY'] = proxy
    else:
        if os.environ.get('HTTPS_PROXY'):
            os.environ.pop('HTTPS_PROXY')
        if os.environ.get('HTTP_PROXY'):
            os.environ.pop('HTTP_PROXY')
    with open(f'{ROOT_DIR}/logs/test-huggingface.txt', "a", encoding='utf-8') as f:
        f.write(
            f"{proxy=},{os.environ.get('HTTPS_PROXY')=},{os.environ.get('HF_ENDPOINT')=},{os.environ.get('HF_HUB_DISABLE_XET')=}\n")


# 返回 True 有缓存，无需设置
# 返回 False 没有缓存，需正确设置代理和镜像站
def check_cache_and_setproxy(repo_id: str, ROOT_DIR: str, proxy: str = None, defulelang: str = 'zh') -> bool:
    # 没有缓存，需要设置
    if not _is_model_cached(repo_id, f"{ROOT_DIR}/models"):
        _check_huggingface_connect(ROOT_DIR, proxy, defulelang)
        return False
    return True


# 格式化模型下载和加载时的异常
def down_model_err(e: Exception, model_name: str, cache_dir: str, defaulelang: str) -> str:
    import os, requests, traceback
    from huggingface_hub.errors import HfHubHTTPError
    error = "".join(traceback.format_exception(e))
    if 'json.exception.parse_error' in error:
        model_dir = get_faster_model_cache(model_name, cache_dir)
        msg = (
            f'模型下载不完整，请删除目录 {model_dir}，重新下载' if defaulelang == "zh" else f"The model download may be incomplete, please delete the directory {model_dir} and download it again")
        if 'hf-mirror.com' in os.environ.get('HF_ENDPOINT', ''):
            msg += f"\n当前从国内镜像站下载，若频繁失败，请考虑科学上网并在软件目录下创建 huggingface.lock 文件，以便从国外源站下载\n更多下载方法查看 https://pvt9.com/819\n"
        msg = f"{msg}\n{error}"
    elif isinstance(e, (requests.exceptions.ChunkedEncodingError,
                        HfHubHTTPError)) or "Unable to open file 'model.bin'" in error or "CAS service error" in error:
        if 'hf-mirror.com' in os.environ.get('HF_ENDPOINT', ''):
            msg = '从国内镜像站下载模型失败，若频繁失败，请考虑科学上网并在软件目录下创建 huggingface.lock 文件，以便从国外源站下载\n更多下载方法查看 https://pvt9.com/819\n'
        else:
            msg = f'下载模型失败了，请确认网络稳定并能连接 huggingface.co\n更多下载方法查看 https://pvt9.com/819\n' if defaulelang == 'zh' else f'Download model failed, please confirm network stable and try again.\n'
        msg = f'{msg}{error}'
    elif "CUBLAS_STATUS_NOT_SUPPORTED" in error:
        msg = f"数据类型不兼容：请打开菜单--工具--高级选项--faster/openai语音识别调整--CUDA数据类型--选择 float16，保存后重试:{error}" if defaulelang == 'zh' else f'Incompatible data type: Please open the menu - Tools - Advanced options - Faster/OpenAI speech recognition adjustment - CUDA data type - select float16, save and try again:{error}'
    elif "cudaErrorNoKernelImageForDevice" in error:
        msg = f"pytorch和cuda版本不兼容，请更新显卡驱动后，安装或重装CUDA12.x及cuDNN9.x:{error}" if defaulelang == 'zh' else f'Pytorch and cuda versions are incompatible. Please update the graphics card driver and install or reinstall CUDA12.x and cuDNN9.x:{error}'
    else:
        msg = error
    return msg
