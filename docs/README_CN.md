[English](../README.md)


> ## Recall.ai - Meeting Transcription API
>
> If you’re looking for a transcription API for meetings, consider checking out **[Recall.ai](https://www.recall.ai/product/meeting-transcription-api?utm_source=github&utm_medium=sponsorship&utm_campaign=jianchang512-pyvideotrans)** , an API that works with Zoom, Google Meet, Microsoft Teams, and more. Recall.ai diarizes by pulling the speaker data and separate audio streams from the meeting platforms, which means 100% accurate speaker diarization with actual speaker names.

# 视频翻译配音工具

这是一款功能强大的**开源视频翻译/语音转录/语音合成软件**，致力于将视频从一种语言，无缝转换到包含另一种语言配音和字幕的视频。


## 核心功能一览

*   **全自动视频翻译、音频翻译**：智能识别转录音视频中的说话声，生成源语言字幕文件，再翻译为目标语言字幕文件，接着进行配音，最后将新的音频与字幕合成到原视频中，一气呵成。
*   **语音转录/音视频转字幕**：批量将视频或音频文件中的人类说话声，精准转录为带时间轴的 SRT 字幕文件。
*   **语音合成/文字转语音 (TTS)**：利用多种先进的 TTS 渠道，为您的文本或 SRT 字幕文件生成高质量、自然流畅的配音。
*   **SRT 字幕文件翻译**：支持批量翻译 SRT 字幕文件，保留原有时间码和格式，并提供多种双语字幕样式。


##  软件工作原理

在开始之前，请务必理解本软件的核心工作方式：

**先将音频或视频中的`人类说话声`通过【语音识别渠道】生成字幕文件，然后经【翻译渠道】将该字幕文件翻译为指定的目标语言字幕，接着继续将该字幕使用所选的【配音渠道】生成配音音频，最后将字幕、音频、原视频三者嵌入并对齐，完成视频翻译流程。**
*   **可以处理**：任何包含人类语音的音视频，无论它有没有内嵌字幕。
*   **无法处理**：只有背景音乐和硬字幕，但没有任何人说话的视频。本软件也无法直接提取视频画面中的硬字幕。



## 预打包版本(仅win10/11可用，MacOS/Linux系统使用源码部署)

> 使用pyinstaller打包，未做免杀和签名，杀软可能报毒，请加入信任名单或使用源码部署

0. [点击去下载预打包版,解压到无空格的英文目录后，双击 sp.exe (https://github.com/jianchang512/pyvideotrans/releases)

1. 解压到英文路径下，并且路径中不含有空格。解压后双击 sp.exe  (若遇到权限问题可右键使用管理员权限打开)

2. 注意：必须解压后使用，不可直接压缩包内双击使用，也不可解压后移动sp.exe文件到其他位置



## 源码部署

> [推荐使用 uv 安装，如果还没有 uv，请查看官方安装方法](https://docs.astral.sh/uv/getting-started/installation/)
>
> [Windows用户也可查看该方法安装 uv 和 ffmpeg](https://pyvideotrans.com/zh/blog/uv-ffmpeg)

1. MacOS/Linux预先安装工具

	MacOS需执行如下命令安装相关库
    ```
    brew install libsndfile

    brew install ffmpeg

    brew install git

    brew install python@3.10

    ```
	
	Linux需安装 `ffmpeg`，命令`sudo yum install -y ffmpeg`或`apt-get install ffmpeg`

2. 创建不含空格和中文的文件夹，在终端中进入该文件夹，然后终端中执行命令 
	```
	git clone https://github.com/jianchang512/pyvideotrans
	cd pyvideotrans
	```
	> 也可直接去 https://github.com/jianchang512/pyvideotrans  该地址点击绿色*Code*按钮下载源码，解压后进入`sp.py`所在目录
3. 执行命令 `uv sync` 安装模块，根据网络情况，可能需要几分钟到十几分钟，中国大陆用户可使用镜像加速安装，命令：`uv sync --index https://mirrors.aliyun.com/pypi/simple/`
4. 执行命令 `uv run sp.py` 打开软件界面


##  源码部署问题说明

1. 默认使用 ctranslate2的4.x版本，仅支持CUDA12.x版本，如果你的cuda低于12，并且无法升级cuda到12.x，请执行命令卸载ctranslate2然后重新安装

```

uv remove ctranslate2

uv add ctranslate2==3.24.0

```




# 使用教程和文档

请查看 https://pyvideotrans.com




# 视频教程(第三方)

[Mac下源码部署/b站](https://www.bilibili.com/video/BV1tK421y7rd/)

[用Gemini Api 给视频翻译设置方法/b站](https://b23.tv/fED1dS3)

[如何下载和安装](https://www.bilibili.com/video/BV1Gr421s7cN/)


# 软件预览截图

![](https://pvtr2.pyvideotrans.com/1760079781627_image.png)


## 致谢

> 本程序主要依赖的部分开源项目

1. [ffmpeg](https://github.com/FFmpeg/FFmpeg)
2. [PySide6](https://pypi.org/project/PySide6/)
3. [edge-tts](https://github.com/rany2/edge-tts)
4. [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
5. [openai-whisper](https://github.com/openai/whisper)
6. [pydub](https://github.com/jiaaro/pydub)
6. [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)




如果觉得该项目对你有价值，并希望该项目能一直稳定持续维护，欢迎捐助

<img width="200" src="https://github.com/user-attachments/assets/5e8688ef-47c3-4a3c-a016-e60f73ccc4dc">


<img width="200" src="https://github.com/jianchang512/pyvideotrans/assets/3378335/fe1aa29d-c26d-46d3-b7f3-e9c030ef32c7">

