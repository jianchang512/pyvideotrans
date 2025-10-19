[English](../README.md)

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



## MacOS源码部署

0. 打开终端窗口，分别执行如下命令
	
	> 执行前确保已安装 Homebrew，如果你没有安装 Homebrew,那么需要先安装
	>
	> 执行命令安装 Homebrew：  `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
	>
	> 安装完成后，执行： `eval $(brew --config)`
	>

    ```
    brew install libsndfile

    brew install ffmpeg

    brew install git

    brew install python@3.10

    ```

    继续执行

    ```
    export PATH="/usr/local/opt/python@3.10/bin:$PATH"

    source ~/.bash_profile 
	
	source ~/.zshrc

    ```



1. 创建不含空格和中文的文件夹，在终端中进入该文件夹。
2. 终端中执行命令 `git clone https://github.com/jianchang512/pyvideotrans `
3. 执行命令 `cd pyvideotrans`
4. 继续执行 `python3.10 -m venv venv`
5. 继续执行命令 `source ./venv/bin/activate`，执行完毕查看确认终端命令提示符已变成已`(venv)`开头,以下命令必须确定终端提示符是以`(venv)`开头
6. 执行 `pip3 install -r requirements.txt `，如果提示失败，执行如下2条命令切换pip镜像到阿里镜像

    ```
    pip3 config set global.index-url https://mirrors.aliyun.com/pypi/simple/
    pip3 config set install.trusted-host mirrors.aliyun.com
    ```

    然后重新执行
    如果已切换到阿里镜像源，仍提示失败，请尝试执行 `pip install -r requirements.txt`

7. `python3.10 sp.py` 打开软件界面



## Linux 源码部署

0. CentOS/RHEL系依次执行如下命令安装 python3.10

```

sudo yum update

sudo yum groupinstall "Development Tools"

sudo yum install openssl-devel bzip2-devel libffi-devel

cd /tmp

wget https://www.python.org/ftp/python/3.10.4/Python-3.10.4.tgz

tar xzf Python-3.10.4.tgz

cd Python-3.10.4

./configure — enable-optimizations

sudo make && sudo make install

sudo alternatives — install /usr/bin/python3 python3 /usr/local/bin/python3.10 1

sudo yum install -y ffmpeg

```

1. Ubuntu/Debian系执行如下命令安装python3.10

```

apt update && apt upgrade -y

apt install software-properties-common -y

add-apt-repository ppa:deadsnakes/ppa

apt update

sudo apt-get install libxcb-cursor0

apt install python3.10

curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10

sudo update-alternatives --install /usr/bin/python python /usr/local/bin/python3.10  1

sudo update-alternatives --config python

apt-get install ffmpeg

```


**打开任意一个终端，执行 `python3 -V`，如果显示 “3.10.4”，说明安装成功，否则失败**


1. 创建个不含空格和中文的文件夹， 从终端打开该文件夹。
3. 终端中执行命令 `git clone https://github.com/jianchang512/pyvideotrans`
4. 继续执行命令 `cd pyvideotrans`
5. 继续执行 `python3 -m venv venv`
6. 继续执行命令 `source ./venv/scripts/activate`，执行完毕查看确认终端命令提示符已变成已`(venv)`开头,以下命令必须确定终端提示符是以`(venv)`开头
7. 执行 `pip3 install -r requirements.txt`，如果提示失败，执行如下2条命令切换pip镜像到阿里镜像

    ```

    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
    pip config set install.trusted-host mirrors.aliyun.com

    ```

    然后重新执行,如果已切换到阿里镜像源，仍提示失败，请尝试执行 `pip install -r requirements.txt `
8. 如果要使用CUDA加速，分别执行

    `pip3 uninstall -y torch torchaudio`

    `pip3 install torch torchaudio --index-url https://download.pytorch.org/whl/cu126`

    `pip3 install nvidia-cublas-cu12 nvidia-cudnn-cu12`

9. linux 如果要启用cuda加速，必须有英伟达显卡，并且配置好了CUDA12+环境,请自行搜索 "Linux CUDA 安装"


10. `python3 sp.py` 打开软件界面




## 使用 UV 部署：参考文档

- 提前安装好uv，然后项目目录下运行命令 `uv sync`


##  源码部署问题说明

1. 默认使用 ctranslate2的4.x版本，仅支持CUDA12.x版本，如果你的cuda低于12，并且无法升级cuda到12.x，请执行命令卸载ctranslate2然后重新安装

```

pip uninstall -y ctranslate2

pip install ctranslate2==3.24.0

```

2. 可能会遇到 `xx module not found ` 之类错误，请打开 requirements.txt，搜索该 xx 模块，然后将xx后的 ==及等会后的版本号去掉




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




如果觉得该项目对你有价值，并希望该项目能一直稳定持续维护，欢迎捐助

<img width="200" src="https://github.com/user-attachments/assets/5e8688ef-47c3-4a3c-a016-e60f73ccc4dc">


<img width="200" src="https://github.com/jianchang512/pyvideotrans/assets/3378335/fe1aa29d-c26d-46d3-b7f3-e9c030ef32c7">

