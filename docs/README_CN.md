# pyVideoTrans

> | Sponsors ||
> | :--- | :--- |
> | [Recall.ai Meeting Transcription API](https://www.recall.ai/product/meeting-transcription-api?utm_source=github&utm_medium=sponsorship&utm_campaign=jianchang512-pyvideotrans)   | If you’re looking for a transcription API for meetings, consider checking out **[Recall.ai](https://www.recall.ai/product/meeting-transcription-api?utm_source=github&utm_medium=sponsorship&utm_campaign=jianchang512-pyvideotrans)** , an API that works with Zoom, Google Meet, Microsoft Teams, and more |
> | [OfoxAI：文本、语音、图像、视频，多模型 API 资源](https://ofox.ai/zh?utm_source=github&utm_medium=sponsorship&utm_content=pyvideotrans) | 一个 API Key 接入 GPT、Claude、Gemini、DeepSeek 等文本模型及 ElevenLabs 语音模型，同时提供图像与视频生成模型，按创作需求灵活选择。|


---

<div align="center">

**一款强大的开源视频翻译 / 语音转录 / AI配音 / 字幕翻译工具**

[English](../README.md) | [**文档**](https://pyvideotrans.com) | [**问答**](https://bbs.pyvideotrans.com) | [**文档仓库**](https://github.com/jianchang512/pyvideotrans_doc_en)

[![License](https://img.shields.io/badge/License-GPL_v3-blue.svg)](../LICENSE) [![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/) [![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

</div>

**pyVideoTrans** 致力于无缝地将视频从一种语言转换为另一种语言，包含语音识别、字幕翻译、多角色配音及音画同步等全套流程。支持本地离线部署与多种主流在线 API。

<img width="1730" height="957" alt="image" src="https://github.com/user-attachments/assets/07b9c144-6043-4780-8522-bcf0eb7ca910" />

---

## ✨ 核心功能

> [技术架构与原理](architecture.md)

- **全自动视频翻译**: 一键完成：语音识别(ASR) → 字幕翻译 → 语音合成(TTS) → 视频合成。
- **️语音转录 / 字幕生成**: 批量将音视频转为 SRT 字幕，支持 **说话人分离**，区分不同角色。
- **️多角色 AI 配音**: 支持根据不同说话人分配不同的 AI 配音角色。
- **声音克隆**: 集成 **F5-TTS, CosyVoice, GPT-SoVITS** 等模型，支持零样本声音克隆。
- **强大的模型支持**:
  - **ASR**: Faster-Whisper (本地), OpenAI Whisper, 阿里 Qwen, 字节火山, Azure, Google 等。
  - **LLM 翻译**: DeepSeek, ChatGPT, Claude, Gemini, MiniMax, Ollama (本地), 阿里百炼等。
  - **TTS**: Edge-TTS (免费), OpenAI, Azure, Minimaxi, ChatTTS, ChatterBox 等。
- **️交互式编辑**: 支持在识别、翻译、配音的每个阶段暂停并人工校对，确保精准度。
- **️实用工具集**: 包含人声分离、视频/字幕合并、音画对齐、文稿匹配等辅助工具。
- **命令行模式 (CLI)**: 支持无头模式运行，方便服务器部署或批处理。
- **Web 界面 (WebUI)**: 基于浏览器的界面，适合远程访问或局域网部署。


---

## 🚀 快速开始 (Windows 用户)

我们为 Windows 10/11 用户提供了预打包的 `.exe` 版本，无需配置 Python 环境。

1. **下载**: [点击下载最新预打包版本](https://github.com/jianchang512/pyvideotrans/releases)
2. **解压**: 将压缩包解压到一个**不包含中文、空格**的路径下 (例如 `D:\pyVideoTrans`)。
3. **运行**: 双击文件夹内的 `sp.exe` 启动。

> **注意**:
> * 请勿直接在压缩包内运行。
> * 如需使用 GPU 加速(仅支持英伟达显卡加速)，请确保安装 **CUDA 12.8** 和 **cuDNN 9.11**。

---

## ️ 源码部署 (macOS / Linux / Windows 开发者)

推荐使用 **[`uv`](https://docs.astral.sh/uv/)** 进行包管理，速度更快且环境隔离更好。

### 1. 前置准备

* **Python**: 建议版本 3.10
* **FFmpeg**: 必须安装并配置到环境变量。
  * **macOS**: 
  ```
    brew install libsndfile  git  python@3.10
	
	brew uninstall --ignore-dependencies ffmpeg
	
	brew tap homebrew-ffmpeg/ffmpeg
	
	brew install homebrew-ffmpeg/ffmpeg/ffmpeg
  ```
  * **Linux (Ubuntu/Debian)**: `sudo apt-get install ffmpeg libsndfile1-dev`
  * **Windows**: [下载 FFmpeg](https://ffmpeg.org/download.html) 并配置 Path，或者直接将 ffmpeg.exe 和 ffprobe.exe 放在项目目录下

### 2. 安装 uv (如果尚未安装)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. 克隆与安装

```bash
git clone https://github.com/jianchang512/pyvideotrans.git
cd pyvideotrans
uv sync
```

> 默认不安装 `whisper.net` 本地渠道，若需要全部安装请执行 `uv sync --all-extras`
> - 单独安装 `whisper.net`：`uv sync --extra dotnet`

### 4. 启动软件

**启动 GUI 界面**:
```bash
uv run sp.py
```

**使用 CLI 命令行**:

```bash
# 视频翻译示例
uv run cli.py --task vtv --name "./video.mp4" --source_language_code zh-cn --target_language_code en --voice_role "en-US-GuyNeural"

# 语音转字幕示例
uv run cli.py --task stt --name "./audio.wav" --model_name large-v3

# 字幕翻译示例
uv run cli.py --task sts --name "./subs.srt" --target_language_code en

# 文字配音示例
uv run cli.py --task tts --name "./subs.srt" --voice_role "zh-CN-YunyangNeural"
```

> [CLI 详细参数说明](cli.md)

**启动 WebUI** (适合远程访问或局域网部署):
```bash
uv sync --extra webui
uv run webui.py
```


**Docker 部署** (容器化部署):
```bash
# 构建镜像
docker build -t pyvideotrans-webui .

# 运行
docker run -d -p 7860:7860 --name pyvideotrans pyvideotrans-webui

# 持久化配置和输出
docker run -d -p 7860:7860 \
  -v ./data/output:/app/output \
  -v ./data/config:/app/videotrans \
  --name pyvideotrans pyvideotrans-webui
```

> [WebUI 使用说明](webui.md)


### 5. (可选) GPU 加速配置(NVIDIA GPU only)

1. 如果您拥有 NVIDIA 显卡，请执行以下命令以安装支持 CUDA 的 PyTorch 版本：

```bash
# 卸载 CPU 版本
uv remove torch torchaudio

# 安装 CUDA 版本 (以 CUDA 12.x 为例)
uv add torch==2.7 torchaudio==2.7 --index-url https://download.pytorch.org/whl/cu128
uv add nvidia-cublas-cu12 nvidia-cudnn-cu12
```

2. [如果你使用 AMD 显卡，可查看该文档尝试加速](whisper_net_setup.md)

---

##  支持的渠道与模型 (部分)

| 类别 | 渠道/模型 | 说明 |
| :--- | :--- | :--- |
| **语音识别 (ASR)** | **Faster-Whisper** (本地) | 推荐，速度快，精度高 |
| | WhisperX / Parakeet | 支持时间轴对齐与说话人分离 |
| | 阿里 Qwen3-ASR / 字节火山 | 在线 API，中文效果极佳 |
| **翻译 (LLM/MT)** | **DeepSeek** / OpenAiChatGPT | 支持上下文理解，翻译更自然 |
| | MiniMax/Zhipu/Gemini/Xiaomi | 多家主流AI大模型，OpenAI兼容接口 |
| | Google / Microsoft | 传统机器翻译，速度快 |
| | HY-MT2 / M2M100 | 完全本地离线翻译 |
| **语音合成 (TTS)** | **Edge-TTS** | 微软免费接口，效果自然 |
| | **F5-TTS / OmniVoice / Qwen3-TTS** | 支持 **声音克隆** |
| | GPT-SoVITS / ChatTTS / Index-TTS | 高质量开源 TTS,要求本地部署 |
| | 302.AI / OpenAI / Azure / ElevenLabs | 高质量商业 API |

---

##  文档与支持

* **官方文档**: [https://pyvideotrans.com](https://pyvideotrans.com) (包含详细教程、API配置指南、常见问题)
* **在线问答社区**: [https://bbs.pyvideotrans.com](https://bbs.pyvideotrans.com) (提交报错日志，AI 自动分析回答)
* **GitHub Wiki**: [架构说明](architecture.md) | [新增渠道](dev_extend.md) | [CLI 文档](cli.md) | [WebUI 说明](webui.md) | [音画对齐原理](Synchronize.md) | [常见问题](faq.md)

## ️ 免责声明

- **协议范围**：本项目代码以 GPL-V3 开源，该协议仅适用于本项目代码本身，不适用于项目集成的本地模型、第三方在线 API 及其输出内容。分发修改版或衍生作品时，请遵守 GPL-V3 的相关义务。
> `videotrans`目录内`moss_transcribe_diarize | mosstts |confuciustts |external `文件夹中为集成的第三方代码，请查看对应`README.md` 了解相应协议，若不需要可删除
- **本地模型**：项目集成的本地模型各有独立许可证，版权与许可条件归上游作者或发布方所有。使用前（尤其商业使用）请自行确认并遵守对应模型许可。
- **在线 API**：项目调用的在线 API 需你自行注册、获取授权并承担费用，使用须遵守各服务商条款；输出结果能否商用请自行确认。
- **内容版权**：处理视频、音频、字幕等内容时，你须确保拥有合法权利或已获授权。开发者不对输入或输出内容主张权利，也不承担由此引发的第三方索赔责任。
- **责任限制**：软件按“现状”提供，开发者不对使用或无法使用本软件造成的任何直接或间接损失承担责任。使用即视为理解并接受上述条款。


##  致谢

本项目主要依赖以下开源项目 (部分)：

* [FFmpeg](https://github.com/FFmpeg/FFmpeg)
* [PySide6](https://pypi.org/project/PySide6/)
* [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)
* [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
* [openai-whisper](https://github.com/openai/whisper)
* [edge-tts](https://github.com/rany2/edge-tts)
* [F5-TTS](https://github.com/SWivid/F5-TTS)
* [Confucius4-TTS](https://github.com/netease-youdao/Confucius4-TTS)
* [OmniVoice](https://github.com/k2-fsa/omnivoice)
* [CosyVoice](https://github.com/FunAudioLLM/CosyVoice)
* [Gradio](https://www.gradio.app/) (WebUI)

---

*Created by [jianchang512](https://github.com/jianchang512)*


