import multiprocessing,os
from videotrans.configure.config import app_cfg,settings,logger

# ==========================================
# 增加一个包装类：用来兼容调用方对 Future 对象的习惯 (.result())
# ==========================================
class AsyncResultFutureWrapper:
    def __init__(self, async_result):
        self.async_result = async_result

    def result(self, timeout=None):
        # 把 Pool 独有的 .get() 伪装成 Future 的 .result()
        return self.async_result.get(timeout=timeout)
        
    def done(self):
        return self.async_result.ready()


# ==========================================
# 全局单例管理器
# ==========================================


class GlobalProcessManager:
    _executor_cpu = None
    _executor_gpu = None



    @classmethod
    def get_cpu_process_nums(cls):
        cpu_count=int(os.cpu_count())
        try:
            man_set=int(float(settings.get('process_max',0)))
        except:
            man_set=0
        if man_set>0:
            return int(min(man_set,8,cpu_count))

        import psutil
        mem=psutil.virtual_memory()
        # 最多8个进程,最小2个
        return int(max( min( (mem.available/(1024**3))//4 , 8, cpu_count ), 2))

    @classmethod
    def get_gpu_process_nums(cls):
        cpu_count=int(os.cpu_count())
        try:
            process_max_gpu=int(float(settings.get('process_max_gpu',0)))
        except:
            process_max_gpu=0
        # 手动设置了gpu进程数量，则优先级最高,例如虽然只有一卡，但显存特别大，可手动设置多个gpu进程
        if process_max_gpu>0:
            return int(min(process_max_gpu,8,cpu_count))
        if app_cfg.NVIDIA_GPU_NUMS<0:
            return 1
        # 没有显卡 或 没有启用多显卡，则只启动一个gpu进程
        if  app_cfg.NVIDIA_GPU_NUMS<1 or not bool(settings.get('multi_gpus',False)):
            return 1
        
        return int(min(app_cfg.NVIDIA_GPU_NUMS,8,cpu_count))

    @classmethod
    def get_executor_cpu(cls):
        """
        """
        if cls._executor_cpu is None:
            ctx = multiprocessing.get_context('spawn')
            max_workers=cls.get_cpu_process_nums()
            logger.debug(f'CPU进程池:{max_workers=}')
            #cls._executor_cpu = ProcessPoolExecutor(max_workers=int(max_workers), mp_context=ctx)
            cls._executor_cpu = ctx.Pool(
                processes=int(max_workers), 
                maxtasksperchild=1  # <--- CPU 也让它跑完就死，彻底释放物理内存
            )
        return cls._executor_cpu

    @classmethod
    def get_executor_gpu(cls):
        """
        max_workers 设为 1，意味着同一时间只能跑一个 AI 任务。
        """
        if cls._executor_gpu is None:
            ctx = multiprocessing.get_context('spawn')
            max_workers=cls.get_gpu_process_nums()
            logger.debug(f'GPU进程池:{max_workers=}')
            #cls._executor_gpu = ProcessPoolExecutor(max_workers=int(max_workers), mp_context=ctx)
            cls._executor_gpu = ctx.Pool(
                processes=int(max_workers), 
                maxtasksperchild=1
            )

        return cls._executor_gpu

    @classmethod
    def submit_task_cpu(cls, func, **kwargs):
        _executor=cls.get_executor_cpu()
        async_result = _executor.apply_async(func, kwds=kwargs)
        return AsyncResultFutureWrapper(async_result)
        #return _executor.submit(func, **kwargs)

    @classmethod
    def submit_task_gpu(cls, func, **kwargs):
        _executor=cls.get_executor_gpu()
        # Pool 提交任务的方法是 apply_async，且需要指定 kwds 关键字参数
        async_result = _executor.apply_async(func, kwds=kwargs)
        # 返回我们写的包装类，这样主逻辑拿到后依然可以写 future.result()
        return AsyncResultFutureWrapper(async_result)
        #return _executor.submit(func, **kwargs)

    @classmethod
    def shutdown(cls):
        if cls._executor_cpu:
            cls._executor_cpu.close()
            cls._executor_cpu.join()
            cls._executor_cpu = None
            #cls._executor_cpu.shutdown(wait=True)
        if cls._executor_gpu:
            cls._executor_gpu.close()
            cls._executor_gpu.join()
            cls._executor_gpu = None
            #cls._executor_gpu.shutdown(wait=True)

