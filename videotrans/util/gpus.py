
# 设置 config.NVIDIA_GPU_NUMS 可用cuda显卡数量并返回
import platform

from videotrans.configure import config
# 获取可用gpu数量，0=无可用显卡
def getset_gpu(is_cpu=False)->int:
    if is_cpu:
        return 0
    import torch
    # 无可用显卡
    if not torch.cuda.is_available():
        config.NVIDIA_GPU_NUMS=0
        return 0
    _count=torch.cuda.device_count()
    config.NVIDIA_GPU_NUMS=_count
    return _count

# 获取当前限制可用的cuda显卡索引
# return -1 无可用显卡， 强制接收端改用cpu
# >=0返回显卡号
def get_cudaX()->int:
    import torch
    try:
        # 尚未初始化可用显卡数量
        if config.NVIDIA_GPU_NUMS==-1:
            getset_gpu()
        if config.NVIDIA_GPU_NUMS==0:
            # 无可用显卡
            return -1
        if config.NVIDIA_GPU_NUMS==1:
            # 只有一张卡，无可选
            return 0

        # 存在可用显存大于12G的可直接返回使用
        free_12g=(1024**3)*12
        # 默认使用第0块
        _default_index=0
        _default_free, _ = torch.cuda.mem_get_info(_default_index)
        if _default_free>free_12g:
            return 0

        # 依次返回大于12G可用显存的，若不存在则返回空余显存最大的
        for i in range(1,config.NVIDIA_GPU_NUMS):
            free_bytes, _ = torch.cuda.mem_get_info(i)
            if free_bytes>free_12g:
                config.logger.debug(f'[使用第{i}块显卡],可用显存为 {free_bytes/(1024**3)}GB')
                return i
            if free_bytes>_default_free:
                _default_free=free_bytes
                _default_index=i

        config.logger.debug(f'[使用第{_default_index}块显卡],可用显存为 {_default_free/(1024**3)}GB')
        return _default_index
    except Exception as e:
        config.logger.exception(f'获取当前可用显卡索引失败,返回第0块显卡:{e}',exc_info=True)
        return 0

# 苹果系统上判断是否支持mps，如果支持返回 mps 祝发财，否则返回cpu
def mps_or_cpu():
    if platform.system() != 'Darwin':
        return 'cpu'
    import torch
    if torch.backends.mps.is_built() and torch.backends.mps.is_available():
        return 'mps'
    return 'cpu'