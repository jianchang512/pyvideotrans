# 从日志队列获取日志
import subprocess
import sys,io
from PySide6.QtCore import QThread

from videotrans.configure import config
from videotrans.util.tools import  set_process


class Download(QThread):

    def __init__(self, *,url=None,proxy=None,out=None,parent=None,vid=False):
        super().__init__(parent=parent)
        self.url=url
        self.proxy=proxy
        self.out=out
        self.vid=vid

    def run(self):
        set_process(config.transobj["downing..."],'update_download')
        cmd=""
        p=None
        try:
            pwd=config.rootdir+f"/ffmpeg/yt{sys.platform}"
            proxy=self.proxy if self.proxy.startswith("http") or self.proxy.startswith('sock') else None
            proxy="" if not proxy else f' --proxy {proxy} '
            
            outname=""
            if self.vid:
                outname='  -o %(id)s.mp4'
            
            cmd=f'{pwd} -c -P {self.out}   {proxy} --windows-filenames --force-overwrites    --ignore-errors --merge-output-format mp4 {self.url}{outname}'
            print(f'{cmd=}')
            p=subprocess.run(cmd,check=True)
            if p.returncode==0:
                set_process(f'下载完成' if config.defaulelang=='zh' else 'Download succeed','youtube_ok')
        except subprocess.CalledProcessError as e:
            err=str(e.stderr)
            config.logger.error(f'下载youtube失败:,')
            set_process(f"\n下载失败，请检查网络连接/代理地址/播放页地址\n",'youtube_error')
        except BrokenPipeError:
            pass
            #sys.stdout = None
        except Exception as e:
            config.logger.error(f'下载youtube失败:{str(e)}')
            set_process(str(e),'youtube_error')
