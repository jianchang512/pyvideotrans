# pyVideoTrans 技术架构与实现原理

`pyvideotrans` 是一款功能强大的开源视频翻译配音工具（v3.99），能够将视频自动翻译并配上目标语言的语音。其核心设计理念是模块化、多线程流水线，通过灵活的标志位组合支持多种工作模式。

![](https://pvtr2.pyvideotrans.com/1760167240539_image.png)

---

## 一、核心处理流程

![](https://pvtr2.pyvideotrans.com/1760165489380_image.png)

软件将视频翻译配音过程分解为 **9 个独立阶段**，形成一条自动化的处理流水线。每个任务通过 4 个布尔标志位（`shoud_recogn`、`shoud_trans`、`shoud_dubbing`、`shoud_hebing`）控制哪些阶段被跳过，从而支持不同的工作模式。

### 1.1 九个处理阶段

| 阶段 | 方法 | 职责 |
|------|------|------|
| **① 预处理** | `prepare()` | 从视频中分离无声视频流和原始音频流；可选人声/背景分离（UVR/Spleeter）；可选降噪；创建缓存目录和输出目录 |
| **② 语音识别** | `recogn()` | 调用 ASR 引擎（默认 Faster-Whisper，支持 22 种渠道）将音频转录为带时间戳的 SRT 字幕；可选标点恢复、LLM 重新断句 |
| **③ 说话人分离** | `diariz()` | 调用说话人分离模型（built/sherpa-onnx、ali_CAM/ModelScope、pyannote、reverb 四种后端），将字幕按说话人归类标注 |
| **④ 字幕翻译** | `trans()` | 将原始语言 SRT 字幕通过翻译渠道（24 种渠道）翻译为目标语言字幕；支持双语字幕输出 |
| **⑤ 配音** | `dubbing()` | 根据目标语言字幕内容和时间戳，调用 TTS 引擎（34 种渠道）逐条生成配音音频；支持声音克隆（从原始音频截取参考片段） |
| **⑥ 音画对齐** | `align()` | 通过 `SpeedRate` 类处理：配音加速、视频慢放、去除字幕间隙静音、字幕音频强制对齐；完成后可选调节音量 |
| **⑦ 二次识别** | `recogn2pass()` | 对配音音频再次进行 ASR，生成时间轴精确且短小的字幕（仅在启用配音且非双字幕嵌入时执行） |
| **⑧ 最终合成** | `assembling()` | 将无声视频流、配音音频、背景音乐、目标语言字幕合并为最终视频文件（ffmpeg） |
| **⑨ 收尾** | `task_done()` | 将输出文件从临时目录移动到指定输出目录，清理临时文件，发送完成通知 |

### 1.2 流程控制标志位

位于 `videotrans/task/_base.py:27-39`，四个标志位在 `TransCreate.__post_init__()` 中根据配置自动计算：

```python
shoud_recogn: bool    # 是否需要语音识别（无已有字幕则为 True）
shoud_trans: bool     # 是否需要翻译（源语言 ≠ 目标语言则为 True）
shoud_dubbing: bool   # 是否需要配音（选择了配音角色且非 'No' 则为 True）
shoud_hebing: bool    # 是否需要嵌入合并（非 'tiqu' 模式且有配音或字幕嵌入则为 True）
shoud_separate: bool  # 是否需要人声背景分离
```

### 1.3 模式切换示例

不同功能通过标志位组合实现，无需单独的任务子类：

| 功能 | shoud_recogn | shoud_trans | shoud_dubbing | shoud_hebing |
|------|:---:|:---:|:---:|:---:|
| 视频翻译配音（标准模式） | ✓ | ✓ | ✓ | ✓ |
| 视频/音频转字幕（tiqu） | ✓ | 可选 | ✗ | ✗ |
| 字幕配音 | ✗ | ✗ | ✓ | ✓ |
| 仅翻译字幕文件 | ✗ | ✓ | ✗ | ✗ |

---

## 二、多线程异步任务处理架构

软件采用基于 **"生产者-消费者"模式** 的多线程多队列架构。`MultVideo` 线程充当生产者，将任务对象推入流水线的第一个队列；9 种专用 `BaseWorker` 子类作为消费者，各自监听专属队列。

### 2.1 队列流水线

```
                     MultVideo (生产者)
                           │
                    app_cfg.prepare_queue
                           ▼
                   WorkerPrepare (×N)
                    ┌────────┼────────┐
                    │ shoud_recogn ?  │
                    ▼        ▼        ▼
           regcon_queue  trans_queue  dubb_queue / assemb_queue / taskdone_queue
                │
                ▼
          WorkerRegcon (×N)
                │
         diariz_queue
                │
                ▼
          WorkerDiariz (×N)
           ┌────┼────┐
           ▼    ▼    ▼
      trans_queue  dubb_queue  assemb_queue / taskdone_queue
           │
           ▼
     WorkerTrans (×1)
      ┌────┼────┐
      ▼    ▼    ▼
 dubb_queue  assemb_queue  taskdone_queue
      │
      ▼
WorkerDubb (×1)
      │
 align_queue
      │
      ▼
WorkerAlign (×1)
 ┌────┼────┐
 ▼    ▼    ▼
regcon2_queue  assemb_queue  taskdone_queue
 │
 ▼
WorkerRegcon2Pass (×1)
 ┌────┼────┐
 ▼    ▼
assemb_queue  taskdone_queue
 │
 ▼
WorkerAssemb (×N)
 │
taskdone_queue
 │
 ▼
WorkerTaskDone (×1)
 │
(end)
```

### 2.2 Worker 基类设计

所有工作线程继承自 `BaseWorker(QThread)`（`videotrans/task/job.py:33-95`），核心循环如下：

```python
class BaseWorker(QThread):
    def __init__(self, name, queue):
        self.name = name
        self.queue = queue

    def run(self):
        while True:
            if app_cfg.exit_soft:          # 全局软退出标志
                return
            try:
                trk = self.queue.get(timeout=1)  # 阻塞1秒取任务
            except Empty:
                continue
            if trk.uuid in app_cfg.stoped_uuid_set:  # 任务已停止
                continue
            try:
                self.process_task(trk)       # 子类实现具体逻辑
            except Exception as e:
                self.handle_error(e, trk)    # 统一错误处理
```

每个子类重写 `process_task(trk)`、`get_error_prefix(trk)`（可选）和 `cleanup_on_error(trk)`（可选）。

### 2.3 线程数量动态计算

`start_thread()`（`videotrans/task/job.py:243-288`）根据 GPU 配置动态决定各 Worker 的实例数：

| Worker | 实例数 | 原因 |
|--------|--------|------|
| `WorkerPrepare` | 1 ~ 4 | GPU 密集型操作（视频编解码） |
| `WorkerRegcon` | 1 ~ 4 | GPU 密集型（ASR 推理） |
| `WorkerDiariz` | 1 ~ 4 | GPU 密集型（说话人分离） |
| `WorkerTrans` | **固定 1** | API 调用，避免并发限流 |
| `WorkerDubb` | **固定 1** | TTS API 调用，避免并发限流 |
| `WorkerRegcon2Pass` | **固定 1** | 辅助阶段 |
| `WorkerAlign` | **固定 1** | 音画对齐为单线程 |
| `WorkerAssemb` | 1 ~ 4 | GPU 密集型（ffmpeg 编码） |
| `WorkerTaskDone` | **固定 1** | 文件移动/清理 |

`task_nums` 的计算逻辑（通过 `settings.process_max_gpu` 手动指定，或根据 `multi_gpus` 自动检测：1 GPU = 1 实例，2-3 GPU = 2 实例，≥4 GPU = 4 实例）。

### 2.4 批量任务提交：MultVideo

`MultVideo(QThread)`（`videotrans/task/_mult_video.py`）负责将用户选择的多个视频文件逐个创建 `TransCreate` 对象并推入 `prepare_queue`。支持通过 `batch_nums` 参数控制每批并发数量（0 = 全部并发）。

### 2.5 软退出机制

全局标志 `app_cfg.exit_soft` 设为 `True` 时，所有 Worker 在下一轮循环中检测并安全退出。`app_cfg.stoped_uuid_set` 用于标记被手动停止的特定任务 UUID，Worker 在取出任务后跳过这些任务。

---

## 三、核心类的设计与继承关系

### 3.1 类继承体系

```
@dataclass BaseCon                    ← videotrans/configure/_base.py
    │                                  基础属性和工具方法
    ├── @dataclass BaseTask           ← videotrans/task/_base.py
    │       │                          定义 9 个阶段空方法和 4 个标志位
    │       └── @dataclass TransCreate ← videotrans/task/trans_create.py
    │                                    完整实现 9 阶段处理逻辑（~1100 行）
    │
    ├── @dataclass BaseRecogn         ← videotrans/recognition/_base.py
    │       │                          VAD 音频切分、字幕合并
    │       └── 22 个子类（懒加载）    各 ASR 渠道具体实现
    │
    ├── @dataclass BaseTrans          ← videotrans/translator/_base.py
    │       │                          MD5 缓存、逐行/全文翻译调度
    │       └── 24 个子类（懒加载）    各翻译渠道具体实现
    │
    └── @dataclass BaseTTS            ← videotrans/tts/_base.py
            │                          异步/多线程并发调度
            └── 34 个子类（懒加载）    各 TTS 渠道具体实现
```

**重要说明**：所有通道类均为 `@dataclass`，使用 `__post_init__` 初始化而非传统构造函数 `__init__`。

### 3.2 BaseCon——顶层基类

`videotrans/configure/_base.py` 定义了所有类共用的核心能力：

| 方法 | 职责 |
|------|------|
| `_exit()` | 检查是否应停止（`exit_soft` 或 UUID 在 `stoped_uuid_set` 中） |
| `_signal(**kwargs)` | 向 UI 发送消息（日志、进度、状态等） |
| `_set_proxy(type)` | 设置/清除 HTTP 代理 |
| `_new_process(callback, title, is_cuda, kwargs)` | **在子进程中执行耗时任务**（关键方法） |
| `convert_to_wav()` | 音频统一转为 48kHz 立体声 WAV |
| `_base64_to_audio()` / `_audio_to_base64()` | Base64 音频编解码 |
| `_get_internal_host()` | 检测内网地址（用于 no_proxy 设置） |

### 3.3 BaseTask——任务基类

`videotrans/task/_base.py` 定义了任务的所有阶段方法和控制标志，但方法体均为空（`pass`）——由 `TransCreate/SpeechToText/DubbingSrt/TranslateSrt` 子类重写实现。

### 3.4 三层配置体系

软件将配置分为三个层次（`videotrans/configure/config.py`）：

| 配置类 | 文件 | 用途 | 示例字段 |
|--------|------|------|---------|
| `AppCfg` | 内存（运行时） | 队列、状态、线程控制 | `prepare_queue`, `exit_soft`, `stoped_uuid_set`, `current_status` |
| `AppSettings` | `videotrans/cfg.json` | 全局默认设置、模型列表 | `homedir`, `model_list`, `vad_type`, `cuda_com_type`, `edgetts_max_concurrent_tasks` |
| `AppParams` | `videotrans/params.json` | 用户偏好、API 密钥 | `source_language`, `recogn_type`, `chatgpt_key`, `voice_role`, `app_mode` |

关键单例变量：
```python
app_cfg: AppCfg = AppCfg()        # 运行时状态
settings: AppSettings = AppSettings()  # 全局设置（从 cfg.json 加载）
params: AppParams = AppParams()    # 用户参数（从 params.json 加载）
```

### 3.5 GlobalProcessManager——子进程池管理

`videotrans/process/signelobj.py` 实现了一个单例的 `GlobalProcessManager`，管理两个 `multiprocessing.Pool`：

```
GlobalProcessManager (类级别单例)
    ├── _executor_cpu: multiprocessing.Pool
    │       workers = min(max(available_ram/4GB, 2), 8, cpu_count)
    │       maxtasksperchild = 1  ← 每个子进程执行一个任务后重启，防内存泄漏
    │
    └── _executor_gpu: multiprocessing.Pool
            workers = GPU 数量（或手动指定 process_max_gpu）
            maxtasksperchild = 1
```

- `submit_task_cpu(func, **kwargs)` / `submit_task_gpu(func, **kwargs)` 返回 `AsyncResultFutureWrapper`（将 `Pool.apply_async` 的 `AsyncResult` 包装为 `Future` 兼容接口）
- 用于执行：ASR 推理、TTS 合成、噪声去除、人声分离、说话人分离、标点恢复（均在独立子进程中运行，崩溃不影响主进程）

### 3.6 SignalHub——跨线程消息中心

`videotrans/configure/signal_hub.py` 实现了基于 Qt 信号的消息传递单例：

```python
class SignalHub(QObject):
    _instance = None
    new_message = Signal(str, object)  # (uuid, json_data)

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def post(self, uuid, data):
        self.new_message.emit(uuid, data)  # 跨线程自动使用 QueuedConnection
```

消息流：
```
BaseCon._signal() / tools.set_process()
    → push_queue(uuid, jsondata)              [configure/config.py]
        → SignalHub.instance().post(uuid, data)
            → new_message Signal (QueuedConnection)
                → WinAction.update_data()     [mainwin/_actions.py]
                    → set_process_btn_text() / UI 更新 / 弹出编辑对话框
```

### 3.7 动态通道加载

`videotrans/__init__.py` 提供了通用的懒加载函数：

```python
# ChannelProvider 数据结构
@dataclass
class ChannelProvider:
    name: str           # 界面显示名称
    imp: str            # 模块导入后缀（如 "._whisper" → "videotrans.recognition._whisper"）
    key_name: str|None  # 对应 params.json 中的 API key 字段
    win: str|None       # 对应 winform 中的设置窗口名称

# 懒加载 + 缓存
def get_instance(channel_id, provider_type, _ID_NAME_DICT):
    key = f'{provider_type}-{channel_id}'
    if key in _loaded_modules:
        return _loaded_modules[key]
    module = importlib.import_module(f'videotrans.{provider_type}{module_map.imp}')
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ == module.__name__:
            _loaded_modules[key] = obj
            return obj
```

三大模块各自的 `_ID_NAME_DICT`：
- **识别**：22 个条目（`videotrans/recognition/__init__.py:40-71`）
- **翻译**：24 个条目（`videotrans/translator/__init__.py:63-97`）
- **配音**：34 个条目（`videotrans/tts/__init__.py:74-118`）

### 3.8 特殊子进程通道

为防止 `faster-whisper` 崩溃导致整个软件退出，`Faster-Whisper` 和 `Faster-Whisper-XXL` 通过 `BaseCon._new_process()` 在独立子进程中执行。`BaseCon._signal_of_process()` 通过轮询 JSON 日志文件的方式实时读取子进程的进度和状态信息。

### 3.9 翻译缓存

`BaseTrans`（`videotrans/translator/_base.py`）实现了基于 MD5 的翻译缓存：
- 缓存 key = `md5(channel_name + api_url + model + source_lang + target_lang + text)`
- 缓存文件存储在 `{TEMP_ROOT}/translate_cache/`
- 在 `_set_cache()` 中写入，`_get_cache()` 中读取

### 3.10 CJK 特殊处理

`BaseRecogn`（`videotrans/recognition/_base.py`）对中日韩语言进行特殊处理：
- `join_word_flag`：CJK 语言字幕词间不加空格（其他语言加空格）
- `maxlen`：CJK 语言每行最大字符数为 `settings.cjk_len`（默认 22），其他语言为 `settings.other_len`（默认 46）
- `jianfan`：控制是否进行繁简转换

---

## 四、交互式单视频处理模式

当用户在**标准模式**下仅选择 **1 个视频**时，程序采用不同于批量流水线的处理模型。

### 4.1 设计动机

单视频场景下用户往往希望：
1. 修正 ASR 识别错误的文字
2. 润色机器翻译的结果
3. 为每条字幕单独指定说话人角色
4. 对不满意的配音片段单独重新配音

### 4.2 实现：Worker(QThread)

`videotrans/task/_only_one.py` 中的 `Worker` 类在**单个 QThread 内串行执行**全部 9 个阶段，通过 `uito` 信号与主线程通信：

```
Worker.run()
    ├── trk.prepare()
    ├── trk.recogn()
    ├── trk.diariz()
    ├── [暂停点 ①] → 用户校对原始字幕 → 点击"下一步"或等待倒计时
    ├── trk.trans() (if shoud_trans)
    ├── [暂停点 ②] → 用户校对翻译字幕 + 分配说话人角色 → 点击"下一步"
    ├── trk.dubbing() (if shoud_dubbing)
    ├── [暂停点 ③] → 用户修改配音结果 → 点击"下一步"
    ├── trk.align()
    ├── trk.recogn2pass()
    ├── trk.assembling()
    └── trk.task_done()
```

### 4.3 倒计时与暂停机制

1. **自动倒计时**：由 `app_cfg.set_countdown(86400)` 设置初始值，Worker 线程每 sleep(1) 递减一次。默认倒计时秒数由 `settings.countdown_sec` 控制（默认 30 秒）。
2. **无限期暂停**：用户点击"暂停"按钮将 `app_cfg.current_status` 设为 `'stop'`，触发 `set_countdown(-1)`，倒计时消失。
3. **手动继续**：用户在校对对话框中点击"确定"后调用 `WinAction.set_djs_timeout()` 使倒计时立即归零，Worker 继续执行。

### 4.4 校对对话框

- **原始字幕校对**：`EditRecognResultDialog`（`videotrans/component/onlyone_set_recogn.py`）
- **翻译字幕 + 角色分配**：`SpeakerAssignmentDialog`（`videotrans/component/onlyone_set_role.py`）
- **配音结果校对**：`EditDubbingResultDialog`（`videotrans/component/onlyone_set_editdubb.py`）

![](https://pvtr2.pyvideotrans.com/1760192881455_image.png)
![](https://pvtr2.pyvideotrans.com/1760192930833_image.png)
![](https://pvtr2.pyvideotrans.com/1760191980439_image.png)

---

## 五、软件启动与 UI 实现

### 5.1 启动流程

`sp.py` 是唯一入口，启动过程如下：

```
sp.py (if __name__ == "__main__")
  │
  ├── 1. multiprocessing.freeze_support() / set_start_method('spawn')
  ├── 2. qInstallMessageHandler() 抑制 Qt 警告
  ├── 3. atexit.register(cleanup) 注册退出清理
  ├── 4. QApplication.setHighDpiScaleFactorRoundingPolicy()
  ├── 5. 创建 QApplication
  ├── 6. 检测是否在压缩包内运行（PyInstaller 打包版）
  ├── 7. 创建 StartWindow (splash screen)
  │       └── QTimer.singleShot(100ms) → initialize_full_app()
  │           ├── 设置日志文件 logs/YYYYMMDD.log
  │           ├── 解析 --lang CLI 参数
  │           ├── 加载 QSS 样式表 (videotrans/styles/style.qss)
  │           ├── 导入 Ui_MainWindow （连接信号与槽）
  │           └── 实例化 MainWindow → main_window.uito.connect(splash.update_lable)
  │               └── MainWindow.__init__()
  │                   ├── 初始化 UI (setupUi)
  │                   ├── 实例化 WinAction (绑定界面控件事件)
  │                   ├── 启动 9 种后台 Worker 线程 (start_thread)
  │                   └── uito.emit('end') → splash 关闭
  └── 8. app.exec() → Qt 事件循环
```

### 5.2 退出机制

用户点击关闭按钮时：
1. 主窗口立即隐藏（`hide()`）
2. 设置 `app_cfg.exit_soft = True`
3. 等待数秒让所有 Worker 完成当前工作并安全退出
4. 调用 `GlobalProcessManager.shutdown()` 关闭子进程池
5. 清理临时文件 → `atexit` 回调执行 → 程序终止

### 5.3 UI 架构分层

```
UI 定义层         videotrans/ui/         ←  生成的 UI 布局文件,高级选项窗口
    ↓
UI 逻辑层         videotrans/component/   ← 通用组件：进度条、设置对话框、字幕编辑器、实时语音识别、某些独立小部件功能
    ↓
窗口管理层        videotrans/winform/     ← 懒加载的 ~70 个设置窗口、批量语音转字幕、批量为字幕配音、批量翻译srt字幕、其他独立功能模块
    ↓
主窗口层          videotrans/mainwin/
    ├── _main_win.py                      ← MainWindow: 信号绑定、GPU 检测、窗口管理
    ├── _actions.py                       ← WinAction: 核心业务逻辑 → 流程控制 → UI 更新
    └── _actions_sub.py                   ← WinActionSub: 模式切换、代理、CUDA 检查、文件选择
    ↓
任务层            videotrans/task/        ← Worker 线程、TransCreate、SpeedRate、VAD
```

### 5.4 WinAction——核心控制器

`WinAction`（`videotrans/mainwin/_actions.py`）是连接 UI 和后台任务的关键枢纽：

- **`check_start()`**：验证所有输入参数（文件、语言、API Key、输出目录等），构建 `cfg` 字典
- **`create_btns()`**：根据模式选择处理路径（单视频 → `Worker`，批量 → `MultVideo`）
- **`update_data(uuid, json_data)`**：连接 `SignalHub.new_message` 信号，根据消息类型分发到进度条更新、对话框弹出、状态切换等
- **`update_status(type)`**：切换 `ing`/`stop`/`end` 状态，控制按钮启用/禁用

### 5.5 通道设置窗口懒加载

`videotrans/winform/__init__.py` 维护了一个 ~70 个模块名的映射表（如 `"chatgpt": ".chatgpt"`），通过 `get_win(name)` 实现懒加载：

```python
def get_win(name):
    if name in _loaded_modules:
        return _loaded_modules[name]
    module = importlib.import_module(_module_map[name], __name__)
    _loaded_modules[name] = module
    return module
```

每个通道设置窗口模块通常提供一个 `openwin()` 函数来显示配置对话框。

---

## 六、代码结构概览

```
/
├── sp.py                       # ★ 主程序入口（223 行）
├── models/                     # 存放本地 AI 模型文件（ONNX 等）
├── logs/                       # 日志文件目录（YYYYMMDD.log）
├── ffmpeg/                     # ffmpeg 及 sox 二进制文件
├── docs/                       # 文档
│
└── videotrans/                 # 核心业务逻辑代码
    │   __init__.py             # ★ ChannelProvider 定义、get_instance() 懒加载
    │   cfg.json                # settings 持久化文件
    │   params.json             # params 持久化文件
    │
    ├── configure/              # 全局配置、队列定义、顶层基类
    │   ├── config.py           # ★ AppCfg / AppSettings / AppParams / logger / 队列定义 / tr()
    │   ├── _base.py            # ★ BaseCon 基类（_new_process, _signal, _exit 等）
    │   ├── signal_hub.py       # ★ SignalHub 单例（跨线程 Qt 信号）
    │   └── _except.py          # 异常信息提取
    │
    ├── task/                   # 任务处理逻辑与后台线程
    │   ├── _base.py            # ★ BaseTask 基类（9 阶段空方法 + 4 标志位）
    │   ├── trans_create.py     # ★ TransCreate 完整实现（~1100 行，核心逻辑）
    │   ├── job.py              # ★ 9 种 Worker 类 + start_thread() 入口
    │   ├── _only_one.py        # ★ 单视频交互式 Worker(QThread)
    │   ├── _mult_video.py      # ★ 多视频批量提交 MultVideo(QThread)
    │   ├── taskcfg.py          # TaskCfgBase / TaskCfgVTT 等任务配置 dataclass
    │   ├── _rate.py            # SpeedRate 音画对齐处理
    │   ├── vad.py              # TenVad / Silero VAD 语音活动检测
    │   ├── simple_runnable_qt.py # QRunnable 线程池工具
    │   └── pseudo.py           # 背景音伪原创处理
    │
    ├── recognition/            # 语音识别 (ASR) 模块（22 个渠道）
    │   ├── __init__.py         # ★ 渠道常量、_ID_NAME_DICT、run() 统一入口
    │   ├── _base.py            # ★ BaseRecogn（VAD 分割、字幕合并）
    │   └── _*.py               # 22 个渠道实现文件
    │
    ├── translator/             # 字幕翻译模块（24 个渠道）
    │   ├── __init__.py         # ★ 渠道常量、_ID_NAME_DICT、LANG_CODE 语言映射、run() 统一入口
    │   ├── _base.py            # ★ BaseTrans（MD5 缓存、逐行/全文翻译调度）
    │   └── _*.py               # 24 个渠道实现文件
    │
    ├── tts/                    # 文本转语音 (TTS) 模块（34 个渠道）
    │   ├── __init__.py         # ★ 渠道常量、_ID_NAME_DICT、SUPPORT_CLONE、run() 统一入口
    │   ├── _base.py            # ★ BaseTTS（异步/多线程并发）
    │   └── _*.py               # 34 个渠道实现文件
    │
    ├── process/                # 独立子进程实现
    │   ├── signelobj.py        # ★ GlobalProcessManager（CPU/GPU 双进程池）
    │   ├── prepare_audio.py    # 人声分离、降噪、标点恢复、说话人分离（4 种后端）
    │   ├── stt_fun.py          # ASR 子进程入口（openai_whisper, faster_whisper, paraformer 等）
    │   └── tts_fun.py          # TTS 子进程入口
    │
    ├── mainwin/                # 主窗口界面与业务逻辑
    │   ├── _main_win.py        # ★ MainWindow(QMainWindow) 初始化、信号绑定、线程启动
    │   ├── _actions.py         # ★ WinAction 核心控制器（检查、启动、状态更新）
    │   └── _actions_sub.py     # WinActionSub（模式切换、代理、CUDA、文件选择）
    │
    ├── component/              # UI 通用组件
    │   ├── progressbar.py      # 可点击进度条
    │   ├── set_form.py         # 通用设置表单
    │   ├── download.py         # 模型/文件下载弹窗
    │   ├── onlyone_set_recogn.py    # 单视频模式：原始字幕编辑对话框
    │   ├── onlyone_set_role.py      # 单视频模式：说话人角色分配对话框
    │   └── onlyone_set_editdubb.py  # 单视频模式：配音结果编辑对话框
    │
    ├── ui/                     # PySide6 UI 定义文件（自动生成 + 手动调整）
    │   └── dark/darkstyle_rc.py # QSS 资源文件
    │
    ├── winform/                # 各通道设置窗口懒加载管理
    │   ├── __init__.py         # ★ get_win() 懒加载入口（~70 个模块映射）
    │   ├── chatgpt.py          # ChatGPT 设置窗口
    │   ├── deepseek.py         # DeepSeek 设置窗口
    │   └── ...                 # ~70 个设置窗口模块
    │
    ├── styles/                 # UI 样式与图标
    │   ├── style.qss           # Qt 样式表
    │   ├── logo.png            # 启动画面 logo
    │   └── icon.ico            # 应用图标
    │
    ├── util/                   # 通用工具函数
    │   ├── contants.py         # ★ 全局常量（模型列表、角色列表、语言测试文本）
    │   ├── tools.py            # ★ 核心工具函数（ffmpeg 封装、字幕解析、文件操作、通知）
    │   ├── gpus.py             # GPU 检测与分配（get_cudaX 获取可用 GPU 索引）
    │   ├── checkgpu.py         # GPU 检测线程
    │   ├── ListenVoice.py      # 声音试听功能
    │   ├── req_fac.py          # HuggingFace 自定义 session
    │   └── help_ffmpeg.py      # ffmpeg 视频编解码器检测
    │
    ├── language/               # 界面多语言 JSON 文件
    │   ├── en.json
    │   ├── zh.json
    │   └── ...                 # 30+ 语言
    │
    ├── prompts/                # AI 翻译提示词模板
    └── voicejson/              # TTS 音色配置文件（EdgeTTS、AzureTTS 等各语言音色列表）
```

---

## 七、扩展开发指南

### 7.1 新增一个识别/翻译/TTS 通道

假设要新增一个翻译通道 `MyTranslator`，步骤如下：

#### Step 1: 创建通道实现文件

在 `videotrans/translator/` 下创建 `_mytranslator.py`：

```python
from dataclasses import dataclass
from videotrans.translator._base import BaseTrans

@dataclass
class MyTranslator(BaseTrans):
    def __post_init__(self):
        super().__post_init__()
        # 初始化 API URL、model 等
        self.api_url = 'https://api.example.com/translate'

    def _item_task(self, data: dict) -> str:
        """
        必须实现：对单条文本执行翻译，返回译文。
        data 包含 'text'（源文本）、'source_code'、'target_code' 等字段。
        """
        text = data['text']
        source = data['source_code']
        target = data['target_code']
        # 调用你的 API...
        result = call_my_api(text, source, target)
        return result
```

遵循 `BaseTrans` 的两个约定：
- 如果 `self.aisendsrt == True`（AI 渠道），则调用 `_run_srt()` 全文翻译
- 否则调用 `_run_text()` 逐行翻译（通过 `_item_task()`）

#### Step 2: 分配渠道 ID 并注册

在 `videotrans/translator/__init__.py` 中：

```python
# 1. 分配一个不重复的整数 ID
MYTRANSLATOR_INDEX = 24

# 2. 在 _ID_NAME_DICT 中注册
_ID_NAME_DICT = {
    # ... 已有条目 ...
    MYTRANSLATOR_INDEX: ChannelProvider(
        "My Translator",           # 界面显示名称
        imp="._mytranslator",     # 模块导入后缀
        key_name="mytranslator_key",  # params.json 中存储 API key 的字段
        win="mytranslator"         # winform 中的设置窗口名称
    ),
}
```

#### Step 3: 添加用户配置字段

在 `videotrans/configure/config.py` 的 `AppParams._get_defaults()` 中添加：

```python
"mytranslator_key": "",
"mytranslator_model": "model-v1",
```

#### Step 4: 创建设置窗口

在 `videotrans/winform/` 下创建 `mytranslator.py`：

```python
def openwin():
    from videotrans.component.set_form import InfoForm
    # 使用通用设置表单或自定义 QDialog
    # ...
```

在 `videotrans/winform/__init__.py` 中注册：

```python
_module_map = {
    # ... 已有条目 ...
    "mytranslator": ".mytranslator",
}
```

#### Step 5: 

- 如需要，添加语言支持检测，在 `is_allow_translate()` 中添加对该通道的语言兼容性检测逻辑。
- 若需要ui设置窗口，在 `ui/` 目录下新增界面文件，winform中调用
- 若需要在菜单中添加菜单项，`ui/en.py` 中增加 Action

---

> **版本**: v3.99 (VERSION_NUM=120399)  
> **主页**: https://github.com/jianchang512/pyvideotrans  
> **文档**: https://pyvideotrans.com
> **BBS**: https://bbs.pyvideotrans.com
