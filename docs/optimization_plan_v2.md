# pyVideoTrans 可维护性优化计划 v2

> 基于 2026-06-22 全面代码分析，聚焦可维护性目标  
> 前序成果：已完成 8 个大文件拆分（trans_create 9 文件、mainwin 4 文件、actions 6 文件、config 7 文件等）

---

## 总览

| 阶段 | 优先级 | 项目数 | 独立可发布 | 预估工期 |
|------|--------|--------|-----------|---------|
| Phase 0: Bug 修复 | P0 | 3 | ✅ | 1-2 天 |
| Phase 1: 结构性技术债 | P1 | 4 | ✅ | 3-5 天 |
| Phase 2: 安全与可靠性 | P2 | 3 | ✅ | 2-3 天 |
| Phase 3: 命名规范化 | P3 | 4 | ✅ | 1-2 天 |
| Phase 4: 清理死代码 | P4 | 4 | ✅ | 1 天 |
| Phase 5: 架构解耦 | P5 | 1 | ✅ | 1-2 天 |
| Phase 6: 大文件拆分 | — | 9 | ✅ | 5-8 天 |
| Phase 7: 测试覆盖 | — | 5 | ✅ | 5-10 天 |

**总计：约 20-35 个工作日**，各阶段可独立推进和合并。

---

## Phase 0: Bug 修复（P0）

### 0.1 修复 volume/pitch 变量错误

**文件**: `videotrans/mainwin/_actions_base_misc.py:104`

**问题**: `volume` 变量被误用于 `pitch` 语义的场景。  
**修复**: 将变量名改为 `pitch`，或根据实际意图修正赋值逻辑。

**工作量**: 小  
**验证**: 代码审查 + GUI 调用 pitch 滑块确认行为

### 0.2 修复 NotImplementedError 的三个抽象方法

**文件**: `videotrans/translator/_base.py`、`videotrans/tts/_base.py`（确认具体文件）

**问题**: 抽象方法使用 `raise NotImplementedError` 而非 `@abstractmethod`。  
**修复**: 
```python
from abc import ABC, abstractmethod

class BaseTranslator(ABC):
    @abstractmethod
    def translate(self, text: str) -> str:
        ...
```
确保所有基类使用 `ABC` + `@abstractmethod`，子类必须实现。

**工作量**: 小  
**验证**: 运行 `grep -r "raise NotImplementedError" videotrans/translator/ videotrans/tts/` 确认无遗漏

### 0.3 清理 _chatgpt.py 重复导入

**文件**: `videotrans/translator/_chatgpt.py`

**问题**: 存在重复的 import 行。  
**修复**: 删除重复行，保留唯一导入。

**工作量**: 小  
**验证**: `python -c "import videotrans.translator._chatgpt"`

### Phase 0 汇总

```bash
# 验证命令
uv run python -c "import videotrans; print('OK')"
uv run pytest tests/ -x -q
```

---

## Phase 1: 结构性技术债（P1）

### 1.1 提取 @retry 装饰器工厂

**问题**: 43 个 provider 方法中重复定义 `@retry` 装饰器字符串。  
**方案**: 创建 `videotrans/util/retry.py`，提供统一的 retry 工厂函数。

```python
# videotrans/util/retry.py
import functools
import time
from typing import Callable, Type

def with_retry(max_retries: int = 3, delay: float = 1.0, 
               exceptions: tuple[Type[Exception], ...] = (Exception,)):
    """统一的重试装饰器工厂"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
            raise last_exception
        return wrapper
    return decorator
```

然后替换 43 处重复定义。分批进行：先处理 translator/、再 tts/、再 recognition/。

**工作量**: 中（需要逐文件替换，共 43 处）  
**分组建议**:
- Batch A: translator/ 下所有 provider
- Batch B: tts/ 下所有 provider  
- Batch C: recognition/ 下所有 provider

**验证**: 
```bash
grep -rn "@retry" videotrans/translator/ videotrans/tts/ videotrans/recognition/ | wc -l
# 期望：仅 videotrans/util/retry.py 有定义
```

### 1.2 DeepL/DeepLX 统一语言码映射

**问题**: DeepL 和 DeepLX 各自硬编码语言映射，而非使用 `LANG_CODE` 表。  
**文件**: `videotrans/translator/_deepl.py`、`videotrans/translator/_deeplx.py`

**方案**: 引入 `videotrans/util/lang_map.py` 或扩展现有 `LANG_CODE`，让 DeepL/DeepLX 通过查表获取映射。

**工作量**: 小  
**验证**: 单元测试覆盖所有语言对映射

### 1.3 SrtItem/InputFile/SignMsg 统一 dict-like 行为

**问题**: 三个类各自独立实现 `__getitem__`、`keys()` 等字典方法。  
**方案**: 创建 `DictMixin`，三个类共同继承。

```python
# videotrans/util/dict_mixin.py
class DictMixin:
    """为数据类提供统一的 dict-like 访问"""
    def __getitem__(self, key):
        return getattr(self, key)
    def keys(self):
        return [k for k in self.__dataclass_fields__ 
                if not k.startswith('_')]
    def __contains__(self, key):
        return hasattr(self, key)
```

**工作量**: 中  
**验证**: 确保现有 `item['key']` 访问方式不受影响

### 1.4 DropButton/PeiyinDropButton 合并

**问题**: `component.py` 中两个类仅文件过滤器不同。  
**方案**: 通过构造参数 `file_filter` 区分，合并为一个类。

```python
class DropButton(QPushButton):
    def __init__(self, file_filter: str = "所有文件", ...):
        ...
```

**工作量**: 小  
**验证**: 检查所有调用点传入正确的 filter

### Phase 1 汇总

```bash
uv run black .
uv run ruff check .
uv run pytest tests/ -x -q
```

---

## Phase 2: 安全与可靠性（P2）

### 2.1 修复 SSL 验证禁用

**问题**: 8+ 处 HTTP 调用使用 `verify=False`。  
**文件**: 需 `grep -rn "verify=False" videotrans/` 定位所有位置。

**方案**:
1. 对已知安全的内部 API 保留 `verify=False`，但添加注释说明原因
2. 对外部 API 启用 SSL 验证
3. 如果是证书问题，配置正确的 CA bundle

```python
# 明确标注为什么禁用
requests.post(url, verify=False)  # 内网 API，无有效证书
```

**工作量**: 中  
**验证**: 安全审查 + 网络请求测试

### 2.2 ChatTTS 超时保护

**问题**: 3600s 超时会冻结工作线程。  
**文件**: `videotrans/tts/_chattts.py`

**方案**: 
1. 将超时降低到合理值（如 120s）
2. 添加异步超时机制或线程中断

**工作量**: 小  
**验证**: 测试长文本 TTS 是否能正常超时

### 2.3 _app_settings.py:get() 类型强转

**问题**: 手动实现类型强转，易出错。  
**方案**: 使用标准库 `ast.literal_eval()` 或简化类型检查逻辑。

**工作量**: 小  
**验证**: 单元测试覆盖各种配置值类型

### Phase 2 汇总

```bash
uv run pytest tests/ -x -q
# 手动验证：启动 GUI，检查网络请求
```

---

## Phase 3: 命名规范化（P3）

### 3.1 修复 contants → constants 拼写错误

**问题**: `configure/contants.py` 文件名拼写错误，影响数十个 import。  
**方案**: 
1. 重命名文件 `contants.py` → `constants.py`
2. 批量更新所有 import 语句

```bash
# 查找所有引用
grep -rn "contants" videotrans/
# 批量替换
sed -i 's/contants/constants/g' $(grep -rln "contants" videotrans/)
```

**工作量**: 中（涉及数十处修改）  
**验证**: `grep -rn "contants" videotrans/` 返回空

### 3.2 修复 defaulelang → defaultlang

**问题**: 50+ 处使用错误的变量名。  
**方案**: 批量重命名变量。

**工作量**: 大（50+ 处修改）  
**建议**: 分模块逐步修复，每次修复一个模块后运行测试

### 3.3 修复 OpenAICampat → OpenAICompat

**问题**: 类名拼写错误。  
**方案**: 重命名类并更新所有引用。

**工作量**: 小  
**验证**: `grep -rn "Campat" videotrans/` 返回空

### 3.4 修复 precent → percent

**问题**: 字段名拼写错误。  
**方案**: 重命名字段，更新所有访问点。

**工作量**: 小  
**验证**: `grep -rn "precent" videotrans/` 返回空

### Phase 3 汇总

```bash
uv run black .
uv run ruff check .
uv run pytest tests/ -x -q
```

---

## Phase 4: 清理死代码（P4）

### 4.1 删除备份文件

**文件**: `task/_rate - 副本.py.bak`

**操作**: 直接删除。  
**工作量**: 小  
**验证**: `ls videotrans/task/` 确认无 .bak 文件

### 4.2 重构 util/tools.py 星号导入

**问题**: 使用 `from xxx import *` 导致符号来源不可追溯。  
**方案**: 改为显式导入。

```python
# 之前
from .help_misc import *
from .help_ffmpeg import *

# 之后
from .help_misc import parse_time, format_time
from .help_ffmpeg import run_ffmpeg
```

**工作量**: 中  
**验证**: `grep -n "from.*import \*" videotrans/util/tools.py` 返回空

### 4.3 清理未使用的 whispernet_config.py

**问题**: 可能未被使用。  
**方案**: 
1. `grep -rn "whispernet_config" videotrans/` 确认是否被引用
2. 如未使用，删除或标记为废弃

**工作量**: 小  

### 4.4 清理 tts/_geminitts.py 注释代码

**文件**: `videotrans/tts/_geminitts.py`

**操作**: 删除注释掉的代码块（如需保留意图，转为 TODO 注释）。  
**工作量**: 小  

### Phase 4 汇总

```bash
uv run black .
uv run ruff check .
uv run pytest tests/ -x -q
```

---

## Phase 5: 架构解耦（P5）

### 5.1 解除 configure/base.py ↔ task/taskcfg.py 循环依赖

**问题**: `configure/base.py` 导入 `task/taskcfg.py` 中的 `SignMsg`，而 `taskcfg.py` 可能也依赖 `configure/`。  
**方案**:

1. **方案 A（推荐）**: 将 `SignMsg` 移到共享位置 `videotrans/common.py` 或 `videotrans/types.py`
2. **方案 B**: 使用延迟导入（`TYPE_CHECKING` 块）
3. **方案 C**: 提取 `SignMsg` 到独立模块 `videotrans/sign_msg.py`

```python
# videotrans/sign_msg.py
from dataclasses import dataclass

@dataclass
class SignMsg:
    """签名消息数据类"""
    name: str
    msg: str
```

**工作量**: 中  
**验证**: 
```bash
# 检查循环依赖
python -c "from videotrans.configure.base import *"
python -c "from videotrans.task.taskcfg import *"
```

### Phase 5 汇总

```bash
uv run pytest tests/ -x -q
uv run python -c "import videotrans; print('No circular import')"
```

---

## Phase 6: 大文件拆分

### 6.1 component/set_form.py（549 行）

**问题**: Provider 表单工厂，包含多种 provider 的表单逻辑。  
**方案**: 按 provider 类型拆分：
- `component/set_form/_base_form.py` — 基础表单类
- `component/set_form/_tts_form.py` — TTS provider 表单
- `component/set_form/_asr_form.py` — ASR provider 表单
- `component/set_form/_translate_form.py` — 翻译 provider 表单
- `component/set_form/__init__.py` — facade

**工作量**: 大

### 6.2 component/set_ass.py（587 行）

**问题**: ASS 编辑器，功能集中。  
**方案**: 按功能拆分：
- `component/set_ass/_editor.py` — 编辑器核心
- `component/set_ass/_preview.py` — 预览功能
- `component/set_ass/_export.py` — 导出功能

**工作量**: 大

### 6.3 component/onlyone_set_editdubb.py（550 行）

**问题**: 配音编辑器。  
**方案**: 拆分 UI 布局和业务逻辑。

**工作量**: 大

### 6.4 component/onlyone_set_role.py（547 行）

**问题**: 角色分配。  
**方案**: 拆分角色列表管理、分配逻辑、UI 布局。

**工作量**: 大

### 6.5 component/textmatching.py（521 行）

**问题**: SRT 文本匹配。  
**方案**: 拆分匹配算法、UI 交互、结果展示。

**工作量**: 中

### 6.6 ui/setini.py（685 行）

**问题**: 设置对话框，最大文件。  
**方案**: 按设置类别拆分：
- `ui/setini/_general.py` — 通用设置
- `ui/setini/_tts.py` — TTS 设置
- `ui/setini/_asr.py` — ASR 设置
- `ui/setini/_advanced.py` — 高级设置
- `ui/setini/__init__.py` — facade

**工作量**: 大

### 6.7 util/help_misc.py（422 行）

**问题**: 工具函数杂烩。  
**方案**: 按功能分类拆分到已有模块或新模块。

**工作量**: 中

### 6.8 util/help_role.py（361 行）

**问题**: 语音角色管理。  
**方案**: 拆分角色加载、保存、查询逻辑。

**工作量**: 中

### 6.9 util/help_down.py（325 行）

**问题**: 模型下载器。  
**方案**: 拆分下载逻辑、进度显示、文件管理。

**工作量**: 中

### Phase 6 验证

每个文件拆分后：
```bash
uv run black .
uv run ruff check .
uv run python -c "import videotrans.component.set_form"
uv run pytest tests/ -x -q
```

---

## Phase 7: 测试覆盖提升

### 7.1 当前覆盖情况

| 模块 | 覆盖率 | 目标 |
|------|--------|------|
| task/ 编排 | ~5% | 40% |
| recognition/ 提供者 | 0% | 30% |
| tts/ 提供者 | 0% | 30% |
| component/ | 0% | 20% |
| winform/ | ~5% | 20% |
| util/ | ~15% | 50% |

### 7.2 测试策略

1. **Provider 测试**: 使用 mock 模拟外部 API，测试翻译/TTS/ASR 逻辑
2. **Component 测试**: 使用 PySide6 的 QTest 进行 UI 组件测试
3. **Integration 测试**: 测试 task 编排流程（speech2text → translate → dubbing）

### 7.3 测试文件规划

```
tests/
├── test_recognition/
│   ├── test_whisper.py
│   ├── test_funasr.py
│   └── ...
├── test_tts/
│   ├── test_geminitts.py
│   ├── test_edgetts.py
│   └── ...
├── test_translator/
│   ├── test_chatgpt.py
│   ├── test_deepl.py
│   └── ...
├── test_task/
│   ├── test_speech2text.py
│   ├── test_translate_srt.py
│   └── test_dubbing.py
├── test_component/
│   ├── test_set_form.py
│   └── ...
└── test_util/
    ├── test_retry.py
    └── ...
```

### 7.4 Mock 策略

利用 `tests/conftest.py` 已有的 mock 基础设施，扩展：
- Mock 外部 API 调用
- Mock 文件系统操作
- Mock GPU/CUDA 相关调用

### Phase 7 验证

```bash
uv run pytest tests/ -v --cov=videotrans --cov-report=html
# 目标：总体覆盖率从 ~5% 提升到 25%+
```

---

## 执行建议

### 依赖关系

```
Phase 0 (Bug) ─────────────────────────────────┐
Phase 3 (命名) ────────────────────────────────┤
Phase 4 (清理) ────────────────────────────────┤→ Phase 7 (测试)
Phase 1 (结构) ──→ Phase 2 (安全) ──→ Phase 5 (解耦) ──→ Phase 6 (拆分) ──┘
```

**推荐执行顺序**:
1. Phase 0 → Phase 3 → Phase 4（快速修复，建立信心）
2. Phase 1 → Phase 2 → Phase 5（结构性改进）
3. Phase 6（大文件拆分，依赖前面的基础）
4. Phase 7（测试覆盖，贯穿始终）

### 每阶段检查清单

- [ ] 代码通过 `black` 格式化
- [ ] 代码通过 `ruff check` 检查
- [ ] 现有测试全部通过
- [ ] 新增代码有对应测试
- [ ] 更新相关文档（如有）

### 回滚策略

每个 Phase 独立提交，如发现问题可单独 revert：
```bash
git revert <commit-hash>
```

---

## 附录：快速命令参考

```bash
# 代码质量
uv run black .
uv run ruff check .

# 测试
uv run pytest tests/ -x -q
uv run pytest tests/ -v --cov=videotrans

# 搜索问题
grep -rn "verify=False" videotrans/
grep -rn "raise NotImplementedError" videotrans/
grep -rn "from.*import \*" videotrans/util/tools.py
grep -rn "contants" videotrans/
grep -rn "defaulelang" videotrans/
```

---

*文档版本: v2.0 | 创建日期: 2026-06-22 | 维护者: AI Assistant*
