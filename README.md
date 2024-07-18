简体中文 | [English](docs/EN/README_EN.md) | [pt-BR](docs/pt-BR/README_pt-BR.md) | [Italian](docs/IT/README_IT.md) | [Spanish](docs/ES/README_ES.md) / [捐助](docs/about.md) / [Discord](https://discord.gg/y9gUweVCCJ) / 微信公众号：`pyvideotrans`

# 视频翻译配音工具

这是一个视频翻译配音工具，可将一种语言的视频翻译为指定语言的视频，自动生成和添加该语言的字幕和配音。


语音识别支持 `faster-whisper`模型 `openai-whisper`模型 和 `GoogleSpeech` `zh_recogn阿里中文语音识别模型`.

文字翻译支持 `微软翻译|Google翻译|百度翻译|腾讯翻译|ChatGPT|AzureAI|Gemini|DeepL|DeepLX|字节火山|离线翻译OTT`

文字合成语音支持 `Microsoft Edge tts` `Google tts` `Azure AI TTS` `Openai TTS` `Elevenlabs TTS` `自定义TTS服务器api` `GPT-SoVITS` [clone-voice](https://github.com/jianchang512/clone-voice)  [ChatTTS-ui](https://github.com/jianchang512/ChatTTS-ui)  [Fish TTS](https://github.com/fishaudio/fish-speech)  [CosyVoice](https://github.com/FunAudioLLM/CosyVoice)

允许保留背景伴奏音乐等(基于uvr5)

支持的语言：中文简繁、英语、韩语、日语、俄语、法语、德语、意大利语、西班牙语、葡萄牙语、越南语、泰国语、阿拉伯语、土耳其语、匈牙利语、印度语、乌克兰语、哈萨克语、印尼语、马来语、捷克语、波兰语


> [赞助商]
> 
> [![](https://github.com/user-attachments/assets/48f4ac8f-e321-4bd3-ab2e-d6053d932f49)](https://302.ai/)
>  [302.AI](https://302.ai) 是一个汇集全球顶级AI的自助平台，按需付费，零月费，零门槛使用各种类型AI。
> 
> [点击注册](https://302.ai): 立即获得 1PTC(1PTC=1美金，约为7人民币)代币。
> 
> 功能全面: 将最好用的AI集成到在平台之上，包括不限于AI聊天，图片生成，图片处理，视频生成，全方位覆盖。
> 
> 简单易用: 提供机器人，工具和API多种使用方法，可以满足从小白到开发者多种角色的需求。
> 
> 按需付费，零门槛: 不提供月付套餐，对产品不设任何门槛，按需付费，全部开放。充值余额永久有效。
> 
> 管理者和使用者分离：管理者一键分享，使用者无需登录。



# 主要用途和使用方式

【翻译视频并配音】将视频中的声音翻译为另一种语言的配音，并嵌入该语言字幕

【音频或视频转为字幕】将音频、视频文件中的人类说话声，识别为文字并导出为srt字幕文件

【批量字幕创建配音】根据本地已有的srt字幕文件创建配音，支持单个或批量字幕

【批量字幕翻译】将一个或多个srt字幕文件翻译为其他语言的字幕文件

【音频、视频、字幕合并】音频文件、视频文件、字幕文件合并为一个视频文件

【从视频中分离出音频】从视频中分离为音频文件和无声视频

【下载油管视频】可从youtube上下载视频

----



https://github.com/jianchang512/pyvideotrans/assets/3378335/3811217a-26c8-4084-ba24-7a95d2e13d58


# 预打包版本(仅win10/win11可用，MacOS/Linux系统使用源码部署)

> 使用pyinstaller打包，未做免杀和签名，杀软可能报毒，请加入信任名单或使用源码部署

0. [点击去下载预打包版,解压到无空格的英文目录后，双击 sp.exe (https://github.com/jianchang512/pyvideotrans/releases)

1. 解压到英文路径下，并且路径中不含有空格。解压后双击 sp.exe  (若遇到权限问题可右键使用管理员权限打开)

4. 注意：必须解压后使用，不可直接压缩包内双击使用，也不可解压后移动sp.exe文件到其他位置


# MacOS源码部署

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
4. 继续执行 `python -m venv venv`
5. 继续执行命令 `source ./venv/bin/activate`，执行完毕查看确认终端命令提示符已变成已`(venv)`开头,以下命令必须确定终端提示符是以`(venv)`开头
6. 执行 `pip install -r mac-requirements.txt --no-deps`，如果提示失败，执行如下2条命令切换pip镜像到阿里镜像

    ```
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
    pip config set install.trusted-host mirrors.aliyun.com
    ```

    然后重新执行
    如果已切换到阿里镜像源，仍提示失败，请尝试执行 `pip install -r mac-requirements.txt  --ignore-installed --no-deps `

7. `python sp.py` 打开软件界面



# Linux 源码部署

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

sudo alternatives — install /usr/bin/python3 python3 /usr/local/bin/python3.10

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

pip 23.2.1 from /usr/local/lib/python3.10/site-packages/pip (python 3.10)

sudo update-alternatives --install /usr/bin/python python /usr/local/bin/python3.10 

sudo update-alternatives --config python

apt-get install ffmpeg

```


**打开任意一个终端，执行 `python3 -V`，如果显示 “3.10.4”，说明安装成功，否则失败**


1. 创建个不含空格和中文的文件夹， 从终端打开该文件夹。
3. 终端中执行命令 `git clone https://github.com/jianchang512/pyvideotrans`
4. 继续执行命令 `cd pyvideotrans`
5. 继续执行 `python -m venv venv`
6. 继续执行命令 `source ./venv/bin/activate`，执行完毕查看确认终端命令提示符已变成已`(venv)`开头,以下命令必须确定终端提示符是以`(venv)`开头
7. 执行 `pip install -r requirements.txt --no-deps`，如果提示失败，执行如下2条命令切换pip镜像到阿里镜像

    ```

    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
    pip config set install.trusted-host mirrors.aliyun.com

    ```

    然后重新执行,如果已切换到阿里镜像源，仍提示失败，请尝试执行 `pip install -r requirements.txt  --ignore-installed --no-deps `
8. 如果要使用CUDA加速，分别执行

    `pip uninstall -y torch torchaudio`

    `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118`

    `pip install nvidia-cublas-cu11 nvidia-cudnn-cu11`

9. linux 如果要启用cuda加速，必须有英伟达显卡，并且配置好了CUDA11.8+环境,请自行搜索 "Linux CUDA 安装"


10. `python sp.py` 打开软件界面


# Window10/11 源码部署

0. 打开 https://www.python.org/downloads/ 下载 windows3.10，下载后双击，一路next，注意要选中“Add to PATH”

   **打开一个cmd，执行 `python -V`，如果输出不是 `3.10.4`,说明安装出错，或没有加入 `Add to PATH`,请重新安装**

1. 打开 https://github.com/git-for-windows/git/releases/download/v2.45.0.windows.1/Git-2.45.0-64-bit.exe ，下载git，下载后双击一路下一步。
2. 找个不含空格和中文的文件夹，地址栏中输入 `cmd`回车，打开终端，以下命令均在该终端中执行
3. 执行命令 `git clone https://github.com/jianchang512/pyvideotrans`
4. 继续执行命令 `cd pyvideotrans`
5. 继续执行 `python -m venv venv`
6. 继续执行命令 `.\venv\scripts\activate`,执行后请查看确认命令行开头已变成了`(venv)`,否则说明出错
7. 执行 `pip install -r requirements.txt --no-deps`，如果提示失败，执行如下2条命令切换pip镜像到阿里镜像

    ```

    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
    pip config set install.trusted-host mirrors.aliyun.com

    ```

    然后重新执行,如果已切换到阿里镜像源，仍提示失败，请尝试执行 `pip install -r requirements.txt  --ignore-installed --no-deps `
8.  如果要使用CUDA加速，分别执行

    `pip uninstall -y torch torchaudio`

    `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118`


9. windows  如果要启用cuda加速，必须有英伟达显卡，并且配置好了CUDA11.8+环境，具体安装见 [CUDA加速支持](https://pyvideotrans.com/gpu.html)

10. 解压 ffmpeg.zip 到当前源码目录下，提示覆盖则覆盖，解压后确保源码下的ffmepg文件夹内能看到 ffmpeg.exe ffprobe.exe ytwin32.exe,

11. `python sp.py` 打开软件界面



#  源码部署问题说明

1. 默认使用 ctranslate2的4.x版本，仅支持CUDA12.x版本，如果你的cuda低于12，并且无法升级cuda到12.x，请执行命令卸载ctranslate2然后重新安装

```

pip uninstall -y ctranslate2

pip install ctranslate2==3.24.0

```

2. 可能会遇到 `xx module not found ` 之类错误，请打开 requirements.txt，搜索该 xx 模块，然后将xx后的 ==及等会后的版本号去掉




# 使用教程和文档

请查看 https://pyvideotrans.com/guide.html


# 语音识别模型:

   下载地址： https://pyvideotrans.com/model.html

   模型说明和区别介绍：https://pyvideotrans.com/02.html



# 视频教程(第三方)

[Mac下源码部署/b站](https://www.bilibili.com/video/BV1tK421y7rd/)

[用Gemini Api 给视频翻译设置方法/b站](https://b23.tv/fED1dS3)

[如何下载和安装](https://www.bilibili.com/video/BV1Gr421s7cN/)


# 软件预览截图

![image](https://github.com/jianchang512/pyvideotrans/assets/3378335/55faecd9-5ac6-4962-b0f3-ef2283000c64)



# 相关联项目

[ChatTTS-ui:使用ChatTTS合成声音的UI界面](https://github.com/jianchang512/ChatTTS-ui)

[OTT:本地离线文字翻译工具](https://github.com/jianchang512/ott)

[声音克隆工具:用任意音色合成语音](https://github.com/jianchang512/clone-voice)

[语音识别工具:本地离线的语音识别转文字工具](https://github.com/jianchang512/stt)

[人声背景乐分离:人声和背景音乐分离工具](https://github.com/jianchang512/vocal-separate)

[GPT-SoVITS的api.py改良版](https://github.com/jianchang512/gptsovits-api)

[适配 CosyVoice 的 api.py](https://github.com/jianchang512/cosyvoice-api)


## 致谢

> 本程序主要依赖的部分开源项目

1. ffmpeg
2. PySide6
3. edge-tts
4. faster-whisper
5. openai-whisper
6. pydub

## 关注作者微信公众号

<img width="200" src="https://github.com/jianchang512/pyvideotrans/assets/3378335/f9337111-9084-41fe-8840-1fb8fedca92d">


如果觉得该项目对你有价值，并希望该项目能一直稳定持续维护，欢迎捐助

<img width="200" src="https://github.com/jianchang512/pyvideotrans/raw/main/images/wx.png">

<img width="200" src="https://github.com/jianchang512/pyvideotrans/assets/3378335/fe1aa29d-c26d-46d3-b7f3-e9c030ef32c7">
