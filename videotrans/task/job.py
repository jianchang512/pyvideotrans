import time
from threading import Thread

from videotrans.configure import config
from videotrans.task._base import BaseTask
from videotrans.util.tools import set_process
import traceback

# 当前 uuid 是否已停止
def task_is_stop(uuid) -> bool:
    if uuid in config.stoped_uuid_set:
        return True
    return False

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
"""


class WorkerPrepare(Thread):
    def __init__(self, *, parent=None):
        super().__init__()

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return
            if len(config.prepare_queue) < 1:
                time.sleep(0.5)
                continue
            try:
                trk: BaseTask = config.prepare_queue.pop(0)
            except:
                continue
            if task_is_stop(trk.uuid):
                continue
            try:

                trk.prepare()
                # 如果需要识别，则插入 recogn_queue队列，否则继续判断翻译队列、配音队列，都不吻合则插入最终队列
                if trk.shoud_recogn:
                    config.regcon_queue.append(trk)
                elif trk.shoud_trans:
                    config.trans_queue.append(trk)
                elif trk.shoud_dubbing:
                    config.dubb_queue.append(trk)
                else:
                    config.assemb_queue.append(trk)
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg=get_msg_from_except(e)
                config.logger.exception(e, exc_info=True)
                set_process(text=f'{config.transobj["yuchulichucuo"]}:{except_msg}:\n' + traceback.format_exc(), type='error', uuid=trk.uuid)


class WorkerRegcon(Thread):
    def __init__(self, *, parent=None):
        super().__init__()

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return

            if len(config.regcon_queue) < 1:
                time.sleep(0.5)
                continue
            trk = config.regcon_queue.pop(0)
            if task_is_stop(trk.uuid):
                continue
            try:
                trk.recogn()
                # 如果需要识翻译,则插入翻译队列，否则就行判断配音队列，都不吻合则插入最终队列
                if trk.shoud_trans:
                    config.trans_queue.append(trk)
                elif trk.shoud_dubbing:
                    config.dubb_queue.append(trk)
                else:
                    config.assemb_queue.append(trk)
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg=get_msg_from_except(e)
                config.logger.exception(e, exc_info=True)
                if trk.cfg.get('recogn_type') is not None:
                    except_msg+=f"[{get_recogn_type(trk.cfg.get('recogn_type'))}]"
                set_process(text=f'{config.transobj["shibiechucuo"]}:{except_msg}:\n' + traceback.format_exc(), type='error', uuid=trk.uuid)


class WorkerTrans(Thread):
    def __init__(self, *, parent=None):
        super().__init__()

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return
            if len(config.trans_queue) < 1:
                time.sleep(0.5)
                continue
            trk = config.trans_queue.pop(0)
            if task_is_stop(trk.uuid):
                continue
            try:
                trk.trans()
                # 如果需要配音，则插入 dubb_queue 队列，否则插入最终队列
                if trk.shoud_dubbing:
                    config.dubb_queue.append(trk)
                else:
                    config.assemb_queue.append(trk)
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg=get_msg_from_except(e)
                if trk.cfg.get('translate_type') is not None:
                    except_msg+=f"[{get_tanslate_type(trk.cfg.get('translate_type'))}]"
                msg = f'{config.transobj["fanyichucuo"]}:{except_msg}:\n' + traceback.format_exc()
                config.logger.exception(e, exc_info=True)
                set_process(text=msg, type='error', uuid=trk.uuid)


class WorkerDubb(Thread):
    def __init__(self, *, parent=None):
        super().__init__()

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return
            if len(config.dubb_queue) < 1:
                time.sleep(0.5)
                continue
            trk = config.dubb_queue.pop(0)
            if task_is_stop(trk.uuid):
                continue
            try:
                trk.dubbing()
                config.align_queue.append(trk)
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg=get_msg_from_except(e)
                if trk.cfg.get('tts_type') is not None:
                    except_msg+=f"[{get_tts_type(trk.cfg.get('tts_type'))}]"
                msg = f'{config.transobj["peiyinchucuo"]}:{except_msg}:\n' + traceback.format_exc()
                config.logger.exception(e, exc_info=True)
                set_process(text=msg, type='error', uuid=trk.uuid)


class WorkerAlign(Thread):
    def __init__(self, *, parent=None):
        super().__init__()

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return
            if len(config.align_queue) < 1:
                time.sleep(0.5)
                continue
            trk = config.align_queue.pop(0)
            if task_is_stop(trk.uuid):
                continue
            try:
                trk.align()
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg=get_msg_from_except(e)
                msg = f'{config.transobj["peiyinchucuo"]}:{except_msg}:' + traceback.format_exc()
                config.logger.exception(e, exc_info=True)
                set_process(text=msg, type='error', uuid=trk.uuid)
            else:
                config.assemb_queue.append(trk)


class WorkerAssemb(Thread):
    def __init__(self, *, parent=None):
        super().__init__()

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return
            if len(config.assemb_queue) < 1:
                time.sleep(0.5)
                continue
            trk = config.assemb_queue.pop(0)
            if task_is_stop(trk.uuid):
                continue
            try:
                trk.assembling()
                trk.task_done()
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg=get_msg_from_except(e)
                msg = f'{config.transobj["hebingchucuo"]}:{except_msg}:' + traceback.format_exc()
                config.logger.exception(e, exc_info=True)
                set_process(text=msg, type='error', uuid=trk.uuid)


def start_thread(parent=None):
    WorkerPrepare(parent=parent).start()
    WorkerRegcon(parent=parent).start()
    WorkerTrans(parent=parent).start()
    WorkerDubb(parent=parent).start()
    WorkerAlign(parent=parent).start()
    WorkerAssemb(parent=parent).start()
