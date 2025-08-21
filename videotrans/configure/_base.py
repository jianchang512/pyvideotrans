import os
import subprocess
from dataclasses import dataclass, field
from typing import Optional

from videotrans.util import tools


@dataclass
class BaseCon:
    uuid: Optional[str] = field(default=None, init=False)
    shound_del: bool = field(default=False, init=False)

    def _signal(self, **kwargs):
        if 'uuid' not in kwargs:
            kwargs['uuid'] = self.uuid
        tools.set_process(**kwargs)

    def _set_proxy(self, type='set'):
        if type == 'del':
            from . import config
            try:
                os.environ['bak_proxy'] = config.proxy or os.environ.get('http_proxy') or os.environ.get('https_proxy')
                config.proxy=None
                del os.environ['http_proxy']
                del os.environ['https_proxy']
                del os.environ['all_proxy']
            except:
                pass
            self.shound_del = False
            return

        if type == 'set':
            from . import config
            raw_proxy = config.proxy or os.environ.get('https_proxy') or os.environ.get('http_proxy')
            if raw_proxy:
                return raw_proxy
            if not raw_proxy:
                proxy = tools.set_proxy() or os.environ.get('bak_proxy')
                if proxy:
                    self.shound_del = True
                    os.environ['http_proxy'] = proxy
                    os.environ['https_proxy'] = proxy
                    os.environ['all_proxy'] = proxy
                return proxy
        return None

    def _external_cmd_with_wrapper(self, cmd_list=None):
        if not cmd_list:
            raise ValueError("cmd_list is None")
        from . import config

        try:
            subprocess.run(cmd_list, capture_output=True, text=True, check=True, encoding='utf-8', creationflags=0,
                           cwd=os.path.dirname(cmd_list[0]))
        except subprocess.CalledProcessError as e:
            if os.name == 'nt' and config.IS_FROZEN:
                raise RuntimeError(
                    '当前Faster-Whisper-XXL无法在打包版中使用，请源码部署或单独使用Faster-Whisper-XXL转录' if config.defaulelang == 'zh' else 'Currently Faster-Whisper-XXL cannot be used in the packaged version. Please deploy the source code or use Faster-Whisper-XXL transcription separately.')
            raise RuntimeError(e.stderr)
        # 不是 Windows 或 非打包
        '''
        if os.name != 'nt' or not config.IS_FROZEN:
            return subprocess.run(cmd_list, capture_output=True, text=True, check=True,encoding='utf-8')

        import json
        try:            

            config.logger.info(f'执行:{cmd_list=}')
            os.environ['TQDM_DISABLE'] = '0'
            subprocess.run(cmd_list, creationflags=0,cwd=os.path.dirname(cmd_list[0]),
                        check=True,
                        capture_output=True, # 捕获 stdout 和 stderr
                        text=True,           # 将它们解码为文本
                        encoding='utf-8',    # 使用 utf-8 解码
                        errors='replace'
            )
            os.environ['TQDM_DISABLE'] = '1'
            config.logger.info("[OK]:Faster-XXL success")
            return True
        except subprocess.CalledProcessError as e:
            config.logger.error(f"Faster-XXL: {e.stderr}")
        except Exception as e:
            config.logger.error(f"Faster-XXL: {e}")
            raise
        '''

    def convert_to_wav(self, mp3_file_path: str, output_wav_file_path: str, extra=None):
        cmd = [
            "-y",
            "-i",
            mp3_file_path,
            "-ar",
            "44100",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le"
        ]
        if extra:
            cmd += extra
        cmd += [
            output_wav_file_path
        ]
        return tools.runffmpeg(cmd, force_cpu=True)
