import asyncio
import threading
import time

import edge_tts

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


# asyncio 异步并发

class EdgeTTS(BaseTTS):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def _item_task(self, data_item=None):
        split_queue = [self.queue_tts[i:i + self.dub_nums] for i in range(0, self.len, self.dub_nums)]
        try:
            for items in split_queue:
                retry = 2
                tasks = []
                while retry > 0:
                    retry -= 1
                    try:
                        for it in items:
                            if self._exit():
                                return
                            if not tools.vail_file(it['filename']):
                                communicate_task = edge_tts.Communicate(
                                    text=it["text"], voice=it['role'], rate=self.rate, volume=self.volume,
                                    pitch=self.pitch)
                                tasks.append(communicate_task.save(it['filename']))

                        if len(tasks) < 1:
                            continue

                        # 使用 asyncio.gather 并行执行保存任务
                        await asyncio.gather(*tasks)
                    except Exception:
                        time.sleep(10)
                    else:
                        self.has_done += self.dub_nums
                        if self.inst and self.inst.precent < 80:
                            self.inst.precent += 0.1
                        self._signal(text=f'{config.transobj["kaishipeiyin"]} [{self.has_done}/{self.len}]')
                        break
        except Exception as e:
            self.error = str(e)
            self._signal(text=f'{str(e)}')
            config.logger.exception(e, exc_info=True)

    def _exec(self) -> None:
        # 防止出错，重试一次
        for i in range(2):
            if self._exit():
                return
            try:
                t = threading.Thread(target=self._run_as_async)
                t.start()
                t.join()
                err_num = 0
                for it in self.queue_tts:
                    if not tools.vail_file(it['filename']):
                        err_num += 1
                # 全部失败，不再重试
                if err_num >= self.len:
                    break
                # 有错误则降低并发，重试
                if err_num > 0:
                    config.logger.error(f'存在失败的配音，重试')
                    self.dub_nums = 1
                    self.has_done = 0
                    time.sleep(10)
                else:
                    break
            except Exception as e:
                print(f'eget$$$$$$$$$$$$$$$$${e}')

    def _run_as_async(self):
        # loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(loop)
        try:
            asyncio.run(self._item_task())
            # loop.run_until_complete(self._item_task())
        except Exception as e:
            print(f'############edgetts {e}')
        # finally:
        # 确保事件循环关闭
        # loop.run_until_complete(loop.shutdown_asyncgens())  # 清理异步生成器
        # loop.close()
