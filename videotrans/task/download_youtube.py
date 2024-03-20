# 从日志队列获取日志
import subprocess
import sys,io
from PySide6.QtCore import QThread

from videotrans.configure import config
from videotrans.util.tools import  set_process
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


class Download(QThread):

    def __init__(self, *,url=None,proxy=None,out=None,parent=None):
        super().__init__(parent=parent)
        self.url=url
        self.proxy=proxy
        self.out=out

    def run(self):
        set_process(config.transobj["downing..."],'update_download')
        cmd=""
        try:
            pwd=config.rootdir+f"/ffmpeg/yt{sys.platform}"
            proxy=self.proxy if self.proxy.startswith("http") or self.proxy.startswith('sock') else None
            proxy="" if not proxy else f' --proxy {proxy} '
            cmd=f'{pwd} -c -P {self.out}   {proxy} --windows-filenames --force-overwrites    --ignore-errors --merge-output-format mp4 {self.url}'
            print(f'{cmd=}')
            p=subprocess.run(cmd,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding="utf-8",text=True)
            if p.returncode==0:
                set_process(f'下载完成' if config.defaulelang=='zh' else 'Download succeed','youtube_ok')
        except subprocess.CalledProcessError as e:
            err=str(e.stderr)
            config.logger.error(f'下载youtube失败:{err}')
            set_process(err+f"\n下载失败，请直接复制下行命令到cmd控制台粘贴执行\n\n{cmd}\n",'youtube_error')
        except BrokenPipeError:
            sys.stdout = None
        except Exception as e:
            config.logger.error(f'下载youtube失败:{str(e)}')
            set_process(str(e),'youtube_error')
