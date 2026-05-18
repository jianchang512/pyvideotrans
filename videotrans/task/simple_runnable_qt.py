from PySide6.QtCore import QRunnable, QThreadPool
from videotrans import logger


class SimpleRunnable(QRunnable):
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.func(*self.args, **self.kwargs)
        except Exception as e:
            logger.exception(f'后台qt线程执行任务失败:{self.args=},{self.kwargs=},{e}',exc_info=True)

# 通用的线程池运行函数
def run_in_threadpool(func, *args, **kwargs):
    runnable = SimpleRunnable(func, *args, **kwargs)
    QThreadPool.globalInstance().start(runnable)