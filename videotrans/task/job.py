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
            try:
                trk.recogn()
                # 插入翻译队列
                config.trans_queue.append(trk)
            except Exception as e:
                if trk.init['btnkey'] not in config.unidlist:
                    config.unidlist.append(trk.init['btnkey'])
                msg=f'{config.transobj["shibiechucuo"]}:'+str(e)
                set_process(msg,'error',btnkey=trk.init['btnkey'])
                config.errorlist[trk.init['btnkey']]=msg


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
            try:
                trk.trans()
                config.dubb_queue.append(trk)
            except Exception as e:
                if trk.init['btnkey'] not in config.unidlist:
                    config.unidlist.append(trk.init['btnkey'])
                msg = f'{config.transobj["fanyichucuo"]}:' + str(e)
                set_process(msg, 'error', btnkey=trk.init['btnkey'])
                config.errorlist[trk.init['btnkey']] = msg

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
            try:
                trk.dubbing()
                config.compose_queue.append(trk)
            except Exception as e:
                if trk.init['btnkey'] not in config.unidlist:
                    config.unidlist.append(trk.init['btnkey'])
                msg=f'{config.transobj["peiyinchucuo"]}:'+str(e)
                set_process(msg,'error',btnkey=trk.init['btnkey'])
                config.errorlist[trk.init['btnkey']]=msg

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
            try:
                trk.hebing()
                trk.move_at_end()
                config.errorlist[trk.init['btnkey']]=""
            except Exception as e:
                msg=f'{config.transobj["hebingchucuo"]}:'+str(e)
                set_process(msg,'error',btnkey=trk.init['btnkey'])
                config.errorlist[trk.init['btnkey']]=msg
            finally:
                if trk.init['btnkey'] not in config.unidlist:
                    config.unidlist.append(trk.init['btnkey'])


def start_thread(parent):
    regcon_thread = WorkerRegcon(parent=parent)
    regcon_thread.start()
    trans_thread = WorkerTrans(parent=parent)
    trans_thread.start()
    dubb_thread = WorkerDubb(parent=parent)
    dubb_thread.start()
    compose_thread = WorkerCompose(parent=parent)
    compose_thread.start()