"""
本 winform 包里文件用于管理 ui 包中同名界面窗口
若需新增窗口:
    1. 确定代码文件名称 {name}，必须以英文字母开头，且仅包含英文、数字、_，例如 testwin.py
    2. 在 ui 包创建同名 界面文件 `{name}.py`，例如 testwin.py，类名必须是`Ui_{name}`,例如 `Ui_testwin`
    3. 可直接复制已有代码文件修改
    4. 需调用窗口设置的地方，使用 winform.get_win({name})

"""

import importlib
from videotrans.configure.config import app_cfg

_loaded_modules = {}  # 用于缓存已经加载过的模块
def get_win(name):
    """
    根据名字按需导入返回并显示窗口模块。
    """
    _win=app_cfg.child_forms.get(name)
    if _win:
        if hasattr(_win, 'update_ui'):
            _win.update_ui()
        _win.show()
        _win.activateWindow()
        return


    if name in ['clip_video','realtime_stt','textmatching','set_ass','formatsrtfiles','set_xxl']:
        # 在 videotrans.component.xx 返回类的实例，直接调用 .show()
        module = importlib.import_module(f'..component.{name}', package=__package__)
        _win = getattr(module, name.upper())()
        app_cfg.child_forms[name]=_win
        _win.show()
        return _win

    try:
        #返回函数执行后的结果,直接 调用 show()
        module = importlib.import_module(f'.{name}', package=__package__)
        obj = getattr(module,"openwin")()
        app_cfg.child_forms[name]=obj
        if hasattr(obj,'update_ui'):
            obj.update_ui()
        obj.show()
        return obj
    except ImportError as e:
        raise ImportError(f"Could not import winform module '{name}': {e}")

# 从 ui 包里获取ui类
def get_cls(module_name):
    if module_name in _loaded_modules:
        return getattr(_loaded_modules[module_name], f'Ui_{module_name}')

    module = importlib.import_module(f'..ui.{module_name}', package=__package__)
    _loaded_modules[module_name]=module
    return getattr(module, f'Ui_{module_name}')
