import time,shutil
from PySide6.QtCore import QThread
from videotrans.configure import config
from videotrans.configure.config import tr,params,settings,app_cfg,logger
from videotrans.task._base import BaseTask
from videotrans.util import tools, gpus
from videotrans.util.tools import set_process
import traceback
from queue import  Empty, Full
from videotrans.configure._except import get_msg_from_except


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
            if app_cfg.exit_soft:
                return
            try:
                trk: BaseTask = app_cfg.prepare_queue.get(timeout=1)
            except Empty:
                continue
            if trk.uuid in app_cfg.stoped_uuid_set:
                continue
            try:
                trk.prepare()
                # 如果需要识别，则插入 recogn_queue队列，否则继续判断翻译队列、配音队列，都不吻合则插入最终队列
                if trk.shoud_recogn:
                    app_cfg.regcon_queue.put_nowait(trk)
                elif trk.shoud_trans:
                    app_cfg.trans_queue.put_nowait(trk)
                elif trk.shoud_dubbing:
                    app_cfg.dubb_queue.put_nowait(trk)
                elif trk.shoud_hebing:
                    app_cfg.assemb_queue.put_nowait(trk)
                else:
                    app_cfg.taskdone_queue.put_nowait(trk)
            except Exception as e:
                logger.exception(e, exc_info=True)
                except_msg = get_msg_from_except(e)
                detail_back=(traceback.format_exc()).strip()
                if not except_msg:
                    except_msg=detail_back.split("\n")[-1]
                msg=f'{tr("yuchulichucuo")} {except_msg}\n{detail_back}\n{trk.cfg}'
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')



class WorkerRegcon(QThread):
    def __init__(self):
        super().__init__()
        self.name = "SpeechToText"

    def run(self) -> None:
        while 1:
            if app_cfg.exit_soft:
                return


            try:
                trk = app_cfg.regcon_queue.get(timeout=1)
            except Empty:
                continue
            if trk.uuid in app_cfg.stoped_uuid_set:
                logger.debug(f'[job] {trk.uuid=}已停止，执行语音识别阶段 {trk.cfg=}')
                continue
            try:
                logger.debug(f'[job] 进入执行语音识别阶段 {trk.cfg=}')
                trk.recogn()
                app_cfg.diariz_queue.put_nowait(trk)
            except Exception as e:
                logger.exception(e, exc_info=True)                
                except_msg = get_msg_from_except(e)
                detail_back=(traceback.format_exc()).strip()
                if not except_msg:
                    except_msg=detail_back.split("\n")[-1]
                if trk.cfg.recogn_type is not None:
                    except_msg = f"[{get_recogn_type(trk.cfg.recogn_type)}] {except_msg}"
                msg=f"{tr('shibiechucuo')} {except_msg}\n{detail_back}\n{trk.cfg}"
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')


class WorkerDiariz(QThread):
    def __init__(self):
        super().__init__()
        self.name = "DiarizSpeaker"

    def run(self) -> None:
        while 1:
            if app_cfg.exit_soft:
                return


            try:
                trk = app_cfg.diariz_queue.get(timeout=1)
            except Empty:
                continue
            if trk.uuid in app_cfg.stoped_uuid_set:
                continue
            try:
                print(f'进入执行说话人分离阶段')
                trk.diariz()
            except Exception as e:
                logger.exception(e, exc_info=True)
            finally:
                # 如果需要识翻译,则插入翻译队列，否则就行判断配音队列，都不吻合则插入最终队列
                if trk.shoud_trans:
                    app_cfg.trans_queue.put_nowait(trk)
                elif trk.shoud_dubbing:
                    app_cfg.dubb_queue.put_nowait(trk)
                elif trk.shoud_hebing:
                    app_cfg.assemb_queue.put_nowait(trk)
                else:
                    app_cfg.taskdone_queue.put_nowait(trk)



class WorkerTrans(QThread):
    def __init__(self):
        super().__init__()
        self.name = "TranslationSRT"

    def run(self) -> None:
        while 1:
            if app_cfg.exit_soft:
                return

            try:
                trk = app_cfg.trans_queue.get(timeout=1)
            except Empty:
                continue
            if trk.uuid in app_cfg.stoped_uuid_set:
                continue
            try:
                print(f'进入执行字幕翻译阶段')
                trk.trans()
                # 如果需要配音，则插入 dubb_queue 队列，否则插入最终队列
                if trk.shoud_dubbing:
                    app_cfg.dubb_queue.put_nowait(trk)
                elif trk.shoud_hebing:
                    app_cfg.assemb_queue.put_nowait(trk)
                else:
                    app_cfg.taskdone_queue.put_nowait(trk)
            except Exception as e:
                logger.exception(e, exc_info=True)
                except_msg = get_msg_from_except(e)
                detail_back=(traceback.format_exc()).strip()
                if not except_msg:
                    except_msg=detail_back.split("\n")[-1]
                if trk.cfg.translate_type is not None:
                    except_msg = f"[{get_tanslate_type(trk.cfg.translate_type)}] {except_msg}"
                msg = f'{tr("fanyichucuo")} {except_msg}\n{detail_back}\n{trk.cfg}'
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')


class WorkerDubb(QThread):
    def __init__(self):
        super().__init__()
        self.name = "DubbingSrt"

    def run(self) -> None:
        while 1:
            if app_cfg.exit_soft:
                return

            try:
                trk = app_cfg.dubb_queue.get(timeout=1)
            except Empty:
                continue
            if trk.uuid in app_cfg.stoped_uuid_set:
                continue
            try:
                # 只要配音，就必须进入 同步对齐队列
                print(f'进入执行配音阶段')
                trk.dubbing()
                app_cfg.align_queue.put_nowait(trk)
            except Exception as e:
                logger.exception(e, exc_info=True)
                except_msg = get_msg_from_except(e)
                detail_back=(traceback.format_exc()).strip()
                if not except_msg:
                    except_msg=detail_back.split("\n")[-1]
                if trk.cfg.tts_type is not None:
                    except_msg = f"[{get_tts_type(trk.cfg.tts_type)}] {except_msg}"
                msg = f'{tr("peiyinchucuo")} {except_msg}\n{detail_back}\n{trk.cfg}'
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')



class WorkerAlign(QThread):
    def __init__(self):
        super().__init__()
        self.name = "AlignVieoAudioSrt"

    def run(self) -> None:
        while 1:
            if app_cfg.exit_soft:
                return

            try:
                trk = app_cfg.align_queue.get(timeout=1)
            except Empty:
                continue
            
            if trk.uuid in app_cfg.stoped_uuid_set:
                continue
            try:
                print(f'进入执行对齐阶段')
                trk.align()
                if trk.shoud_hebing:
                    app_cfg.assemb_queue.put_nowait(trk)
                else:
                    app_cfg.taskdone_queue.put_nowait(trk)
            except Exception as e:
                logger.exception(e, exc_info=True)
                except_msg = get_msg_from_except(e)
                detail_back=(traceback.format_exc()).strip()
                if not except_msg:
                    except_msg=detail_back.split("\n")[-1]
                msg = f'{except_msg}\n{detail_back}\n{trk.cfg}'
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
            if app_cfg.exit_soft:
                return

            try:
                trk = app_cfg.assemb_queue.get(timeout=1)
            except Empty:
                continue
            if trk.uuid in app_cfg.stoped_uuid_set:
                continue
            try:
                print(f'进入执行合并阶段')
                trk.assembling()
                app_cfg.taskdone_queue.put_nowait(trk)
            except Exception as e:
                logger.exception(e, exc_info=True)
                except_msg = get_msg_from_except(e)
                detail_back=(traceback.format_exc()).strip()
                if not except_msg:
                    except_msg=detail_back.split("\n")[-1]
                msg = f'{tr("hebingchucuo")} {except_msg}\n{detail_back}\n{trk.cfg}'
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')





class WorkerTaskDone(QThread):
    def __init__(self):
        super().__init__()
        self.name = "TaskDone"

    def run(self) -> None:
        while 1:
            if app_cfg.exit_soft:
                return

            try:
                trk = app_cfg.taskdone_queue.get(timeout=1)
            except Empty:
                continue
            if trk.uuid in app_cfg.stoped_uuid_set:
                continue
            try:
                print(f'进入执行完成阶段')
                trk.task_done()
            except Exception as e:
                logger.exception(e, exc_info=True)
                except_msg = get_msg_from_except(e)
                detail_back=(traceback.format_exc()).strip()
                if not except_msg:
                    except_msg=detail_back.split("\n")[-1]
                msg = f'{except_msg}\n{detail_back}\n{trk.cfg}'
                set_process(text=msg, type='error', uuid=trk.uuid)
                tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')
            finally:
                try:
                    shutil.rmtree(trk.cfg.cache_folder)
                except:
                    pass
                
def start_thread():
    gpus.getset_gpu()
    task_nums=1
    # 存在可用显卡时，进一步判断应该启动几个相关线程
    if app_cfg.NVIDIA_GPU_NUMS>0:
        try:
            process_max_gpu=int(float(settings.get('process_max_gpu',0)))
        except:
            process_max_gpu=0
        # 如果手动设置了gpu进程数量
        if process_max_gpu>0:
            task_nums=process_max_gpu
        elif app_cfg.NVIDIA_GPU_NUMS>1 and bool(settings.get('multi_gpus')):
            # 显卡数量真的大于1 并且 启用了多显卡，
            task_nums=2 if app_cfg.NVIDIA_GPU_NUMS<4 else 4
        print(f'{process_max_gpu=}')
        print(f'multi_gpus={settings.get("multi_gpus")}')
    print(f'Concurrent {task_nums=}')
    print(f'process_max={settings.get("process_max")}')
    # 定义每个工种需要的线程数量
    worker_config = {
        WorkerPrepare: task_nums,  # 准备工作
        WorkerRegcon: task_nums,   # 语音识别
        WorkerDiariz: task_nums,
        WorkerTrans: 1,
        WorkerDubb: 1,
        WorkerAlign: 1,
        WorkerAssemb: task_nums,
        WorkerTaskDone: 1,
    }

    workers = []

    for worker_cls, count in worker_config.items():
        for i in range(count):
            # 实例化
            worker = worker_cls()
            if count > 1:
                worker.name = f"{worker.name}-{i+1}"
                print(f'{worker.name=}')

            worker.start()
            workers.append(worker)

    print(f"start {len(workers)} jobs")
    return workers