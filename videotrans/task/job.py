import time
from PySide6.QtCore import QThread
from videotrans.configure import config
from videotrans.configure.config import tr
from videotrans.task._base import BaseTask
from videotrans.util import tools
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
            if len(config.prepare_queue) < 1:
                time.sleep(0.1)
                continue
            try:
                trk: BaseTask = config.prepare_queue.pop(0)
            except IndexError:
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
                elif trk.shoud_hebing:
                    config.assemb_queue.append(trk)
                else:
                    config.taskdone_queue.append(trk)
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                config.logger.exception(e, exc_info=True)
                set_process(text=f'{tr("yuchulichucuo")}:{except_msg}:\n' + traceback.format_exc(),
                            type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')
                try:
                    del trk
                except NameError:
                    pass


class WorkerRegcon(QThread):
    def __init__(self):
        super().__init__()
        self.name = "SpeechToText"

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return

            if len(config.regcon_queue) < 1:
                time.sleep(0.1)
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
                elif trk.shoud_hebing:
                    config.assemb_queue.append(trk)
                else:
                    config.taskdone_queue.append(trk)
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                config.logger.exception(e, exc_info=True)
                if trk.cfg.recogn_type is not None:
                    except_msg = f"[{get_recogn_type(trk.cfg.recogn_type)}] {except_msg}"
                set_process(text=f'{tr("shibiechucuo")}:{except_msg}:\n' + traceback.format_exc(),
                            type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')
                try:
                    del trk
                except NameError:
                    pass


class WorkerTrans(QThread):
    def __init__(self):
        super().__init__()
        self.name = "TranslationSRT"

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return
            if len(config.trans_queue) < 1:
                time.sleep(0.1)
                continue
            trk = config.trans_queue.pop(0)
            if task_is_stop(trk.uuid):
                continue
            try:
                trk.trans()
                # 如果需要配音，则插入 dubb_queue 队列，否则插入最终队列
                if trk.shoud_dubbing:
                    config.dubb_queue.append(trk)
                elif trk.shoud_hebing:
                    config.assemb_queue.append(trk)
                else:
                    config.taskdone_queue.append(trk)
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                if trk.cfg.translate_type is not None:
                    except_msg = f"[{get_tanslate_type(trk.cfg.translate_type)}] {except_msg}"
                msg = f'{tr("fanyichucuo")}:{except_msg}:\n' + traceback.format_exc()
                config.logger.exception(e, exc_info=True)
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')
                try:
                    del trk
                except NameError:
                    pass


class WorkerDubb(QThread):
    def __init__(self):
        super().__init__()
        self.name = "DubbingSrt"

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return
            if len(config.dubb_queue) < 1:
                time.sleep(0.1)
                continue
            trk = config.dubb_queue.pop(0)
            if task_is_stop(trk.uuid):
                continue
            try:
                # 只要配音，就必须进入 同步对齐队列
                trk.dubbing()
                config.align_queue.append(trk)
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                if trk.cfg.tts_type is not None:
                    except_msg = f"[{get_tts_type(trk.cfg.tts_type)}] {except_msg}"
                msg = f'{tr("peiyinchucuo")}:{except_msg}:\n' + traceback.format_exc()
                config.logger.exception(e, exc_info=True)
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')
                try:
                    del trk
                except NameError:
                    pass


class WorkerAlign(QThread):
    def __init__(self):
        super().__init__()
        self.name = "AlignVieoAudioSrt"

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return
            if len(config.align_queue) < 1:
                time.sleep(0.1)
                continue
            trk = config.align_queue.pop(0)
            if task_is_stop(trk.uuid):
                continue
            try:
                trk.align()
                if trk.shoud_hebing:
                    config.assemb_queue.append(trk)
                else:
                    config.taskdone_queue.append(trk)
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                msg = f'{except_msg}:\n' + traceback.format_exc()
                config.logger.exception(e, exc_info=True)
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')
                try:
                    del trk
                except NameError:
                    pass



class WorkerAssemb(QThread):
    def __init__(self):
        super().__init__()
        self.name = "AssembVideoAudioSrt"

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return
            if len(config.assemb_queue) < 1:
                time.sleep(0.1)
                continue
            trk = config.assemb_queue.pop(0)
            if task_is_stop(trk.uuid):
                continue
            try:
                trk.assembling()
                config.taskdone_queue.append(trk)
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                msg = f'{tr("hebingchucuo")}:{except_msg}:\n' + traceback.format_exc()
                config.logger.exception(e, exc_info=True)
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')
                try:
                    del trk
                except NameError:
                    pass


class WorkerTaskDone(QThread):
    def __init__(self):
        super().__init__()
        self.name = "TaskDone"

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return
            if len(config.taskdone_queue) < 1:
                time.sleep(0.1)
                continue
            trk = config.taskdone_queue.pop(0)
            if task_is_stop(trk.uuid):
                continue
            try:
                trk.task_done()
            except Exception as e:
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                msg = f'{except_msg}:\n' + traceback.format_exc()
                config.logger.exception(e, exc_info=True)
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')
            else:
                tools.send_notification(tr('Succeed'), f"{trk.cfg.basename}")
            finally:
                try:
                    del trk
                except NameError:
                    pass


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
