# -*- coding: utf-8 -*-
import os
import sys
import tempfile
from pathlib import Path

from videotrans.configure.contants import no_proxy

IS_FROZEN = True if getattr(sys, 'frozen', False) else False
SYS_TMP = Path(tempfile.gettempdir()).as_posix()
ROOT_DIR = Path(sys.executable).parent.as_posix() if IS_FROZEN else Path(__file__).parent.parent.parent.as_posix()
TEMP_ROOT = f'{ROOT_DIR}/tmp'
LOGS_DIR = f'{ROOT_DIR}/logs'
TEMP_DIR = f'{TEMP_ROOT}/None'
TRANSLATE_CACHE = f'{TEMP_ROOT}/translate_cache'

Path(f"{ROOT_DIR}/models").mkdir(parents=True, exist_ok=True)
Path(f"{ROOT_DIR}/logs").mkdir(parents=True, exist_ok=True)
Path(f"{TRANSLATE_CACHE}").mkdir(parents=True, exist_ok=True)

def fix_ssl_cert_env():
    """
    修复部分用户电脑上存在错误的全局 SSL 证书环境变量，
    强制将其指向程序自带的 certifi 证书路径。
    """
    try:
        import certifi
        ca_bundle = certifi.where()
        
        # 确保该路径确实存在（兼容 PyInstaller 打包后的临时目录）
        if os.path.exists(ca_bundle):
            # 强制覆盖用户的错误环境变量，指引到正确的证书
            os.environ['CURL_CA_BUNDLE'] = ca_bundle
            os.environ['REQUESTS_CA_BUNDLE'] = ca_bundle
            os.environ['SSL_CERT_FILE'] = ca_bundle
        else:
            raise FileNotFoundError
            
    except Exception:
        # 如果 certifi 加载失败，至少把错误的干扰变量删掉，让系统回退到默认逻辑
        for key in ['CURL_CA_BUNDLE', 'REQUESTS_CA_BUNDLE', 'SSL_CERT_FILE']:
            os.environ.pop(key, None)



def _set_env():
    if IS_FROZEN:
        os.environ['TQDM_DISABLE'] = '1'
    os.environ['no_proxy'] = no_proxy
    os.environ['NO_PROXY'] = no_proxy
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
    os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
    os.environ["CT2_VERBOSE"] = "1"
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["PYTHONWARNINGS"]="ignore"
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
    os.environ['PYTHONUTF8'] = '1'
    os.environ['QT_API'] = 'pyside6'
    os.environ['SOFT_NAME'] = 'pyvideotrans'
    os.environ['MODELSCOPE_CACHE'] = ROOT_DIR + "/models"
    os.environ['HF_HOME'] = ROOT_DIR + "/models"
    os.environ['HF_HUB_CACHE'] = ROOT_DIR + "/models"
    os.environ['HF_TOKEN_PATH'] = ROOT_DIR + "/models/hf_token.txt"
    os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = 'true'
    os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = "3600"
    os.environ["HF_HUB_DISABLE_XET"] = "1"
    os.environ['GRADIO_ANALYTICS_ENABLED'] = '0'
    # 必须在 import requests, modelscope 等库之前执行！
    fix_ssl_cert_env()
    if Path(f'{ROOT_DIR}/netoffline.txt').is_file():
        os.environ['HF_HUB_OFFLINE'] = '1'

    if sys.platform == 'win32' and IS_FROZEN:
        os.environ['PATH'] = f'{ROOT_DIR}/_internal/torch/lib;' + os.environ.get("PATH", "")
    os.environ['PATH'] = ROOT_DIR + os.pathsep + f'{ROOT_DIR}/ffmpeg' + os.pathsep + f'{ROOT_DIR}/ffmpeg/sox' + os.pathsep + os.environ.get(
        "PATH", "")
