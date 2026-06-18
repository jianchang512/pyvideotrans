import multiprocessing, os
import time

from videotrans.configure.config import app_cfg, settings, logger


def _task_worker_wrapper(func, kwargs):
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    # 这里执行真正的任务
    return func(**kwargs)


class AsyncResultFutureWrapper:
    def __init__(self, async_result, pool_executor):
        self.async_result = async_result
        self._pool = pool_executor  # 持有对进程池的引用，用于检查健康状态

    def result(self, timeout=None):
        # 默认总超时 1 小时，或者自定义
        start_time = time.time()
        actual_timeout = timeout if timeout is not None else 3600

        while True:
            # 1. 检查是否已经完成（正常结束或捕获了 Python 异常）
            if self.async_result.ready():
                try:
                    return self.async_result.get(timeout=1)
                except Exception as e:
                    return None, f"Subprocess Error: {str(e)}"

            # 2. 检查进程池是否还健康
            # 如果进程池里所有的工作进程都消失了，或者池被关闭了
            if not self._is_pool_healthy():
                return None, "Subprocess crashed hard (Segmentation Fault/OOM)"

            # 3. 检查是否超时
            if (time.time() - start_time) > actual_timeout:
                return None, "Task timeout (Possible deadlock in C++ layer)"

            # 4. 检查外部退出信号
            if app_cfg.exit_soft:
                return None, "Task interrupted by user"

            # 5. 短暂休眠，防止 CPU 空转
            time.sleep(0.5)

    def _is_pool_healthy(self):
        """检查进程池中的工作进程是否还在存活"""
        try:
            # Pool 的私有属性 _pool 包含了所有工作进程对象 (Process)
            # 虽然访问私有属性略有风险，但在 Python 3.10 中这是检测 Pool 健康最直接的方法
            workers = getattr(self._pool, '_pool', [])
            if not workers:
                return False
            # 只要有一个工作进程是存活的，就认为池还在工作
            return any(w.is_alive() for w in workers)
        except:
            return False

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
        cpu_count = int(os.cpu_count())
        try:
            man_set = int(float(settings.get('process_max', 0)))
        except (ValueError, TypeError):
            man_set = 0
        if man_set > 0:
            # 最小1个
            return int(max(min(man_set, 8, cpu_count), 1))

        import psutil
        mem = psutil.virtual_memory()
        # 最多8个进程,最小1个
        return int(max(min((int(mem.available / (1024 ** 3)) // 4), 8, cpu_count), 1))

    @classmethod
    def get_gpu_process_nums(cls):
        cpu_count = int(os.cpu_count())
        try:
            process_max_gpu = int(float(settings.get('process_max_gpu', 0)))
        except (TypeError, ValueError):
            process_max_gpu = 0

        # 手动设置了gpu进程数量，则优先级最高,例如虽然只有一卡，但显存特别大，可手动设置多个gpu进程
        if process_max_gpu > 0:
            # 最小1个
            return int(max(min(process_max_gpu, 8, cpu_count), 1))

        # 没有显卡 或 没有启用多显卡，则只启动一个gpu进程
        if app_cfg.NVIDIA_GPU_NUMS < 1 or not bool(settings.get('multi_gpus', False)):
            return 1
        # 最小1个
        return int(max(min(app_cfg.NVIDIA_GPU_NUMS, 8, cpu_count), 1))

    @classmethod
    def get_executor_cpu(cls):
        if cls._executor_cpu is None:
            ctx = multiprocessing.get_context('spawn')
            max_workers = cls.get_cpu_process_nums()
            logger.debug(f'CPU进程池:{max_workers=}')
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
            max_workers = cls.get_gpu_process_nums()
            logger.debug(f'GPU进程池:{max_workers=}')
            cls._executor_gpu = ctx.Pool(
                processes=int(max_workers),
                maxtasksperchild=1
            )

        return cls._executor_gpu

    @classmethod
    def submit_task_cpu(cls, func, **kwargs):
        _executor = cls.get_executor_cpu()
        # 使用 error_callback 记录错误日志
        async_result = _executor.apply_async(
            _task_worker_wrapper,
            args=(func, kwargs),
            error_callback=lambda e: logger.error(f"CPU进程池回调异常: {e}")
        )
        return AsyncResultFutureWrapper(async_result, _executor)

    @classmethod
    def submit_task_gpu(cls, func, **kwargs):
        _executor = cls.get_executor_gpu()
        async_result = _executor.apply_async(
            _task_worker_wrapper,
            args=(func, kwargs),
            error_callback=lambda e: logger.error(f"GPU进程池回调异常: {e}")
        )

        return AsyncResultFutureWrapper(async_result, _executor)

    @classmethod
    def shutdown(cls):
        if cls._executor_cpu:
            cls._executor_cpu.close()
            cls._executor_cpu.join()
            cls._executor_cpu = None
        if cls._executor_gpu:
            cls._executor_gpu.close()
            cls._executor_gpu.join()
            cls._executor_gpu = None
