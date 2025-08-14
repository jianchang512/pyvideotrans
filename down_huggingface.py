
import os,time,sys

def get_proxy():
    # 获取代理
    http_proxy = os.environ.get('http_proxy') or os.environ.get('https_proxy')
    if http_proxy:
        return http_proxy
    if sys.platform != 'win32':
        return None
    try:
        import winreg
        # 打开 Windows 注册表
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
            # 读取代理设置
            proxy_enable, _ = winreg.QueryValueEx(key, 'ProxyEnable')
            proxy_server, _ = winreg.QueryValueEx(key, 'ProxyServer')
            if proxy_server:
                # 是否需要设置代理
                if not proxy_server.startswith("http") and not proxy_server.startswith('sock'):
                    proxy_server = "http://" + proxy_server
                return proxy_server
    except Exception as e:
        pass
    return None

proxy=get_proxy()
if proxy:
    os.environ['http_proxy'] = proxy
    os.environ['all_proxy'] = proxy
# proxies={"http://":proxy,"https://":proxy} if proxy else None
print(f"\n从 huggingface.co 下载faster-whisper模型，中国大陆地区需开启系统代理...\n")
print(f'当前使用代理：{proxy}')
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
    print(f'下载失败了，请检查网络代理后重试')
    print('请尝试切换代理节点，可能该节点ip被污染无法下载' if proxy else '')
    print(f'错误信息:{e}')
finally:
    os.system('pause')

