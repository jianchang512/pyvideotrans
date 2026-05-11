import shutil
from PySide6.QtCore import QThread
from videotrans.configure.config import tr, params, settings, app_cfg, logger
from videotrans.task._base import BaseTask
from videotrans.util import tools, gpus
from videotrans.util.tools import set_process
import traceback
from queue import Empty, Full
from videotrans.configure._except import get_msg_from_except


def _get_type_name(type_index, name_list):
    if type_index is None or type_index >= len(name_list):
        return '-'
    return name_list[type_index]


def get_recogn_type(type_index=None):
    from videotrans.recognition import RECOGN_NAME_LIST
    return _get_type_name(type_index, RECOGN_NAME_LIST)


def get_tanslate_type(type_index=None):
    from videotrans.translator import TRANSLASTE_NAME_LIST
    return _get_type_name(type_index, TRANSLASTE_NAME_LIST)


def get_tts_type(type_index=None):
    from videotrans.tts import TTS_NAME_LIST
    return _get_type_name(type_index, TTS_NAME_LIST)


class BaseWorker(QThread):
    """
    工作线程基类：统一处理 while 1 循环、队列读取、软退出判断以及异常捕获和上报逻辑。
    """

    def __init__(self, name: str, queue):
        super().__init__()
        self.name = name
        self.queue = queue

    def run(self) -> None:
        while True:
            if app_cfg.exit_soft:
                return

            try:
                trk = self.queue.get(timeout=1)
            except Empty:
                continue

            if trk.uuid in app_cfg.stoped_uuid_set:
                logger.debug(f'[job] {trk.uuid=}已停止，跳过阶段 {self.name} {trk.cfg=}')
                continue

            try:
                # 执行具体的业务逻辑和队列路由
                self.process_task(trk)
            except Exception as e:
                self.handle_error(e, trk)

    def process_task(self, trk):
        """子类必须实现：具体的执行逻辑和下一步队列路由"""
        raise NotImplementedError

    def handle_error(self, e, trk):
        """统一的错误处理逻辑"""
        trk.set_end()
        logger.exception(e, exc_info=True)
        except_msg = get_msg_from_except(e)
        detail_back = traceback.format_exc().strip()
        if not except_msg:
            except_msg = detail_back.split("\n")[-1]

        # 获取子类可能自定义的错误前缀 (如识别引擎名称、动作名称)
        prefix = self.get_error_prefix(trk)
        if prefix:
            except_msg = f"{prefix} {except_msg}"

        msg = f'{except_msg}\n{detail_back}\n{trk.cfg}'
        trk.signal(text=msg, type='error', uuid=trk.uuid)
        tools.send_notification(f'Error:{e}', f'{trk.cfg.basename}')

        # 允许子类在出错时进行额外的清理工作
        self.cleanup_on_error(trk)

    def get_error_prefix(self, trk) -> str:
        """默认没有错误前缀，子类可按需覆盖"""
        return ""

    def cleanup_on_error(self, trk):
        """默认无清理动作，子类可按需覆盖"""
        pass


class WorkerPrepare(BaseWorker):
    def __init__(self):
        super().__init__("PrepareVideo", app_cfg.prepare_queue)

    def get_error_prefix(self, trk):
        return tr("yuchulichucuo")

    def process_task(self, trk):
        trk.prepare()
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


class WorkerRegcon(BaseWorker):
    def __init__(self):
        super().__init__("SpeechToText", app_cfg.regcon_queue)

    def get_error_prefix(self, trk):
        if trk.cfg.recogn_type is not None:
            return f"{tr('shibiechucuo')}[{get_recogn_type(trk.cfg.recogn_type)}]"
        return tr('shibiechucuo')

    def process_task(self, trk):
        logger.debug(f'[job] 进入执行语音识别阶段 {trk.cfg=}')
        trk.recogn()
        app_cfg.diariz_queue.put_nowait(trk)


class WorkerDiariz(BaseWorker):
    def __init__(self):
        super().__init__("DiarizSpeaker", app_cfg.diariz_queue)

    def process_task(self, trk):
        try:
            # 注意：原代码中 diariz 报错并不阻断流程，而是继续往下走，所以在这里内部 catch
            trk.diariz()
        except Exception as e:
            logger.exception(e, exc_info=True)

        if trk.shoud_trans:
            app_cfg.trans_queue.put_nowait(trk)
        elif trk.shoud_dubbing:
            app_cfg.dubb_queue.put_nowait(trk)
        elif trk.shoud_hebing:
            app_cfg.assemb_queue.put_nowait(trk)
        else:
            app_cfg.taskdone_queue.put_nowait(trk)


class WorkerTrans(BaseWorker):
    def __init__(self):
        super().__init__("TranslationSRT", app_cfg.trans_queue)

    def get_error_prefix(self, trk):
        if trk.cfg.translate_type is not None:
            return f"{tr('fanyichucuo')} [{get_tanslate_type(trk.cfg.translate_type)}]"
        return tr("fanyichucuo")

    def process_task(self, trk):
        trk.trans()
        if trk.shoud_dubbing:
            app_cfg.dubb_queue.put_nowait(trk)
        elif trk.shoud_hebing:
            app_cfg.assemb_queue.put_nowait(trk)
        else:
            app_cfg.taskdone_queue.put_nowait(trk)


class WorkerDubb(BaseWorker):
    def __init__(self):
        super().__init__("DubbingSrt", app_cfg.dubb_queue)

    def get_error_prefix(self, trk):
        if trk.cfg.tts_type is not None:
            return f"{tr('peiyinchucuo')} [{get_tts_type(trk.cfg.tts_type)}]"
        return tr("peiyinchucuo")

    def process_task(self, trk):
        trk.dubbing()
        app_cfg.align_queue.put_nowait(trk)


class WorkerAlign(BaseWorker):
    def __init__(self):
        super().__init__("AlignVieoAudioSrt", app_cfg.align_queue)

    def process_task(self, trk):
        trk.align()
        if hasattr(trk, 'recogn2pass'):
            app_cfg.regcon2_queue.put_nowait(trk)
        elif trk.shoud_hebing:
            app_cfg.assemb_queue.put_nowait(trk)
        else:
            app_cfg.taskdone_queue.put_nowait(trk)

    def cleanup_on_error(self, trk):
        # 对齐失败时的专属清理逻辑
        try:
            shutil.rmtree(trk.cfg.cache_folder, ignore_errors=True)
        except Exception:
            pass


class WorkerRegcon2Pass(BaseWorker):
    def __init__(self):
        super().__init__("SpeechToText2", app_cfg.regcon2_queue)

    def get_error_prefix(self, trk):
        return tr("Secondary speech recognition of dubbing files")

    def process_task(self, trk):
        trk.recogn2pass()
        if trk.shoud_hebing:
            app_cfg.assemb_queue.put_nowait(trk)
        else:
            app_cfg.taskdone_queue.put_nowait(trk)


class WorkerAssemb(BaseWorker):
    def __init__(self):
        super().__init__("AssembVideoAudioSrt", app_cfg.assemb_queue)

    def get_error_prefix(self, trk):
        return tr("hebingchucuo")

    def process_task(self, trk):
        trk.assembling()
        app_cfg.taskdone_queue.put_nowait(trk)


class WorkerTaskDone(BaseWorker):
    def __init__(self):
        super().__init__("TaskDone", app_cfg.taskdone_queue)

    def process_task(self, trk):
        trk.task_done()


def start_thread():
    gpus.getset_gpu()
    task_nums = 1
    # 存在可用显卡时，进一步判断应该启动几个相关线程
    if app_cfg.NVIDIA_GPU_NUMS > 0:
        try:
            process_max_gpu = int(float(settings.get('process_max_gpu', 0)))
        except:
            process_max_gpu = 1
        # 如果手动设置了gpu进程数量
        if process_max_gpu > 0:
            task_nums = process_max_gpu
        elif app_cfg.NVIDIA_GPU_NUMS > 1 and bool(settings.get('multi_gpus')):
            # 显卡数量真的大于1 并且 启用了多显卡，
            task_nums = 2 if app_cfg.NVIDIA_GPU_NUMS < 4 else 4
        logger.debug(f'{process_max_gpu=}')
        logger.debug(f'is_multi_gpus={settings.get("multi_gpus")}')
    logger.debug(f'Concurrent {task_nums=}')
    logger.debug(f'process_max={settings.get("process_max")}')
    # 定义每个工种需要的线程数量
    worker_config = {
        WorkerPrepare: task_nums,  # 准备工作
        WorkerRegcon: task_nums,  # 语音识别
        WorkerDiariz: task_nums,
        WorkerTrans: 1,
        WorkerDubb: 1,
        WorkerRegcon2Pass: 1,
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
                worker.name = f"{worker.name}-{i + 1}"

            worker.start()
            workers.append(worker)

    logger.debug(f"start {len(workers)} jobs")
    return workers
