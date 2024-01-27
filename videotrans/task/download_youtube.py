# 从日志队列获取日志
import subprocess
import sys
from PySide6.QtCore import QThread

from videotrans.util.tools import  set_process


class Download(QThread):

    def __init__(self, cmd=[],parent=None):
        super().__init__(parent=parent)
        self.cmd=cmd

    def run(self):
        """
        cmd = ["you-get", "--itag=18", "-o", outdir]
            if proxy:
                config.proxy = proxy
                self.main.settings.setValue("proxy", proxy)
                cmd.append("-x")
                cmd.append(proxy)
            cmd.append(url)

        :return:
        """
        # if sys.platform != "win32":
        from you_get.extractors import  youtube
        set_process("downing...",'update_download')
        try:
            youtube.download(self.cmd[-1],
                output_dir=self.cmd[3],
                merge=True,
                extractor_proxy=self.cmd[-2] if self.cmd[-2].startswith("http") or self.cmd[-2].startswith('sock') else None
            )
        except Exception as e:
            set_process(str(e),'update_download')

            return
        set_process('ok','update_download')
        return
        p = subprocess.Popen(self.cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             shell=True,
                             creationflags=0 if sys.platform != 'win32' else subprocess.CREATE_NO_WINDOW
                             )

        while True:
            try:
                # 等待0.1未结束则异常
                outs, errs = p.communicate(timeout=0.5)
                try:
                    errs = str(errs.decode('utf-8'))
                except:
                    errs = str(errs.decode('gbk'))
                if errs:
                    errs = errs.replace('\\\\', '\\').replace('\r', ' ').replace('\n', ' ')

                # 如果结束从此开始执行
                if p.returncode==0:
                    # 成功
                    set_process('ok','update_download')
                    break
                # 失败
                print(errs)
                set_process(errs,'update_download')
            except subprocess.TimeoutExpired as e:
                # 如果前台要求停止
                set_process("downing...",'update_download')

            except Exception as e:
                # 出错异常
                print(str(e))
                set_process(str(e),'update_download')
