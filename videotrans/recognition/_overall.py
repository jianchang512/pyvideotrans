import multiprocessing
import threading
import time
from pathlib import Path

from videotrans.configure import config
from videotrans.process._overall import run
from videotrans.recognition._base import BaseRecogn


class FasterAll(BaseRecogn):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raws = []
        self.pidfile = ""
        if self.detect_language[:2].lower() in ['zh', 'ja', 'ko']:
            self.flag.append(" ")
            self.maxlen = int(config.settings['cjk_len'])
        else:
            self.maxlen = int(config.settings['other_len'])
        self.error = ''

    # 获取新进程的结果
    def _get_signal_from_process(self, q: multiprocessing.Queue):
        while not self.has_done:
            if self._exit():
                Path(self.pidfile).unlink(missing_ok=True)
                return
            try:
                if not q.empty():
                    data = q.get_nowait()
                    if self.inst and self.inst.precent < 50:
                        self.inst.precent += 0.1
                    if data:
                        self._signal(text=data['text'], type=data['type'])
            except Exception as e:
                print(e)
            time.sleep(0.2)

    def _exec(self):
        while 1:
            if self._exit():
                Path(self.pidfile).unlink(missing_ok=True)
                return
            if config.model_process is not None:
                self._signal(text="等待另外进程退出")
                time.sleep(1)
                continue
            break

        # 创建队列用于在进程间传递结果
        result_queue = multiprocessing.Queue()
        try:
            self.has_done = False
            threading.Thread(target=self._get_signal_from_process, args=(result_queue,)).start()
            with multiprocessing.Manager() as manager:
                raws = manager.list([])
                err = manager.dict({"msg": ""})
                detect=manager.dict({"langcode":self.detect_language})
                # 创建并启动新进程
                process = multiprocessing.Process(target=run, args=(raws, err,detect), kwargs={
                    "model_name": self.model_name,
                    "is_cuda": self.is_cuda,
                    "detect_language": self.detect_language,
                    "audio_file": self.audio_file,
                    "maxlen": self.maxlen,
                    "flag": self.flag,
                    "join_word_flag": self.join_word_flag,
                    "q": result_queue,
                    "settings": config.settings,
                    "defaulelang": config.defaulelang,
                    "ROOT_DIR": config.ROOT_DIR,
                    "TEMP_DIR": config.TEMP_DIR
                })
                process.start()
                self.pidfile = config.TEMP_DIR + f'/{process.pid}.lock'
                with Path(self.pidfile).open('w', encoding='utf-8') as f:
                    f.write(f'{process.pid}')
                    f.flush()
                # 等待进程执行完毕
                process.join()
                if err['msg']:
                    self.error = str(err['msg'])
                else:
                    if self.detect_language=='auto' and self.inst and  hasattr(self.inst,'set_source_language'):
                        config.logger.info(f'需要自动检测语言，当前检测出的语言为{detect["langcode"]=}')
                        self.detect_language=detect['langcode']
                        self.inst.set_source_language(detect['langcode'])
                    self.raws=self.re_segment_sentences(list(raws))
                try:
                    if process.is_alive():
                        process.terminate()
                except:
                    pass
        except (LookupError,ValueError,AttributeError,ArithmeticError) as e:
            raise
        except Exception as e:        
            raise Exception(f"faster-whisper进程崩溃，请尝试使用openai-whisper模式或查看解决方案 https://pyvideotrans.com/12.html   :{e}")
        finally:
            # 暂停2s，等待exit判断，循环线程退出
            config.model_process = None
            self.has_done = True

        if self.error:
            raise Exception(self.error)
        return self.raws
