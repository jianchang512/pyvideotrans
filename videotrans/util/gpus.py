# 1. 获取并缓存可用 gpu 数量
# 2. 获取可用 cuda 号
# 3. MacOSX 是否支持 mps
import platform
from videotrans.configure.config import app_cfg,logger



# 获取可用的gpu数量 并缓存在 config.NVIDIA_GPU_NUMS 中，0=无可用显卡
#
# force_cpu: 未使用参数
#   True 强制使用 cpu 即强制设定没有显卡
def getset_gpu(force_cpu=False) -> int:
    if force_cpu:
        return 0
    # 尚未获取过时是 -1
    if app_cfg.NVIDIA_GPU_NUMS > -1:
        return app_cfg.NVIDIA_GPU_NUMS
    
    if platform.system() == 'Darwin':
        app_cfg.NVIDIA_GPU_NUMS = 0
        return 0
        
    import torch
    # 无可用显卡
    app_cfg.NVIDIA_GPU_NUMS = 0 if not torch.cuda.is_available() else torch.cuda.device_count()
    logger.debug(f'可用 Nvidia 显卡数: {app_cfg.NVIDIA_GPU_NUMS}')
    return app_cfg.NVIDIA_GPU_NUMS

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
