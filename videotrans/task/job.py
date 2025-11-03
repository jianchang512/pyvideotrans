import time
from PySide6.QtCore import QThread
from videotrans.configure import config
from videotrans.configure.config import tr, logs
from videotrans.task._base import BaseTask
from videotrans.util import tools
from videotrans.util.tools import set_process
import traceback
from queue import  Empty, Full



def get_recogn_type(type_index=None):
    from videotrans.recognition import RECOGN_NAME_LIST
    if type_index is None or type_index >= len(RECOGN_NAME_LIST):
        return '-'
    return RECOGN_NAME_LIST[type_index]


def get_tanslate_type(type_index=None):
    from videotrans.translator import TRANSLASTE_NAME_LIST
    if type_index is None or type_index >= len(TRANSLASTE_NAME_LIST):
        return '-'
    return TRANSLASTE_NAME_LIST[type_index]


def get_tts_type(type_index=None):
    from videotrans.tts import TTS_NAME_LIST
    if type_index is None or type_index >= len(TTS_NAME_LIST):
        return '-'
    return TTS_NAME_LIST[type_index]


# 预处理线程，所有任务均需要执行，也是入口
"""
prepare_queue
regcon_queue
trans_queue
dubb_queue
align_queue
assemb_queue
taskdone_queue
"""


class WorkerPrepare(QThread):
    def __init__(self):
        super().__init__()
        self.name = "PrepareVideo"

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return
            if  config.prepare_queue.empty():
                time.sleep(0.1)
                continue
            try:
                trk: BaseTask = config.prepare_queue.get_nowait()
            except Empty:
                continue
            if trk.uuid in config.stoped_uuid_set:
                continue
            try:
                trk.prepare()
                # 如果需要识别，则插入 recogn_queue队列，否则继续判断翻译队列、配音队列，都不吻合则插入最终队列
                if trk.shoud_recogn:
                    config.regcon_queue.put_nowait(trk)
                elif trk.shoud_trans:
                    config.trans_queue.put_nowait(trk)
                elif trk.shoud_dubbing:
                    config.dubb_queue.put_nowait(trk)
                elif trk.shoud_hebing:
                    config.assemb_queue.put_nowait(trk)
                else:
                    config.taskdone_queue.put_nowait(trk)
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                logs(e, level="except")
                set_process(text=f'{tr("yuchulichucuo")}:{except_msg}:\n' + traceback.format_exc(),
                            type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')



class WorkerRegcon(QThread):
    def __init__(self):
        super().__init__()
        self.name = "SpeechToText"

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return

            if config.regcon_queue.empty():
                time.sleep(0.1)
                continue
            try:
                trk = config.regcon_queue.get_nowait()
            except Empty:
                continue
            if trk.uuid in config.stoped_uuid_set:
                continue
            try:
                trk.recogn()
                # 如果需要识翻译,则插入翻译队列，否则就行判断配音队列，都不吻合则插入最终队列
                if trk.shoud_trans:
                    config.trans_queue.put_nowait(trk)
                elif trk.shoud_dubbing:
                    config.dubb_queue.put_nowait(trk)
                elif trk.shoud_hebing:
                    config.assemb_queue.put_nowait(trk)
                else:
                    config.taskdone_queue.put_nowait(trk)
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                logs(e, level="except")
                if trk.cfg.recogn_type is not None:
                    except_msg = f"[{get_recogn_type(trk.cfg.recogn_type)}] {except_msg}"
                set_process(text=f'{tr("shibiechucuo")}:{except_msg}:\n' + traceback.format_exc(),
                            type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')



class WorkerTrans(QThread):
    def __init__(self):
        super().__init__()
        self.name = "TranslationSRT"

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return
            if  config.trans_queue.empty():
                time.sleep(0.1)
                continue
            try:    
                trk = config.trans_queue.get_nowait()
            except Empty:
                continue
            if trk.uuid in config.stoped_uuid_set:
                continue
            try:
                trk.trans()
                # 如果需要配音，则插入 dubb_queue 队列，否则插入最终队列
                if trk.shoud_dubbing:
                    config.dubb_queue.put_nowait(trk)
                elif trk.shoud_hebing:
                    config.assemb_queue.put_nowait(trk)
                else:
                    config.taskdone_queue.put_nowait(trk)
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                if trk.cfg.translate_type is not None:
                    except_msg = f"[{get_tanslate_type(trk.cfg.translate_type)}] {except_msg}"
                msg = f'{tr("fanyichucuo")}:{except_msg}:\n' + traceback.format_exc()
                logs(e, level="except")
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')


class WorkerDubb(QThread):
    def __init__(self):
        super().__init__()
        self.name = "DubbingSrt"

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return
            if  config.dubb_queue.empty():
                time.sleep(0.1)
                continue
            try:
                trk = config.dubb_queue.get_nowait()
            except Empty:
                continue
            if trk.uuid in config.stoped_uuid_set:
                continue
            try:
                # 只要配音，就必须进入 同步对齐队列
                trk.dubbing()
                config.align_queue.put_nowait(trk)
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                if trk.cfg.tts_type is not None:
                    except_msg = f"[{get_tts_type(trk.cfg.tts_type)}] {except_msg}"
                msg = f'{tr("peiyinchucuo")}:{except_msg}:\n' + traceback.format_exc()
                logs(e, level="except")
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')



class WorkerAlign(QThread):
    def __init__(self):
        super().__init__()
        self.name = "AlignVieoAudioSrt"

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return
            if config.align_queue.empty():
                time.sleep(0.1)
                continue
            try:
                trk = config.align_queue.get_nowait()
            except Empty:
                continue
            
            if trk.uuid in config.stoped_uuid_set:
                continue
            try:
                trk.align()
                if trk.shoud_hebing:
                    config.assemb_queue.put_nowait(trk)
                else:
                    config.taskdone_queue.put_nowait(trk)
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                msg = f'{except_msg}:\n' + traceback.format_exc()
                logs(e, level="except")
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')




class WorkerAssemb(QThread):
    def __init__(self):
        super().__init__()
        self.name = "AssembVideoAudioSrt"

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return
            if config.assemb_queue.empty():
                time.sleep(0.1)
                continue
            try:
                trk = config.assemb_queue.get_nowait()
            except Empty:
                continue
            if trk.uuid in config.stoped_uuid_set:
                continue
            try:
                trk.assembling()
                config.taskdone_queue.put_nowait(trk)
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                msg = f'{tr("hebingchucuo")}:{except_msg}:\n' + traceback.format_exc()
                logs(e, level="except")
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')



class WorkerTaskDone(QThread):
    def __init__(self):
        super().__init__()
        self.name = "TaskDone"

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return
            if config.taskdone_queue.empty():
                time.sleep(0.1)
                continue
            try:
                trk = config.taskdone_queue.get_nowait()
            except Empty:
                continue
            if trk.uuid in config.stoped_uuid_set:
                continue
            try:
                trk.task_done()
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                msg = f'{except_msg}:\n' + traceback.format_exc()
                logs(e, level="except")
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')
            else:
                tools.send_notification(tr('Succeed'), f"{trk.cfg.basename}")
            


def start_thread():
    workers = [
        WorkerPrepare(),
        WorkerRegcon(),
        WorkerTrans(),
        WorkerDubb(),
        WorkerAlign(),
        WorkerAssemb(),
        WorkerTaskDone(),
    ]
    for worker in workers:
        worker.start()

    # 返回创建的线程列表
    return workers
