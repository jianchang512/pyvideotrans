import time

from PySide6.QtCore import QThread

from videotrans.configure import config
from videotrans.util.tools import set_process


class WorkerRegcon(QThread):
    def __init__(self, *,parent=None):
        super().__init__(parent=parent)
    def run(self) -> None:
        while 1:
            if config.exit_soft or config.current_status!='ing':
                return
            if len(config.regcon_queue)<1:
                time.sleep(0.5)
                continue
            trk=config.regcon_queue.pop(0)
            is_recogn=trk.is_recogn()
            # 不需要识别
            if not is_recogn[0] or is_recogn[1]:
                config.trans_queue.append(trk)
                continue
            try:
                trk.recogn()
                # 插入翻译队列
                config.trans_queue.append(trk)
            except Exception as e:
                if trk.btnkey not in config.unidlist:
                    config.unidlist.append(trk.btnkey)
                msg=f'{config.transobj["shibiechucuo"]}:'+str(e)
                set_process(msg,'error',btnkey=trk.btnkey)
                config.errorlist[trk.btnkey]=msg


class WorkerTrans(QThread):
    def __init__(self, *,parent=None):
        super().__init__(parent=parent)
    def run(self) -> None:
        while 1:
            if config.exit_soft or config.current_status!='ing':
                return
            if len(config.trans_queue)<1:
                time.sleep(0.5)
                continue
            trk=config.trans_queue.pop(0)
            # 需要识别但识别未完成
            is_recogn=trk.is_recogn()
            if is_recogn[0] and not is_recogn[1]:
                config.trans_queue.append(trk)
                time.sleep(0.5)
                continue

            is_trans=trk.is_trans()
            if not is_trans[0] or is_trans[1]:
                # 不需要翻译，则插入配音队列
                config.dubb_queue.append(trk)
                time.sleep(0.5)
                continue
            try:
                trk.trans()
                config.dubb_queue.append(trk)
            except Exception as e:
                if trk.btnkey not in config.unidlist:
                    config.unidlist.append(trk.btnkey)
                msg = f'{config.transobj["fanyichucuo"]}:' + str(e)
                set_process(msg, 'error', btnkey=trk.btnkey)
                config.errorlist[trk.btnkey] = msg

class WorkerDubb(QThread):
    def __init__(self, *,parent=None):
        super().__init__(parent=parent)
    def run(self) -> None:
        while 1:
            if config.exit_soft or config.current_status!='ing':
                return
            if len(config.dubb_queue)<1:
                time.sleep(0.5)
                continue
            trk=config.dubb_queue.pop(0)
            # 需要识别但识别未完成
            is_recogn=trk.is_recogn()
            if is_recogn[0] and not is_recogn[1]:
                config.dubb_queue.append(trk)
                time.sleep(0.5)
                continue
            # 需要翻译但未完成
            is_trans=trk.is_trans()
            if is_trans[0] and not is_trans[1]:
                config.trans_queue.append(trk)
                time.sleep(0.5)
                continue

            is_dubb=trk.is_dubb()
            if not is_dubb[0] or is_dubb[1]:
                # 不需要翻译插入合成
                config.compose_queue.append(trk)
                time.sleep(0.5)
                continue
            try:
                trk.dubbing()
                config.compose_queue.append(trk)
            except Exception as e:
                if trk.btnkey not in config.unidlist:
                    config.unidlist.append(trk.btnkey)
                msg=f'{config.transobj["peiyinchucuo"]}:'+str(e)
                set_process(msg,'error',btnkey=trk.btnkey)
                config.errorlist[trk.btnkey]=msg

class WorkerCompose(QThread):
    def __init__(self, *,parent=None):
        super().__init__(parent=parent)
    def run(self) -> None:
        while 1:
            if config.exit_soft or config.current_status!='ing':
                return
            if len(config.compose_queue)<1:
                time.sleep(0.5)
                continue
            trk=config.compose_queue.pop(0)
            # 需要识别但识别未完成
            is_recogn = trk.is_recogn()
            if is_recogn[0] and not is_recogn[1]:
                config.compose_queue.append(trk)
                time.sleep(0.5)
                continue
            # 需要翻译但未完成
            is_trans = trk.is_trans()
            if is_trans[0] and not is_trans[1]:
                config.compose_queue.append(trk)
                time.sleep(0.5)
                continue
            # 需要配音但未完成
            is_dubb = trk.is_dubb()
            if is_dubb[0] and not is_dubb[1]:
                config.compose_queue.append(trk)
                time.sleep(0.5)
                continue

            try:
                trk.hebing()
                trk.move_at_end()
                config.errorlist[trk.btnkey]=""
            except Exception as e:
                msg=f'{config.transobj["hebingchucuo"]}:'+str(e)
                set_process(msg,'error',btnkey=trk.btnkey)
                config.errorlist[trk.btnkey]=msg
            finally:
                if trk.btnkey not in config.unidlist:
                    config.unidlist.append(trk.btnkey)


def start_thread(parent):
    regcon_thread = WorkerRegcon(parent=parent)
    regcon_thread.start()
    trans_thread = WorkerTrans(parent=parent)
    trans_thread.start()
    dubb_thread = WorkerDubb(parent=parent)
    dubb_thread.start()
    compose_thread = WorkerCompose(parent=parent)
    compose_thread.start()