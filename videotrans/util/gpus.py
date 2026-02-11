# 1. 获取并缓存可用 gpu 数量
# 2. 获取可用 cuda 号
# 3. MacOSX 是否支持 mps
import platform
from videotrans.configure import config


# 获取可用的gpu数量 并缓存在 config.NVIDIA_GPU_NUMS 中，0=无可用显卡
#
# force_cpu: 未使用参数
#   True 强制使用 cpu 即强制设定没有显卡
def getset_gpu(force_cpu=False) -> int:
    if force_cpu:
        return 0
    # 尚未获取过时是 -1
    if config.NVIDIA_GPU_NUMS > -1:
        return config.NVIDIA_GPU_NUMS
    print('First searching GPU...')
    import torch
    # 无可用显卡
    config.NVIDIA_GPU_NUMS = 0 if not torch.cuda.is_available() else torch.cuda.device_count()
    return config.NVIDIA_GPU_NUMS


# 获取当前限制可用的cuda显卡索引
# return -1 无可用显卡， 强制调用端使用 cpu 或 mps
# >=0 为显卡号
def get_cudaX() -> int:
    if platform.system() == 'Darwin':
        return -1
    try:
        # 尚未初始化可用显卡数量
        if config.NVIDIA_GPU_NUMS == -1:
            getset_gpu()

        if config.NVIDIA_GPU_NUMS == 0:
            # 无可用显卡
            return -1

        if config.NVIDIA_GPU_NUMS == 1 or not bool(config.settings.get('multi_gpus', False)):
            # 只有一张卡，无可选 或 有多张但未启用多显卡
            return 0

        import torch
        # 存在可用显存大于12G的可直接返回使用
        free_12g = (1024 ** 3) * 12
        _default_index = 0
        _default_free, _ = torch.cuda.mem_get_info(_default_index)
        if _default_free > free_12g:
            return 0

        # 依次返回大于12G可用显存的，若不存在则返回空余显存最大的
        for i in range(1, config.NVIDIA_GPU_NUMS):
            free_bytes, _ = torch.cuda.mem_get_info(i)
            if free_bytes > free_12g:
                config.logger.debug(f'[使用第{i}块显卡],可用显存为 {free_bytes / (1024 ** 3)}GB')
                return i
            if free_bytes > _default_free:
                _default_free = free_bytes
                _default_index = i
        config.logger.debug(f'[使用第{_default_index}块显卡],可用显存为 {_default_free / (1024 ** 3)}GB')
        return _default_index
    except Exception as e:
        config.logger.exception(f'获取当前可用显卡索引失败,返回第0块显卡:{e}', exc_info=True)
        return 0


# MacOSX 判断是否支持 mps
# mps: 支持
# cpu: 不支持，必须使用 cpu
def mps_or_cpu() -> str:
    if platform.system() != 'Darwin':
        return 'cpu'
    import torch
    if torch.backends.mps.is_built() and torch.backends.mps.is_available():
        return 'mps'
    return 'cpu'
