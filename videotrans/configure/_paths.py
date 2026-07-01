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

    if sys.platform == 'win32' and IS_FROZEN:
        os.environ['PATH'] = f'{ROOT_DIR}/_internal/torch/lib;' + os.environ.get("PATH", "")
    os.environ['PATH'] = ROOT_DIR + os.pathsep + f'{ROOT_DIR}/ffmpeg' + os.pathsep + f'{ROOT_DIR}/ffmpeg/sox' + os.pathsep + os.environ.get(
        "PATH", "")
