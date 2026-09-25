# pyvideotrans 渠道扩展二次开发指南

> 本指南适用于 `pyvideotrans` 重构后的插件化渠道架构。开发者可通过继承基类并完成对应注册，快速为软件接入自定义的 **语音识别（STT）**、**字幕翻译（Trans）** 或 **文字配音（TTS）** 渠道。

---

## 目录
1. [全景开发流程](#一全景开发流程)
2. [步骤一：定义与注册渠道常量](#步骤一定义与注册渠道常量)
3. [步骤二：配置窗口与菜单集成（可选）](#步骤二配置窗口与菜单集成可选)
4. [步骤三：实现渠道核心逻辑](#步骤三实现渠道核心逻辑)
   - [3.1 字幕翻译渠道 (Translator)](#31-字幕翻译渠道-videotranstranslator)
   - [3.2 语音识别渠道 (STT/Recognition)](#32-语音识别渠道-videotransrecognition)
   - [3.3 文字配音渠道 (TTS)](#33-文字配音渠道-videotranstts)
5. [TTS 角色清单扩展规范](#五tts-角色清单扩展规范)
6. [开发避坑与最佳实践](#六开发避坑与最佳实践)
7. [附录：版本更新参考](#附录版本更新参考)

---

## 一、全景开发流程

接入一个新渠道（以内部标识名 `{name}` 为例，如 `newai`）的标准闭环如下：

```text
[1. 常量定义与注册] 
    videotrans/{module}/_constants.py  --> 分配 ID、声明 ChannelProvider
              ↓
[2. UI 与参数配置 (需配置项时)]
    videotrans/ui/{name}.py             --> 界面布局 (UI)
    videotrans/winform/{name}.py        --> 业务交互控制 (WinForm)
    videotrans/configure/_app_params.py --> 注入默认参数
    videotrans/ui/menu_list.py          --> 挂载到顶部设置菜单
              ↓
[3. 核心业务实现]
    videotrans/{module}/_{name}.py      --> 继承 Base 类，实现对应抽象方法
              ↓
[4. 角色配置 (仅 TTS 需要)]
    videotrans/configure/constant.py 或 videotrans/voicejson/{name}.json
```

---

## 步骤一：定义与注册渠道常量

对应模块目录：
- 语音识别：`videotrans/recognition/`
- 字幕翻译：`videotrans/translator/`
- 文字配音：`videotrans/tts/`

打开对应目录下的 **`_constants.py`**：

### 1. 规则约束
- **唯一 ID**：在常量列表末尾添加新常量，数值递增（如 `NEWAI_API = 32`）。
- **模块代号 `{name}`**：必须以**英文字母开头**，仅由**小写英文字母、数字、下划线**组成（例如 `newai`）。
- **实现文件**：在同级目录下新建 `_{name}.py`（例如 `_newai.py`）。

### 2. 注册到 `ID_NAME_DICT`

```python
# videotrans/{module}/_constants.py

# 1. 新增递增常量
NEWAI_API = 32

# 2. 在 ID_NAME_DICT 字典末尾注册
ID_NAME_DICT[NEWAI_API] = ChannelProvider(
    name="NewAI 渠道",         # 界面下拉列表显示的名称
    key_name="newai_key",       # 关键必填校验参数（用于校验是否已填写配置）
    win="newai",                # 对应的配置窗口名（与 winform/{name}.py 对应）
    imp="._newai"               # 动态导入的实现文件路径（相对于当前包）
)
```

> **`key_name` 说明**：若该渠道需要配置 API Key、Token 或 Base URL 等，填入核心必填项名称。当用户未在界面填写该项便直接调用时，系统将拦截并自动弹窗警告。

---

## 步骤二：配置窗口与菜单集成（可选）

若新渠道不需要用户配置 API/模型参数（如零配置的本地模型），本步可直接跳过。

### 1. 新增 UI 布局与控制器
- **UI 界面**：新建 `videotrans/ui/{name}.py`（定义输入框、保存按钮等组件，推荐参考同目录下已有文件如 `deepseek.py` 复制修改）。
- **窗口控制器**：新建 `videotrans/winform/{name}.py`（处理参数回显、数据保存、连接测试等逻辑）。

### 2. 注入默认配置参数（可选）
在 `videotrans/configure/_app_params.py` 的 `_get_defaults()` 方法中追加默认参数：
```python
# videotrans/configure/_app_params.py
def _get_defaults():
    return {
        # ...已有配置项
        "newai_key": "",
        "newai_url": "https://api.newai.com/v1",
        "newai_model": "newai-v1",
    }
```

### 3. 挂载到软件菜单栏
打开 `videotrans/ui/menu_list.py`，根据模块类型追加到对应列表中：
- 翻译渠道：追加到 `MENU_CFG_TRANS`
- 配音渠道：追加到 `MENU_CFG_TTS`
- 识别渠道：追加到 `MENU_CFG_STT`

菜单结构为三元元组：`("{name}", "菜单显示文本", None)`（第 3 个参数为 `None` 时，系统会自动寻址打开 `videotrans/winform/{name}.py`）：

```python
# videotrans/ui/menu_list.py
MENU_CFG_TRANS = [
    # ...
    ("newai", "NewAI 设置", None),
]
```

---

## 步骤三：实现渠道核心逻辑

### 3.1 字幕翻译渠道 (`videotrans/translator/`)

新建文件：`videotrans/translator/_{name}.py`。
- 参考范例：兼容 OpenAI 格式可参考 `_deepseek.py`；自建 API 或传统 HTTP 可参考 `_google.py`；本地模型可参考 `_hymt2.py`。

```python
from dataclasses import dataclass
from typing import Union
from videotrans.configure.config import ROOT_DIR, params
from videotrans.translator._base import BaseTrans

@dataclass
class NewAITrans(BaseTrans):
    """
    NewAI 翻译渠道实现
    """

    def _item_task(self, data: str) -> str:
        """
        核心翻译执行函数（必须实现）
        
        :param data: 待翻译文本内容
                     - 若勾选"发送完整字幕(Send full SRT)"：data 为标准 SRT 格式的多行纯文本字符串
                     - 若未勾选/传统渠道：data 为以换行分隔的多行文本字符串
        :return: 翻译后的文本字符串（格式需与输入保持严格对齐）
        """
        api_key = params.get("newai_key")
        
        # 退出信号检测
        if self._exit():
            return ""
        
        # TODO: 发起 HTTP 请求进行翻译
        translated_text = self._request_translate(api_key, data)
        return translated_text

    def _download(self):
        """
        模型下载函数（本地模型渠道必选，API 渠道可 pass）
        模型统一存放路径规范：f"{ROOT_DIR}/models/{model_name}"
        """
        pass
```

---

### 3.2 语音识别渠道 (`videotrans/recognition/`)

新建文件：`videotrans/recognition/_{name}.py`。
- 参考范例：API 识别参考 `_openrouter.py`；轻量本地模型参考 `_fireredasr.py`；多进程/吃显存的重量级模型参考 `_whisper.py`。

```python
from dataclasses import dataclass
from typing import List, Union
from videotrans.configure.config import ROOT_DIR, params
from videotrans.recognition._base import BaseRecogn
from videotrans.util.tools import SrtItem

@dataclass
class NewAIRecogn(BaseRecogn):
    """
    NewAI 语音识别渠道实现
    """

    def _exec(self) -> Union[List[SrtItem], None]:
        """
        核心识别逻辑（必须实现）
        :return: 填充好识别文本的 SrtItem 列表，或者在异常/退出时返回 None
        """
        if self._exit():
            return None

        # self.cut_audio() 会基于 VAD 算法自动完成音频切片
        # raws: List[SrtItem]，每个元素包含 'filename'(切片音频绝对路径)、'start_time'、'end_time' 等字段
        raws: List[SrtItem] = self.cut_audio()
        
        for it in raws:
            if self._exit():
                return None
            
            # 调用识别逻辑填充文本
            audio_file = it["filename"]
            it["text"] = self._transcribe_file(audio_file)

        return raws

    def _download(self):
        """若需要本地模型，下载至 {ROOT_DIR}/models 目录"""
        pass

    def _transcribe_file(self, audio_path: str) -> str:
        # TODO: 实际单段音频识别逻辑
        return ""
```

---

### 3.3 文字配音渠道 (`videotrans/tts/`)

> 每条字幕配音完成后，必须对配音音频文件重新格式化为 48000采样率、双通道、pcm_s16le格式，方便后续对齐和连接处理，避免数据格式不一致的各种错误
>
> 可直接调用该方法`self.convert_to_wav(配音后的音频文件, data_item['filename'])`



新建文件：`videotrans/tts/_{name}.py`。
配音根据运行机制分为两类，实现不同的核心函数：

#### 机制 A：基于 API 的网络流式/并发请求（必须实现 `_run`）
参考范例：`_openrouter.py`、`_xiaomi.py`。

```python
from dataclasses import dataclass
from typing import Dict, List, Union
from videotrans.configure.config import ROOT_DIR, params
from videotrans.tts._base import BaseTTS

@dataclass
class NewAITTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.api_key = params.get("newai_key")
        self.speed = self.get_speed()  # 获取用户在界面设定的语速

    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        """
        单条字幕配音处理
        
        :param data_item: 单条字幕元数据字典
                          {
                              "filename": "/path/to/target.wav",  # 输出音频的目标绝对路径
                              "role": "RoleName",                 # 界面选中的声音角色
                              "text": "待合成的文本内容"            # 配音文字
                          }
        :param idx: 当前字幕下标索引
        :return: 成功返回生成文件绝对路径，失败返回 None
        """
        if self._exit():
            return None

        out_path = data_item["filename"]
        role = data_item["role"]
        text = data_item["text"]

        # TODO: 发送 TTS 请求并写入 out_path
        self._generate_voice(text, role, out_path)
        return out_path

    def _download(self):
        pass
```

#### 机制 B：基于本地权重的本地模型（必须实现 `_exec`）
参考范例：`_omnivoice.py`、`_zipvoice.py`。

```python
from dataclasses import dataclass
from videotrans.configure.config import ROOT_DIR
from videotrans.tts._base import BaseTTS

@dataclass
class NewAILocalTTS(BaseTTS):

    def _exec(self):
        """
        批量/队列式本地推理任务
        所有待配音的任务队列统一存储在 self.queue_tts 中
        """
        for item in self.queue_tts:
            if self._exit():
                break
            
            out_path = item["filename"]
            role = item["role"]
            text = item["text"]
            
            # TODO: 模型批处理推理
            self.model_infer(text, role, out_path)

    def _download(self):
        # 下载权重到 {ROOT_DIR}/models
        pass
```

---

## 五、TTS 角色清单扩展规范

软件下拉框的角色清单支持以下两种维度配置：

### 1. 全局角色（角色不随源语言/目标语言改变）
直接在 `videotrans/configure/constant.py` 中声明逗号分隔的角色字符串，并在 `videotrans/util/help_role.py` 的 `role_menu()` 函数中返回即可：

```python
# videotrans/configure/constant.py
NEWAITTS_ROLES = "voice_a,voice_b,voice_c"
```

> **设计原则**：角色名称推荐直接使用**渠道接口实际接收的声音 ID**（如 `zh-CN-YunxiNeural`）。避免在界面上展示自然语言别名后再二次映射，降低维护复杂度。

### 2. 多语言角色（角色列表依赖于语言切换）
适用于各语言音色互不通用的情况：
1. 在 `videotrans/voicejson/` 目录下新建 `{name}.json`（例如 `newai.json`）。
2. 参考 `videotrans/configure/_languages_dict.py` 中的 `EDGE_LANGUANGES_CODE` 国际标准语言代码：

```json
{
  "zh-cn": ["xiaoxiao", "yunxi"],
  "en": ["jenny", "guy"],
  "ja": ["nanami", "keita"]
}
```

---

## 六、开发避坑与最佳实践

1. **退出响应**：
   长时间运行的循环或网络请求中，务必频繁穿插 `if self._exit(): return` 检查，否则用户在主界面点击“停止”时任务无法及时终止。
2. **重型本地模型隔离**：
   显存开销较大或包含 PyTorch/C++ 绑定的本地模型（如Qwen3-TTS、F5-TTS 、OmniVoice），严禁在主进程直接加载，请参考 `_whisper.py` 采用独立子进程（`multiprocessing` / `subprocess`）拉起，防止主界面卡顿或显存泄露。
3. **本地模型路径规范**：
   下载权重必须限定在 `{ROOT_DIR}/models/{model_name}` 目录下，禁止直接在当前工作目录创建相对路径。
4. **下载自动重试机制**：
   模型下载建议接入重试与断点续传逻辑，避免弱网环境下偶发网络超时导致流程阻断。
5. **SRT 结构与对齐风险**：
   翻译渠道在勾选“发送完整字幕”模式下，LLM 偶尔会破坏换行或缺失时间戳标记，需在写入前对返回行数进行合法性校验，格式损坏时需退化处理或报错提示。

---
