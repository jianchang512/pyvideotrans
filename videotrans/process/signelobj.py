import multiprocessing,os
from concurrent.futures import ProcessPoolExecutor, as_completed


# ==========================================
# 全局单例管理器
# ==========================================
class GlobalProcessManager:
    _executor_cpu = None
    _executor_gpu = None


    @classmethod
    def get_executor_gpu(cls):
        """
        max_workers 设为 1，意味着同一时间只能跑一个 AI 任务。
        """
        if cls._executor_gpu is None:
            ctx = multiprocessing.get_context('spawn')
            # 设为 1 保证显存绝对安全，任务会排队执行
            cls._executor_gpu = ProcessPoolExecutor(max_workers=1, mp_context=ctx)
        return cls._executor_gpu

    @classmethod
    def get_executor_cpu(cls):
        """
        """
        if cls._executor_cpu is None:
            ctx = multiprocessing.get_context('spawn')
            cls._executor_cpu = ProcessPoolExecutor(max_workers=max(2,os.cpu_count()-1), mp_context=ctx)
        return cls._executor_cpu


    @classmethod
    def submit_task_cpu(cls, func, **kwargs):
        _executor=cls.get_executor_cpu()
        return _executor.submit(func, **kwargs)

    def submit_task_gpu(cls, func, **kwargs):
        _executor=cls.get_executor_gpu()
        return _executor.submit(func, **kwargs)



    @classmethod
    def shutdown(cls):
        if cls._executor_cpu:
            cls._executor_cpu.shutdown(wait=True)
        if cls._executor_gpu:
            cls._executor_gpu.shutdown(wait=True)

