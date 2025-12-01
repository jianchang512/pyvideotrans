from PySide6.QtCore import QRunnable, QThreadPool

# 通用的 QRunnable 类
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
            print(e)

# 通用的线程池运行函数
def run_in_threadpool(func, *args, **kwargs):
    runnable = SimpleRunnable(func, *args, **kwargs)
    QThreadPool.globalInstance().start(runnable)