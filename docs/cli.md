# pyVideoTrans 命令行（CLI）使用指南

pyVideoTrans 支持通过命令行进行无界面操作，适合服务器部署、批量处理、自动化流水线等场景。

---

## 目录

- [环境要求](#环境要求)
- [基本用法](#基本用法)
- [全局选项](#全局选项)
- [任务类型总览](#任务类型总览)
- [STT — 语音转录](#stt--语音转录)
- [TTS — 文字配音](#tts--文字配音)
- [STS — 字幕翻译](#sts--字幕翻译)
- [VTV — 视频翻译](#vtv--视频翻译)
- [查询工具](#查询工具)
- [完整示例](#完整示例)
- [常见问题](#常见问题)

---

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | 3.10 |
| 包管理 | [uv](https://docs.astral.sh/uv/) |
| FFmpeg | 必须安装并配置环境变量（Windows 打包版已内置） |
| GPU 加速（可选） | NVIDIA 显卡 + CUDA 12.8 + cuDNN 9.11 |

### 启动方式

```bash
# 源码部署
uv run cli.py [参数...]

# Windows 打包版
cli.exe [参数...]
```

> **注意**：Windows 打包版（`cli.exe`）无需安装 Python，直接运行即可。

---

## 基本用法

```bash
uv run cli.py --task <任务类型> --name "<文件路径>" [其他参数]
```

**四种任务类型：**

| 任务 | 说明 | 流水线 |
|------|------|--------|
| `stt` | 语音转录 — 将音频/视频中的人声转为 SRT 字幕 | 预处理 → 语音识别 → 说话人分离 → 输出字幕 |
| `tts` | 文字配音 — 将 SRT 字幕或文本转为语音音频 | 预处理 → 配音 → 音画对齐 → 输出音频 |
| `sts` | 字幕翻译 — 将 SRT 字幕翻译为目标语言 | 预处理 → 翻译 → 输出字幕 |
| `vtv` | 视频翻译 — 全流程：识别 → 翻译 → 配音 → 合成视频 | 预处理 → 识别 → 说话人分离 → 翻译 → 配音 → 对齐 → 二次识别 → 合成视频 |

---

## 全局选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--task {stt,tts,sts,vtv}` | **必选** — 任务类型 | — |
| `--name FILE` | **必选** — 输入文件的绝对路径 | — |
| `--output-dir DIR` | 输出目录 | `<软件目录>/output/<文件名>/` |
| `--list {providers,languages,models}` | 查询可用渠道/语言/模型列表 | — |
| `--log-level {DEBUG,INFO,WARNING,ERROR}` | 日志级别 | `WARNING` |
| `-v, --verbose` | 详细输出（等同 `--log-level INFO`） | 否 |
| `-q, --quiet` | 静默模式，仅输出错误 | 否 |
| `--version` | 显示版本号 | — |
| `-h, --help` | 显示帮助信息 | — |

---

## 任务类型总览

### 各任务必选参数

| 任务 | `--name` | `--voice_role` | `--source_language_code` | `--target_language_code` |
|------|:---:|:---:|:---:|:---:|
| `stt` | ✅ | — | — | — |
| `tts` | ✅ | ✅ | — | — |
| `sts` | ✅ | — | 可选（默认 auto） | ✅ |
| `vtv` | ✅ | 可选（默认 No） | ✅ | ✅ |

### 各任务参数范围

| 参数 | stt | tts | sts | vtv |
|------|:---:|:---:|:---:|:---:|
| `--recogn_type` | ✅ | — | — | ✅ |
| `--detect_language` | ✅ | — | — | ✅ |
| `--model_name` | ✅ | — | — | ✅ |
| `--cuda` | ✅ | — | — | ✅ |
| `--remove_noise` | ✅ | — | — | ✅ |
| `--enable_diariz` | ✅ | — | — | ✅ |
| `--nums_diariz` | ✅ | — | — | ✅ |
| `--rephrase` | ✅ | — | — | ✅ |
| `--fix_punc` | ✅ | — | — | ✅ |
| `--tts_type` | — | ✅ | — | ✅ |
| `--voice_role` | — | ✅ | — | ✅ |
| `--voice_rate` | — | ✅ | — | ✅ |
| `--volume` | — | ✅ | — | ✅ |
| `--pitch` | — | ✅ | — | ✅ |
| `--voice_autorate` | — | ✅ | — | ✅ |
| `--align_sub_audio` | — | ✅ | — | ✅ |
| `--translate_type` | — | — | ✅ | ✅ |
| `--source_language_code` | — | — | ✅ | ✅ |
| `--target_language_code` | — | — | ✅ | ✅ |
| `--video_autorate` | — | — | — | ✅ |
| `--is_separate` | — | — | — | ✅ |
| `--recogn2pass` | — | — | — | ✅ |
| `--subtitle_type` | — | — | — | ✅ |
| `--clear_cache` | — | — | — | ✅ |

---

## STT — 语音转录

将音频或视频中的人声转录为带时间轴的 SRT 字幕文件。

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--recogn_type` | int | `0` | 语音识别渠道编号（0=faster-whisper, 1=openai-whisper, ...） |
| `--detect_language` | str | `auto` | 音频发音语言（auto=自动检测, zh-cn, en, ja, ...） |
| `--model_name` | str | `tiny` | 模型名称（仅 faster-whisper/openai-whisper 有效） |
| `--cuda` | flag | 否 | 启用 CUDA GPU 加速 |
| `--remove_noise` | flag | 否 | 启用降噪 |
| `--enable_diariz` | flag | 否 | 启用说话人识别 |
| `--nums_diariz` | int | `-1` | 说话人数量（-1=自动检测） |
| `--rephrase` | int | `0` | 重新断句（0=默认, 1=LLM 断句） |
| `--fix_punc` | flag | 否 | 恢复标点符号 |

### 示例

**最简用法 — 使用 faster-whisper 转录中文视频：**

```bash
uv run cli.py --task stt --name "60.mp4"
```

> 默认使用 faster-whisper + tiny 模型，输出 SRT 字幕到 `output/60-mp4/` 目录。

**指定 large-v3 模型 + GPU 加速：**

```bash
uv run cli.py --task stt --name "60.mp4" --recogn_type 0 --model_name large-v3 --cuda
```

**指定源语言为中文 + 降噪：**

```bash
uv run cli.py --task stt --name "60.mp4" --detect_language zh-cn --remove_noise --cuda
```

**使用 openai-whisper 渠道：**

```bash
uv run cli.py --task stt --name "60.mp4" --recogn_type 1 --model_name large-v3 --cuda
```

**启用说话人识别（指定 2 人）：**

```bash
uv run cli.py --task stt --name "60.mp4" --enable_diariz --nums_diariz 2 --cuda
```

**启用 LLM 重新断句 + 恢复标点：**

```bash
uv run cli.py --task stt --name "60.mp4" --rephrase 1 --fix_punc --cuda
```

**自定义输出目录：**

```bash
uv run cli.py --task stt --name "60.mp4" --output-dir "D:/my_output" --cuda
```

---

## TTS — 文字配音

将 SRT 字幕文件或纯文本文件转换为语音音频。

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--tts_type` | int | `0` | 配音渠道编号（0=Edge-TTS, ...） |
| `--voice_role` | str | **必选** | 音色名称 |
| `--voice_rate` | str | `+0%` | 语速（如 `+20%` 加速, `-10%` 减速） |
| `--volume` | str | `+0%` | 音量（如 `+50%` 增大, `-30%` 减小） |
| `--pitch` | str | `+0Hz` | 音调（如 `+10Hz` 变尖锐, `-5Hz` 变低沉） |
| `--voice_autorate` | flag | 否 | 自动加速音频以对齐字幕时间轴 |
| `--align_sub_audio` | flag | 否 | 强制修改字幕时间轴以对齐音频 |
| `--target_language_code` | str | `None` | 目标语言代码 |

### 示例

**最简用法 — 使用 Edge-TTS 为中文字幕配音：**

```bash
uv run cli.py --task tts --name "zw.srt" --voice_role "zh-CN-YunyangNeural"
```

> 使用微软免费 Edge-TTS 的云扬（男声）为中文字幕生成配音音频。

**英文配音（从中文翻译后配音）：**

```bash
uv run cli.py --task tts --name "zw.srt" --voice_role "en-US-GuyNeural" --target_language_code en
```

**调整语速和音量：**

```bash
uv run cli.py --task tts --name "zw.srt" --voice_role "zh-CN-YunyangNeural" --voice_rate=+20% --volume=+10%
```

**调整音调（变低沉）：**

```bash
uv run cli.py --task tts --name "zw.srt" --voice_role "zh-CN-YunyangNeural" --pitch=-5Hz
```

**启用自动加速对齐：**

```bash
uv run cli.py --task tts --name "zw.srt" --voice_role "zh-CN-YunyangNeural" --voice_autorate
```

**使用其他 TTS 渠道（如 OpenAI TTS，渠道编号需通过 `--list providers` 查看）：**

```bash
uv run cli.py --task tts --name "zw.srt" --tts_type <渠道编号> --voice_role "alloy"
```

### 常用 Edge-TTS 音色

| 音色名称 | 性别 | 语言 | 说明 |
|----------|------|------|------|
| `zh-CN-YunyangNeural` | 男 | 中文 | 云扬 — 新闻播报风格 |
| `zh-CN-XiaoxiaoNeural` | 女 | 中文 | 晓晓 — 自然对话 |
| `zh-CN-YunxiNeural` | 男 | 中文 | 云希 — 年轻活泼 |
| `en-US-GuyNeural` | 男 | 英文 | Guy — 自然男声 |
| `en-US-JennyNeural` | 女 | 英文 | Jenny — 自然女声 |
| `en-US-AriaNeural` | 女 | 英文 | Aria — 专业女声 |
| `en-US-EmmaNeural` | 女 | 英文 | Emma — 温暖女声 |
| `en-US-BrianNeural` | 男 | 英文 | Brian — 沉稳男声 |

> 完整音色列表请运行 `uv run cli.py --list providers` 或在软件 GUI 的 TTS 设置中查看。

---

## STS — 字幕翻译

将 SRT 字幕文件从一种语言翻译为另一种语言。

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--translate_type` | int | `0` | 翻译渠道编号（0=Google, ...） |
| `--source_language_code` | str | `auto` | 源语言代码（auto=自动检测） |
| `--target_language_code` | str | **必选** | 目标语言代码 |

### 示例

**最简用法 — 将中文字幕翻译为英文：**

```bash
uv run cli.py --task sts --name "zw.srt" --target_language_code en
```

> 默认使用 Google 翻译，源语言自动检测。

**指定源语言为中文：**

```bash
uv run cli.py --task sts --name "zw.srt" --source_language_code zh-cn --target_language_code en
```

**使用其他翻译渠道（如 DeepSeek，渠道编号需通过 `--list providers` 查看）：**

```bash
uv run cli.py --task sts --name "zw.srt" --translate_type <渠道编号> --target_language_code en
```

**翻译为日文：**

```bash
uv run cli.py --task sts --name "zw.srt" --target_language_code ja
```

**翻译为韩文：**

```bash
uv run cli.py --task sts --name "zw.srt" --target_language_code ko
```

---

## VTV — 视频翻译

全流程视频翻译：语音识别 → 字幕翻译 → 配音 → 音画合成。这是最常用也是最复杂的任务类型。

### 参数说明

VTV 模式包含 STT + TTS + STS 的所有参数，加上以下额外参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--source_language_code` | str | **必选** | 源语言代码（不可为 auto） |
| `--target_language_code` | str | **必选** | 目标语言代码 |
| `--voice_role` | str | `No` | 配音角色（`No`=不配音） |
| `--video_autorate` | flag | 否 | 自动慢速视频以对齐配音 |
| `--is_separate` | flag | 否 | 分离人声背景声 |
| `--recogn2pass` | flag | 否 | 二次语音识别（生成更精准字幕） |
| `--subtitle_type` | int | `1` | 字幕类型（0=无, 1=硬字幕, 2=软字幕, 3=硬字幕双语, 4=软字幕双语） |
| `--clear_cache` | flag | 是 | 完成后清理缓存 |
| `--no-clear-cache` | flag | — | 不清理缓存 |

### 示例

**最简用法 — 中文视频翻译为英文（不配音，仅替换字幕）：**

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en
```

> 默认使用 faster-whisper 识别 + Google 翻译 + 不配音（voice_role=No），嵌入硬字幕。

**完整流程 — 中文视频翻译为英文并配音：**

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural"
```

> 使用 Edge-TTS 的 Guy 男声为翻译后的英文字幕配音。

**GPU 加速 + 高精度模型：**

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural" --cuda --recogn_type 0 --model_name large-v3
```

**分离人声背景声（提高识别和配音质量）：**

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural" --is_separate --cuda
```

**双语硬字幕 + 二次识别：**

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural" --subtitle_type 3 --recogn2pass --cuda
```

**软字幕（播放器可开关）+ 音频自动加速：**

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural" --subtitle_type 2 --voice_autorate --cuda
```

**视频慢速对齐（配音比视频长时放慢视频）：**

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural" --video_autorate --cuda
```

**自定义输出目录 + 保留缓存：**

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural" --output-dir "D:/translated" --no-clear-cache
```

**翻译为日文并配音：**

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code ja --voice_role "ja-JP-KeitaNeural" --cuda
```

**翻译为韩文并配音：**

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code ko --voice_role "ko-KR-InJoonNeural" --cuda
```

**静默模式运行（仅输出错误）：**

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural" -q
```

**详细日志模式（调试用）：**

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural" -v
```

---

## 查询工具

### 列出所有可用渠道

```bash
uv run cli.py --list providers
```

输出示例：

```
=== Available Providers ===

--- Speech Recognition (STT) ---
  0 = faster-whisper(本地)
  1 = openai-whisper(本地)
  2 = 字节语音识别大模型极速版
  ...

--- Translation ---
  0 = Google翻译
  1 = 微软翻译
  2 = 百度翻译
  ...

--- Text-to-Speech (TTS) ---
  0 = Edge-TTS
  1 = Azure TTS
  2 = OpenAI TTS
  ...
```

### 列出所有支持的语言

```bash
uv run cli.py --list languages
```

输出示例：

```
=== Available Language Codes ===
  en         English
  zh-cn      简体中文
  zh-tw      繁體中文
  ja         日本語
  ko         한국어
  fr         Français
  de         Deutsch
  es         Español
  ...
```

### 列出 faster-whisper 可用模型

```bash
uv run cli.py --list models
```

输出示例：

```
=== faster-whisper Models ===
  tiny                      Systran/faster-whisper-tiny
  base                      Systran/faster-whisper-base
  small                     Systran/faster-whisper-small
  medium                    Systran/faster-whisper-medium
  large-v3                  Systran/faster-whisper-large-v3
  large-v3-turbo            mobiuslabsgmbh/faster-whisper-large-v3-turbo
  ...
```

---

## 完整示例

以下示例均假设：
- 中文原始视频文件为 `60.mp4`
- 中文字幕文件为 `zw.srt`
- 翻译目标语言为英文
- 配音使用 Edge-TTS 的 `en-US-GuyNeural` 音色
- 其他非必须参数保持默认

### 场景 1：仅语音转录（中文字幕生成）

```bash
uv run cli.py --task stt --name "60.mp4" --detect_language zh-cn --cuda
```

**说明**：将 `60.mp4` 中的中文语音转录为 `zh-cn.srt` 字幕文件，输出到 `output/60-mp4/`。

### 场景 2：仅字幕翻译（中文字幕 → 英文字幕）

```bash
uv run cli.py --task sts --name "zw.srt" --source_language_code zh-cn --target_language_code en
```

**说明**：将 `zw.srt` 翻译为 `en.srt`，输出到 `output/zw-srt/`。

### 场景 3：仅文字配音（为中文字幕生成英文配音）

```bash
uv run cli.py --task tts --name "zw.srt" --voice_role "en-US-GuyNeural" --target_language_code en
```

**说明**：为 `zw.srt` 中的文本生成英文配音 WAV 文件，输出到 `output/zw-srt/`。

### 场景 4：完整视频翻译（中文 → 英文，带配音）

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural" --cuda
```

**说明**：全流程处理：
1. 识别 `60.mp4` 中的中文语音 → 生成中文字幕
2. 将中文字幕翻译为英文字幕
3. 使用 Edge-TTS Guy 男声生成英文配音
4. 将英文字幕和配音合成到视频中

输出：`output/60-mp4/60.mp4`（翻译后的视频）

### 场景 5：高质量视频翻译（分离人声 + GPU 加速 + 二次识别）

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural" --cuda --is_separate --recogn2pass --model_name large-v3
```

**说明**：
- `--is_separate`：分离人声和背景声，提高识别和配音质量
- `--recogn2pass`：配音完成后再次识别，生成更精准的字幕时间轴
- `--model_name large-v3`：使用最高精度的识别模型
- `--cuda`：GPU 加速

### 场景 6：双语字幕视频

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural" --subtitle_type 3 --cuda
```

**说明**：`--subtitle_type 3` 生成硬字幕双语（中英同时显示）。

### 场景 7：视频翻译到日文

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code ja --voice_role "ja-JP-KeitaNeural" --cuda
```

### 场景 8：批量处理多个文件（Shell 循环）

```bash
# Bash / Git Bash
for f in *.mp4; do
  uv run cli.py --task vtv --name "$f" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural" --cuda
done
```

```powershell
# PowerShell
Get-ChildItem *.mp4 | ForEach-Object {
  uv run cli.py --task vtv --name $_.FullName --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural" --cuda
}
```

---

## 常见问题

### Q: 如何查看所有可用的配音渠道和音色？

```bash
uv run cli.py --list providers
```

或者在软件 GUI 中，选择配音渠道后查看音色下拉列表。

### Q: 如何查看所有支持的语言代码？

```bash
uv run cli.py --list languages
```

### Q: 路径中包含空格怎么办？

使用英文双引号包裹路径：

```bash
uv run cli.py --task vtv --name "D:/my videos/60.mp4" --source_language_code zh-cn --target_language_code en
```

### Q: 如何启用 GPU 加速？

添加 `--cuda` 参数：

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural" --cuda
```

> 前提：已安装 NVIDIA 显卡驱动、CUDA 12.8+、cuDNN 9.11+。

### Q: 如何使用本地大模型翻译？

需要先在本地部署兼容 OpenAI 接口的大模型（如 Ollama），然后：

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --translate_type <兼容AI渠道编号> --cuda
```

> 翻译渠道的 API 地址需要在软件 GUI 的翻译设置中预先配置。

### Q: 处理速度太慢怎么办？

1. **启用 GPU 加速**：添加 `--cuda`
2. **使用小模型**：`--model_name tiny`（速度快但精度低）
3. **跳过人声分离**：不加 `--is_separate`
4. **跳过二次识别**：不加 `--recogn2pass`

### Q: 翻译后的字幕和声音不同步怎么办？

添加 `--voice_autorate`（自动加速音频）或 `--video_autorate`（自动慢速视频）：

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural" --voice_autorate --cuda
```

### Q: 如何只翻译不配音？

不指定 `--voice_role` 或指定为 `No`：

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en
```

### Q: 如何查看详细的处理日志？

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural" -v
```

或者指定日志级别：

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural" --log-level DEBUG
```

### Q: 如何使用软字幕（播放器可开关）？

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --subtitle_type 2 --cuda
```

> `--subtitle_type 2` = 软字幕，`--subtitle_type 1` = 硬字幕（默认）。

### Q: 如何保留处理缓存以便调试？

```bash
uv run cli.py --task vtv --name "60.mp4" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural" --no-clear-cache
```

---

## 退出码

| 退出码 | 含义 |
|--------|------|
| `0` | 任务成功完成 |
| `1` | 任务执行出错 |
| `130` | 用户中断（Ctrl+C） |
| `2` | 参数错误（argparse 自动退出） |

---

## 相关文档

- [使用入门](https://pyvideotrans.com/getstart)
- [CLI 命令行模式文档](https://pyvideotrans.com/cli)
- [语音识别渠道说明](https://pyvideotrans.com/yuyinshibiequdao)
- [翻译渠道说明](https://pyvideotrans.com/fanyiqudao)
- [配音渠道说明](https://pyvideotrans.com/peiyinqudao)
- [常见问题 FAQ](https://pyvideotrans.com/faq)
- [技术架构](https://pyvideotrans.com/yuanli)
