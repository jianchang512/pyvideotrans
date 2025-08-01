import multiprocessing
import threading
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, ClassVar,Union
from videotrans.configure import config
from videotrans.process._average import run
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

@dataclass
class FasterAvg(BaseRecogn):
    raws: List[Any] = field(default_factory=list, init=False)
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
                        if self.inst and self.inst.status_text and data['type']=='log':
                            self.inst.status_text=data['text']
                        self._signal(text=data['text'], type=data['type'])
            except Exception as e:
                print(e)
            time.sleep(0.5)

    def _exec(self) -> Union[List[Dict], None]:
        while 1:
            if self._exit():
                Path(self.pidfile).unlink(missing_ok=True)
                return
            if config.model_process is not None:
                import glob
                if len(glob.glob(config.TEMP_DIR+'/*.lock'))==0:
                    config.model_process=None
                    break
                self._signal(text="等待另外进程退出")
                time.sleep(1)
                continue
            break

        # 创建队列用于在进程间传递结果
        result_queue = multiprocessing.Queue()
        self.has_done = False

        threading.Thread(target=self._get_signal_from_process, args=(result_queue,)).start()
        try:
            with multiprocessing.Manager() as manager:
                raws = manager.list([])
                err = manager.dict({"msg": ""})
                detect = manager.dict({"langcode": self.detect_language})

                # 创建并启动新进程
                process = multiprocessing.Process(target=run, args=(raws, err,detect), kwargs={
                    "model_name": self.model_name,
                    "is_cuda": self.is_cuda,
                    "detect_language": self.detect_language,
                    "audio_file": self.audio_file,
                    "q": result_queue,
                    "settings": config.settings,
                    "defaulelang": config.defaulelang,
                    "ROOT_DIR": config.ROOT_DIR,
                    "TEMP_DIR": config.TEMP_DIR,
                    "proxy":tools.set_proxy()
                })
                process.start()
                self.pidfile = config.TEMP_DIR + f'/{process.pid}.lock'
                with open(self.pidfile,'w', encoding='utf-8') as f:
                    f.write(f'{process.pid}')
                # 等待进程执行完毕
                process.join()
                if err['msg']:
                    self.error = 'err[msg]='+str(err['msg'])
                elif len(list(raws))<1:
                    self.error = "没有识别到任何说话声" if config.defaulelang=='zh' else "No speech detected"
                else:
                    self.raws = list(raws)
                try:
                    if process.is_alive():
                        process.terminate()
                except:
                    pass
        except (LookupError,ValueError,AttributeError,ArithmeticError) as e:
            config.logger.exception(e, exc_info=True)
            self.error=str(e)
        except Exception as e:
            self.error='_avagel'+str(e)
        finally:
            config.model_process = None
            self.has_done = True
            Path(self.pidfile).unlink(missing_ok=True)

        if self.error:
            raise Exception(self.error)
        return self.raws
