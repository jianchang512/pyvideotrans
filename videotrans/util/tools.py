# videotrans/util/tools.py
# 最终优化方案 v3: 适配 PyInstaller 打包，不再扫描文件系统

import importlib
import inspect  # 我们需要 inspect 来替代 os.listdir

# --- 步骤 1: 直接硬编码模块列表，不再扫描文件系统 ---
# 这个列表应该和你 .spec 文件里的 hiddenimports 部分保持一致
_helper_module_names = [
    'help_role',
    'help_ffmpeg',
    'help_srt',
    'help_misc'
]

_function_map = None


def _build_function_map_from_imports():
    """
    通过直接导入预定义的模块列表来构建映射。
    这种方式在开发和打包后都能正常工作。
    """
    global _function_map
    if _function_map is not None:
        return

    print("[诊断] 首次调用 tools 中的函数，开始从预定义列表构建函数映射表...")
    _function_map = {}

    for module_name in _helper_module_names:
        try:
            # 动态导入模块
            module = importlib.import_module(f".{module_name}", __package__)

            # 遍历模块成员，找出所有公开函数
            for name, member in inspect.getmembers(module):
                if inspect.isfunction(member) and not name.startswith('_'):
                    if name in _function_map:
                        print(
                            f"Warning: Function '{name}' is defined in both '{_function_map[name]}' and '{module_name}'. The latter will be used.")
                    _function_map[name] = module_name
        except ImportError as e:
            print(f"Warning: Could not import and inspect module '{module_name}'. Reason: {e}")

    print("[诊断] 函数映射表构建完毕。")


# --- 步骤 2 & 3: __getattr__ 和 __dir__ 保持不变，但调用新的构建函数 ---

def __getattr__(name):
    _build_function_map_from_imports()  # 调用新的构建函数

    if name in _function_map:
        module_name = _function_map[name]
        try:
            module = importlib.import_module(f".{module_name}", __package__)
            func = getattr(module, name)
            globals()[name] = func
            return func
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Could not lazy-load function '{name}' from module '{module_name}'. Reason: {e}")

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    _build_function_map_from_imports()  # 调用新的构建函数
    return list(globals().keys()) + list(_function_map.keys())
