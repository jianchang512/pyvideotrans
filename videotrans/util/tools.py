import inspect
import sys

_helper_modules_names = [
    'help_role',
    'help_ffmpeg',
    'help_srt',
    'help_misc'
]

# 动态导入这些模块，并将它们的公开函数聚合到当前(tools)模块中
for module_name in _helper_modules_names:
    try:
        module = __import__(module_name, globals(), locals(), fromlist=[''], level=1)

        # 遍历导入的模块中的所有成员
        for name, member in inspect.getmembers(module):
            if inspect.isfunction(member) and not name.startswith('_'):
                # 将这个函数添加到 tools.py 的全局命名空间中
                globals()[name] = member
    except ImportError as e:
        print(f"Warning: Could not import helper module '{module_name}'. Reason: {e}", file=sys.stderr)

# 清理临时变量
if 'module_name' in locals():
    del module_name
if 'module' in locals():
    del module
if 'name' in locals():
    del name
if 'member' in locals():
    del member
if 'inspect' in locals():
    del inspect
if 'sys' in locals():
    del sys