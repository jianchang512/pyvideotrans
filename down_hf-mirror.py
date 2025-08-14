
import os,time
import sys

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
print(f"\n从 hf-mirror.com 下载faster-whisper模型...\n")
from huggingface_hub import snapshot_download

ROOT=os.getcwd()
try:
    print(f'开始下载 tiny 模型...')
    snapshot_download('Systran/faster-whisper-tiny',cache_dir=f"{ROOT}/models",local_dir_use_symlinks=False,resume_download=True)
    print(f'开始下载 base 模型...')
    snapshot_download('Systran/faster-whisper-base',cache_dir=f"{ROOT}/models",local_dir_use_symlinks=False,resume_download=True)
    print(f'开始下载 small 模型...')
    snapshot_download('Systran/faster-whisper-small',cache_dir=f"{ROOT}/models",local_dir_use_symlinks=False,resume_download=True)
    print(f'开始下载 medium 模型...')
    snapshot_download('Systran/faster-whisper-medium',cache_dir=f"{ROOT}/models",local_dir_use_symlinks=False,resume_download=True)
    print(f'开始下载 large-v1 模型...')
    snapshot_download('Systran/faster-whisper-large-v1',cache_dir=f"{ROOT}/models",local_dir_use_symlinks=False,resume_download=True)
    print(f'开始下载 large-v2 模型...')
    snapshot_download('Systran/faster-whisper-large-v2',cache_dir=f"{ROOT}/models",local_dir_use_symlinks=False,resume_download=True)
    print(f'开始下载 large-v3 模型...')
    snapshot_download('Systran/faster-whisper-large-v3',cache_dir=f"{ROOT}/models",local_dir_use_symlinks=False,resume_download=True)
    print(f'开始下载 large-v3-turbo 模型...')
    snapshot_download('mobiuslabsgmbh/faster-whisper-large-v3-turbo',cache_dir=f"{ROOT}/models",local_dir_use_symlinks=False,resume_download=True)
    print('全部下完毕,请关闭')
except Exception as e:
    print(f'下载失败了，请检查网络后重试：{e}')
finally:
    os.system('pause')


