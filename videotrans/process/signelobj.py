import multiprocessing,os
from concurrent.futures import ProcessPoolExecutor, as_completed
from videotrans.configure import config

# ==========================================
# 全局单例管理器
# ==========================================
from videotrans.util.gpus import getset_gpu


class GlobalProcessManager:
    _executor_cpu = None
    _executor_gpu = None



    @classmethod
    def get_cpu_process_nums(cls):
        try:
            man_set=int(float(config.settings.get('process_max',0)))
        except:
            man_set=0
        if man_set>0:
            return min(man_set,8,os.cpu_count())

        import psutil
        mem=psutil.virtual_memory()
        # 最多8个进程,最小2个
        return max( min( (mem.available/(1024**3))//4 , 8, os.cpu_count() ), 2)

    @classmethod
    def get_gpu_process_nums(cls):
        try:
            process_max_gpu=int(float(config.settings.get('process_max_gpu',0)))
        except:
            process_max_gpu=0
        # 手动设置了gpu进程数量，则优先级最高,例如虽然只有一卡，但显存特别大，可手动设置多个gpu进程
        if process_max_gpu>0:
            return min(process_max_gpu,8,os.cpu_count())
        if config.NVIDIA_GPU_NUMS<0:
            getset_gpu()
        # 没有显卡 或 没有启用多显卡，则只启动一个gpu进程
        if  config.NVIDIA_GPU_NUMS<1 or not bool(config.settings.get('multi_gpus',False)):
            return 1
        
        return min(config.NVIDIA_GPU_NUMS,8,os.cpu_count())

    @classmethod
    def get_executor_cpu(cls):
        """
        """
        if cls._executor_cpu is None:
            ctx = multiprocessing.get_context('spawn')
            max_workers=cls.get_cpu_process_nums()
            config.logger.debug(f'CPU进程池:{max_workers=}')
            cls._executor_cpu = ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx)
        return cls._executor_cpu

    @classmethod
    def get_executor_gpu(cls):
        """
        max_workers 设为 1，意味着同一时间只能跑一个 AI 任务。
        """
        if cls._executor_gpu is None:
            ctx = multiprocessing.get_context('spawn')
            max_workers=cls.get_gpu_process_nums()
            config.logger.debug(f'GPU进程池:{max_workers=}')
            cls._executor_gpu = ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx)
        return cls._executor_gpu

    @classmethod
    def submit_task_cpu(cls, func, **kwargs):
        _executor=cls.get_executor_cpu()
        return _executor.submit(func, **kwargs)

    @classmethod
    def submit_task_gpu(cls, func, **kwargs):
        _executor=cls.get_executor_gpu()
        return _executor.submit(func, **kwargs)

    @classmethod
    def shutdown(cls):
        if cls._executor_cpu:
            cls._executor_cpu.shutdown(wait=True)
        if cls._executor_gpu:
            cls._executor_gpu.shutdown(wait=True)

