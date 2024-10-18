import asyncio
import threading
import time

import edge_tts
from aiohttp import ClientError, WSServerHandshakeError

from videotrans.configure import config
from videotrans.configure._except import IPLimitExceeded
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


# asyncio 异步并发

class EdgeTTS(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pro = self._set_proxy(type='set')
        if pro:
            self.proxies= pro

    def _dubb(self,it):
        async def _async_dubb(it):
            communicate_task = edge_tts.Communicate(
                text=it["text"], voice=it['role'], rate=self.rate, volume=self.volume,
                proxy=self.proxies,
                pitch=self.pitch)
            await communicate_task.save(it['filename'])
        try:
            asyncio.run(_async_dubb(it))
        except (ClientError,WSServerHandshakeError) as e:
            self.error = e.message if hasattr(e, 'message') else str(e)
        except Exception as e:
            self.error=str(e)
        else:
            self.error=''

    def _item_task(self, data_item=None):
        split_queue = [self.queue_tts[i:i + self.dub_nums] for i in range(0, self.len, self.dub_nums)]
        for items in split_queue:
            tasks = []

            for it in items:
                if self._exit():
                    return
                if it['text'].strip() and not tools.vail_file(it['filename']):
                    tasks.append(threading.Thread(target=self._dubb,args=(it,)))
            if len(tasks) < 1:
                self.has_done+=len(items)
                self._signal(text=f'{config.transobj["kaishipeiyin"]} [{self.has_done}/{self.len}]')
                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.05
                continue
            for t in tasks:
                t.start()
            for t in tasks:
                t.join()
            if str(self.error)=='Invalid response status':
                raise IPLimitExceeded(proxy=self.proxies, msg='403')
            self.has_done += len(items)
            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.05
            self._signal(text=f'{config.transobj["kaishipeiyin"]} [{self.has_done}/{self.len}]')


    def _exec(self) -> None:
        # 防止出错，重试一次
        if self._exit():
            return
        self._item_task()