import multiprocessing
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict,  Union

from videotrans.configure import config
from videotrans.configure.config import tr
from videotrans.process._average import run
from videotrans.recognition._base import BaseRecogn
from videotrans.task.simple_runnable_qt import run_in_threadpool

"""
faster-whisper
内置的本地大模型不重试
"""


@dataclass
class FasterAvg(BaseRecogn):
    pidfile: str = field(default="", init=False)

    def __post_init__(self):
        super().__post_init__()

    # 获取新进程的结果
    def _get_signal_from_process(self, q):
        while not self.has_done:
            if self._exit():
                Path(self.pidfile).unlink(missing_ok=True)
                return
            try:
                if not q.empty():
                    data = q.get_nowait()
                    if data:
                        self._signal(text=data['text'], type=data['type'])
            except Exception:
                pass
            time.sleep(0.1)

    def _exec(self) -> Union[List[Dict], None]:
        while 1:
            if self._exit():return
            if config.model_process is not None:
                import glob
                if len(glob.glob(config.TEMP_DIR + '/*.lock')) == 0:
                    config.model_process = None
                    break
                self._signal(text="wait..")
                time.sleep(0.5)
                continue
            break

        # 创建队列用于在进程间传递结果
        result_queue = multiprocessing.Queue()
        self.has_done = False

        run_in_threadpool(self._get_signal_from_process,result_queue)
        try:
            with multiprocessing.Manager() as manager:
                raws = manager.list([])
                err = manager.dict({"msg": ""})
                detect = manager.dict({"langcode": self.detect_language})

                # 创建并启动新进程
                process = multiprocessing.Process(target=run, args=(raws, err, detect), kwargs={
                    "model_name": self.model_name,
                    "is_cuda": self.is_cuda,
                    "detect_language": self.detect_language,
                    "audio_file": self.audio_file,
                    "q": result_queue,
                    "proxy": self.proxy_str,
                    "TEMP_DIR":config.TEMP_DIR,
                    "defaulelang":config.defaulelang,
                    "settings":config.settings
                })
                process.start()
                self.pidfile = config.TEMP_DIR + f'/{process.pid}.lock'
                with open(self.pidfile, 'w', encoding='utf-8') as f:
                    f.write(f'{process.pid}')
                # 等待进程执行完毕
                process.join()
                if err['msg']:
                    self.error = str(err['msg'])
                self.raws = list(raws)
                try:
                    if process.is_alive():
                        process.terminate()
                except Exception:
                    pass
        except Exception as e:
            self.error =e
        finally:
            config.model_process = None
            self.has_done = True
        if not self.error and len(self.raws)>0:
            return self.raws

        if self.error:
            raise self.error if isinstance(self.error,Exception) else RuntimeError(self.error)
        raise RuntimeError( tr("No speech was detected, please make sure there is human speech in the selected audio/video and that the language is the same as the selected one."))
