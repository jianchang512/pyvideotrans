import os

from videotrans.util import tools


from dataclasses import dataclass, field
from typing import Optional
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
            try:
                os.environ['bak_proxy']=os.environ.get('http_proxy') or os.environ.get('https_proxy')
                del os.environ['http_proxy']
                del os.environ['https_proxy']
                del os.environ['all_proxy']
            except:
                pass
            self.shound_del = False
            return

        if type == 'set':
            raw_proxy = os.environ.get('https_proxy') or os.environ.get('http_proxy')
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

    def convert_to_wav(self, mp3_file_path: str, output_wav_file_path: str):
        cmd = [
            "-y",
            "-i",
            mp3_file_path,
            "-ar",
            "44100",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            output_wav_file_path
        ]
        return tools.runffmpeg(cmd,force_cpu=True)