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
            length=len(self.queue_tts)
            while 1:
                if task_end or self._exit():
                    return
                had=0
                for it in self.queue_tts:
                    if Path(it['filename']).is_file():
                        had+=1
                print(f'{had}/{length}')
                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.05
                self._signal(text=f'{config.transobj["kaishipeiyin"]} [{had}/{length}]')
                time.sleep(0.5)
        
        
        try:
            for it in self.queue_tts:
                communicate = Communicate(
                    it['text'],
                    voice=it['role'],
                    rate=self.rate, 
                    volume=self.volume,
                    proxy=self.proxies,
                    pitch=self.pitch)
                await communicate.save(it['filename'])
            """
            else:
                from videotrans.edge_tts.communicate_list import Communicate
                # 创建 Communicate 对象
                communicate = Communicate(text_list=self.queue_tts,rate=self.rate, volume=self.volume,
                        proxy=self.proxies,
                        pitch=self.pitch,max_retries=5, retry_delay = 2) # 设置最大重试次数为 5，重试延迟为2
                # 异步合成并保存
                threading.Thread(target=process).start()
                await communicate.stream()
            """
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
        