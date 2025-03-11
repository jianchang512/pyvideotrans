import asyncio
import threading
import time
from pathlib import Path


import aiohttp
from aiohttp import ClientError, WSServerHandshakeError

from videotrans.configure import config
from videotrans.configure._except import IPLimitExceeded
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
from edge_tts import Communicate

# asyncio 异步并发

class EdgeTTS(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pro = self._set_proxy(type='set')        
        if pro:
            self.proxies= pro


    async def _task_queue(self):
        
        task_end=False
        
        def process():
            if task_end:
                return        
        try:
            length=len(self.queue_tts)
            for i,it in enumerate(self.queue_tts):
                if task_end or self._exit():
                    return
                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.05
                self._signal(text=f'{config.transobj["kaishipeiyin"]} [{i+1}/{length}]')
                time.sleep(self.wait_sec if self.wait_sec>0 else 0.1)
                communicate = Communicate(
                    it['text'],
                    voice=it['role'],
                    rate=self.rate, 
                    volume=self.volume,
                    proxy=self.proxies,
                    pitch=self.pitch)
                await communicate.save(it['filename'])

        except aiohttp.client_exceptions.ClientHttpProxyError as e:
            config.logger.exception(e, exc_info=True)
            raise Exception(f'代理错误，请检查 {e}')
        except Exception as e:
            config.logger.exception(e, exc_info=True)
            if str(e).find('Invalid response status'):
                raise Exception('可能被edge限流，请尝试使用或切换代理节点')
            print(f"异步合成出错: {e}")
            raise
        finally:
            task_end=True
        print('配音完毕')
    
    def _exec(self) -> None:
        # 防止出错，重试一次
        if self._exit():
            return
        if Path(config.ROOT_DIR+'/edgetts.txt').is_file():
            self.proxies='http://'+Path(config.ROOT_DIR+'/edgetts.txt').read_text(encoding='utf-8').strip()
            print(f'{self.proxies=}')
        asyncio.run(self._task_queue())
        