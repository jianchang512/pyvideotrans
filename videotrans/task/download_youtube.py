# 从日志队列获取日志
import subprocess
import sys, io
from pathlib import Path
import json
from PySide6.QtCore import QThread, Signal

from videotrans.configure import config
from videotrans.util.tools import set_process


class Download(QThread):
    uito = Signal(str)
    
    def post(self,msg):
        self.uito.emit(json.dumps(msg))

    def __init__(self, *, url=None, proxy=None, out=None, parent=None, vid=False,thread_num=8):
        super().__init__(parent=parent)
        self.url = url
        self.proxy = proxy
        self.out = out
        self.vid = vid
        self.thread_num=thread_num

    def run(self):
        self.post({"type":"logs","text":f'{config.transobj["downing..."]}'})
        cmd = ""
        p = None
        downlink={
            "win32":'https://github.com/jianchang512/pyvideotrans/releases/download/v2.19/ytwin32.exe',
            "linux":'https://github.com/jianchang512/pyvideotrans/releases/download/v2.19/ytlinux',
            "darwin":'https://github.com/jianchang512/pyvideotrans/releases/download/v2.19/ytdarwin'

        }
        try:
            pwd = config.rootdir + f"/ffmpeg/yt{sys.platform}"
            if sys.platform=='win32':
                pwd+='.exe'
            if not Path(pwd).exists():
                msg=f'请下载该文件并放置在ffmpeg文件夹内 {downlink[sys.platform]}'
                self.uito.emit(f'error:{msg}')
                return

            proxy = self.proxy if self.proxy.startswith("http") or self.proxy.startswith('sock') else None
            proxy = "" if not proxy else f' --proxy {proxy} '

            outname = ""
            if self.vid:
                outname = '  -o %(id)s.mp4'
            cmd = f'{pwd} -c -P {self.out}  -N {self.thread_num} -f bestvideo+bestaudio  -r 10M  {proxy} --windows-filenames --force-overwrites -q  --progress --no-warnings  --ignore-errors --merge-output-format mp4 {self.url}{outname}'
            print(f'{cmd=}')
            p = subprocess.run(cmd, check=True)
            if p.returncode == 0:
                self.post({"type":"ok","text":f'下载完成' if config.defaulelang == 'zh' else 'Download succeed'})
        except subprocess.CalledProcessError as e:
            err = str(e.stderr)
            config.logger.error(f'下载youtube失败:,')
            self.post({"type":"error","text":"下载失败，请检查网络连接/代理地址/播放页地址"})
        except BrokenPipeError:
            pass
            # sys.stdout = None
        except Exception as e:
            config.logger.error(f'下载youtube失败:{str(e)}')
            self.post({"type":"error","text":str(e)})
