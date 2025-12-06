import time,shutil
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
            if  config.prepare_queue.empty() and config.prepare_queue.qsize()<1:
                time.sleep(0.1)
                continue
            try:
                trk: BaseTask = config.prepare_queue.get_nowait()
            except Empty:
                print('异常？')
                continue
            if trk.uuid in config.stoped_uuid_set:
                continue
            try:
                print(f'进入执行分离阶段 {trk.shoud_recogn=}')
                trk.prepare()
                print(f'应该送入语音识别队列 {trk.shoud_recogn=}')
                
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
                logs(e, level="except")
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                msg=f'{tr("yuchulichucuo")}:{except_msg}:\n' + traceback.format_exc()+f"\n{trk.cfg}"
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')



class WorkerRegcon(QThread):
    def __init__(self):
        super().__init__()
        self.name = "SpeechToText"

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return

            if config.regcon_queue.empty() and config.regcon_queue.qsize()<1:
                time.sleep(0.1)
                continue
            
            try:
                trk = config.regcon_queue.get_nowait()
            except Empty:
                continue
            if trk.uuid in config.stoped_uuid_set:
                continue
            try:
                print(f'进入执行语音识别阶段')
                trk.recogn()
                config.diariz_queue.put_nowait(trk)
            except Exception as e:
                logs(e, level="except")
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                if trk.cfg.recogn_type is not None:
                    except_msg = f"[{get_recogn_type(trk.cfg.recogn_type)}] {except_msg}"
                msg=f'{tr("shibiechucuo")}:{except_msg}:\n' + traceback.format_exc()+f"\n{trk.cfg}"
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')


class WorkerDiariz(QThread):
    def __init__(self):
        super().__init__()
        self.name = "DiarizSpeaker"

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return

            if config.diariz_queue.empty() and config.diariz_queue.qsize()<1:
                time.sleep(0.1)
                continue
            
            try:
                trk = config.diariz_queue.get_nowait()
            except Empty:
                continue
            if trk.uuid in config.stoped_uuid_set:
                continue
            try:
                print(f'进入执行说话人分离阶段')
                trk.diariz()
            except Exception as e:
                logs(e, level="except")
            finally:
                # 如果需要识翻译,则插入翻译队列，否则就行判断配音队列，都不吻合则插入最终队列
                if trk.shoud_trans:
                    config.trans_queue.put_nowait(trk)
                elif trk.shoud_dubbing:
                    config.dubb_queue.put_nowait(trk)
                elif trk.shoud_hebing:
                    config.assemb_queue.put_nowait(trk)
                else:
                    config.taskdone_queue.put_nowait(trk)



class WorkerTrans(QThread):
    def __init__(self):
        super().__init__()
        self.name = "TranslationSRT"

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return
            if  config.trans_queue.empty()  and config.trans_queue.qsize()<1:
                time.sleep(0.1)
                continue
            try:    
                trk = config.trans_queue.get_nowait()
            except Empty:
                continue
            if trk.uuid in config.stoped_uuid_set:
                continue
            try:
                print(f'进入执行字幕翻译阶段')
                trk.trans()
                # 如果需要配音，则插入 dubb_queue 队列，否则插入最终队列
                if trk.shoud_dubbing:
                    config.dubb_queue.put_nowait(trk)
                elif trk.shoud_hebing:
                    config.assemb_queue.put_nowait(trk)
                else:
                    config.taskdone_queue.put_nowait(trk)
            except Exception as e:
                logs(e, level="except")
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                if trk.cfg.translate_type is not None:
                    except_msg = f"[{get_tanslate_type(trk.cfg.translate_type)}] {except_msg}"
                msg = f'{tr("fanyichucuo")}:{except_msg}:\n' + traceback.format_exc()+f"\n{trk.cfg}"
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
            if  config.dubb_queue.empty() and config.dubb_queue.qsize()<1:
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
                print(f'进入执行配音阶段')
                trk.dubbing()
                config.align_queue.put_nowait(trk)
            except Exception as e:
                logs(e, level="except")
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                if trk.cfg.tts_type is not None:
                    except_msg = f"[{get_tts_type(trk.cfg.tts_type)}] {except_msg}"
                msg = f'{tr("peiyinchucuo")}:{except_msg}:\n' + traceback.format_exc()+f"\n{trk.cfg}"
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
            if config.align_queue.empty() and config.align_queue.qsize()<1:
                time.sleep(0.1)
                continue
            try:
                trk = config.align_queue.get_nowait()
            except Empty:
                continue
            
            if trk.uuid in config.stoped_uuid_set:
                continue
            try:
                print(f'进入执行对齐阶段')
                trk.align()
                if trk.shoud_hebing:
                    config.assemb_queue.put_nowait(trk)
                else:
                    config.taskdone_queue.put_nowait(trk)
            except Exception as e:
                logs(e, level="except")
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                msg = f'{except_msg}:\n' + traceback.format_exc()+f"\n{trk.cfg}"
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')
                try:
                    shutil.rmtree(trk.cfg.cache_folder, ignore_errors=True)
                except Exception:
                    pass




class WorkerAssemb(QThread):
    def __init__(self):
        super().__init__()
        self.name = "AssembVideoAudioSrt"

    def run(self) -> None:
        while 1:
            if config.exit_soft:
                return
            if config.assemb_queue.empty() and config.assemb_queue.qsize()<1:
                time.sleep(0.1)
                continue
            try:
                trk = config.assemb_queue.get_nowait()
            except Empty:
                continue
            if trk.uuid in config.stoped_uuid_set:
                continue
            try:
                print(f'进入执行合并阶段')
                trk.assembling()
                config.taskdone_queue.put_nowait(trk)
            except Exception as e:
                logs(e, level="except")
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                msg = f'{tr("hebingchucuo")}:{except_msg}:\n' + traceback.format_exc()+f"\n{trk.cfg}"
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
            if config.taskdone_queue.empty() and config.taskdone_queue.qsize()<1:
                time.sleep(0.1)
                continue
            try:
                trk = config.taskdone_queue.get_nowait()
            except Empty:
                continue
            if trk.uuid in config.stoped_uuid_set:
                continue
            try:
                print(f'进入执行完成阶段')
                trk.task_done()
            except Exception as e:
                logs(e, level="except")
                from videotrans.configure._except import get_msg_from_except
                except_msg = get_msg_from_except(e)
                msg = f'{except_msg}:\n' + traceback.format_exc()+f"\n{trk.cfg}"
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')
            finally:
                try:
                    shutil.rmtree(trk.cfg.cache_folder)
                except:
                    pass
                
            


def start_thread():
    workers = [
        WorkerPrepare(),
        WorkerRegcon(),
        WorkerDiariz(),
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
