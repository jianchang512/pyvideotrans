# 同时代理 __getattr__ 和 __setattr__

import importlib
import sys


class LazyConfigLoader:
    def __init__(self):
        # 使用一个特殊的内部名称来存储真实模块，避免与 getattr/setattr 冲突
        object.__setattr__(self, "_config_module", None)

    def _load_module_if_needed(self):
        """确保底层模块被加载，且只加载一次。"""
        if object.__getattribute__(self, "_config_module") is None:
            # print("[诊断] 首次访问 config 对象，开始加载真正的 _config_loader 模块...")
            module = importlib.import_module("._config_loader", __package__)
            object.__setattr__(self, "_config_module", module)
            # print("[诊断] _config_loader 模块加载完毕。")

    def __getattr__(self, name):
        """
        代理读操作：当访问 config.xxx 时被调用。
        """
        self._load_module_if_needed()
        # 从真实模块获取属性
        # print(f"[诊断] 懒加载 Get: {name}")
        return getattr(object.__getattribute__(self, "_config_module"), name)

    def __setattr__(self, name, value):
        """
        代理写操作：当执行 config.xxx = yyy 时被调用。
        """
        self._load_module_if_needed()
        # 在真实模块上设置属性
        # print(f"[诊断] 懒加载 Set: {name} = {value}")
        setattr(object.__getattribute__(self, "_config_module"), name, value)


# 用代理实例替换当前模块
sys.modules[__name__] = LazyConfigLoader()
