[简体中文](./README.md) / [👑 Donate to this project](./about.md)

# Video Translation and Dubbing Tool

>
> This is a video translation and dubbing tool that can translate a video from one language to a specified language and automatically generate and add subtitles and dubbing in that language.
>
> The voice recognition supports `faster-whisper`, `openai-whisper`, `GoogleSpeech`, `zh_recogn Ali Chinese voice recognition model`.
>
> Text translation supports `Microsoft Translate | Google Translate | Baidu Translate | Tencent Translate | ChatGPT | AzureAI | Gemini | DeepL | DeepLX | Offline translation OTT`
>
> Text-to-speech synthesis supports `Microsoft Edge tts`, `Google tts`, `Azure AI TTS`, `Openai TTS`, `Elevenlabs TTS`, `Custom TTS server API`, `GPT-SoVITS`, [clone-voice](https://github.com/jianchang512/clone-voice).
>
> Allows retaining background accompaniment music, etc. (based on uvr5)
>
> Supported languages: Simplified and Traditional Chinese, English, Korean, Japanese, Russian, French, German, Italian, Spanish, Portuguese, Vietnamese, Thai, Arabic, Turkish, Hungarian, Hindi, Ukrainian, Kazakh, Indonesian, Malay.Cozhen

# Main Uses and How to Use

【Translate videos and dub】Translate the audio in videos into the voice of another language and embed subtitles in that language

【Convert audio or video to subtitles】Recognize human speech in audio or video files as text and export to srt subtitle files

【Batch subtitle creation and dubbing】Create dubbing based on local existing srt subtitle files, supporting single or batch subtitles

【Batch subtitle translation】Translate one or more srt subtitle files into subtitles in other languages

【Audio, video, and subtitle merge】Merge audio files, video files, and subtitle files into one video file

【Extract audio from video】Extract as audio files and mute video from video


【Download YouTube videos】Download videos from YouTube

----

https://github.com/jianchang512/pyvideotrans/assets/3378335/3811217a-26c8-4084-ba24-7a95d2e13d58

# Pre-Packaged Version (Only available for Win10/Win11, MacOS/Linux systems use source code deployment)

> Packaged with pyinstaller, not anti-virus whitelisted or signed, anti-virus software may flag it, please add to trusted list or use source code deployment

0. [Click to download the pre-packaged version, unzip to an English directory without spaces, then double-click sp.exe (https://github.com/jianchang512/pyvideotrans/releases)

1. Unzip to an English path, and ensure the path does not contain spaces. After unzipping, double-click sp.exe (if you encounter permission issues, right-click to open as administrator)

4. Note: Must be used after extracting, cannot be used directly within the compressed package, nor can the sp.exe file be moved to another location after extraction


# MacOS Source Code Deployment

0. Open a terminal window and execute commands respectively

    ```
    brew install libsndfile

    brew install ffmpeg

    brew install git

    brew install python@3.12

    ```

    Then proceed with the following 2 commands

    ```
    export PATH="/usr/local/opt/python@3.12/bin:$PATH"

    source ~/.bash_profile
	
	source ~/.zshrc

    ```

1. Create a folder without spaces and Chinese characters, and enter that folder in the terminal.
2. Execute the command `git clone https://github.com/jianchang512/pyvideotrans` in the terminal.
3. Execute the command `cd pyvideotrans`.
4. Continue with `python -m venv venv`.
5. Continue with the command `source ./venv/bin/activate`, confirming that the terminal prompt starts with `(venv)`, the following commands must be sure the terminal prompt starts with `(venv)`.
6. Execute `pip install -r requirements.txt --no-deps`, if there's a failure prompt,

  try `pip install -r requirements.txt  --ignore-installed --no-deps`.

7. `python sp.py` to open the software interface.



[Detailed MacOS deployment scheme](https://pyvideotrans.com/mac.html)

# Linux Source Code Deployment

0. CentOS/RHEL series execute the following commands in order to install python3.12

```

sudo yum update

sudo yum groupinstall "Development Tools"

sudo yum install openssl-devel bzip2-devel libffi-devel

cd /tmp

wget https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz

tar xzf Python-3.12.0.tgz

cd Python-3.12.0

./configure — enable-optimizations

sudo make && sudo make install

sudo alternatives — install /usr/bin/python3 python3 /usr/local/bin/python3.12 2

sudo yum install -y ffmpeg

```

## Ubuntu/Debian series execute the following commands to install python3.12

```

apt update && apt upgrade -y

apt install software-properties-common -y

add-apt-repository ppa:deadsnakes/ppa

apt update

sudo apt-get install libxcb-cursor0

apt install python3.12

curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

pip 23.2.1 from /usr/local/lib/python3.12/site-packages/pip (python 3.12)

sudo update-alternatives --install /usr/bin/python python /usr/local/bin/python3.12 1

sudo update-alternatives --config python

apt-get install ffmpeg

```

**Open any terminal, execute `python3 -V`, if it displays “3.12.0”, the installation is successful, otherwise it's a failure.**

1. Create a folder without spaces and Chinese characters, open the folder from the terminal.
3. In the terminal execute the command `git clone https://github.com/jianchang512/pyvideotrans`.
4. Continue with the command `cd pyvideotrans`.
5. Continue with `python -m venv venv`.
6. Continue with the command `source ./venv/bin/activate`, confirming that the terminal prompt starts with `(venv)`.
7. Execute `pip install -r requirements.txt --no-deps`, if there's a failure prompt,  try `pip install -r requirements.txt  --ignore-installed --no-deps`.
8. If you want to use CUDA acceleration, execute respectively

    `pip uninstall -y torch torchaudio`


    `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118`

    `pip install nvidia-cublas-cu11 nvidia-cudnn-cu11`

9. To enable CUDA acceleration on Linux, you must have an NVIDIA card and have configured the CUDA11.8+ environment properly

10. `python sp.py` to open the software interface.

# Window10/11 Source Code Deployment

0. Open https://www.python.org/downloads/ and download windows3.12, after downloading, keep clicking next, ensuring to select "Add to PATH".

   **Open a cmd, execute `python -V`, if the output is not `3.12.3`, it means there was an installation error, or "Add to PATH" was not selected, please reinstall.**

1. Open https://github.com/git-for-windows/git/releases/download/v2.45.0.windows.1/Git-2.45.0-64-bit.exe, download git, after downloading keep clicking next.
2. Find a folder that does not contain spaces and Chinese characters, type `cmd` in the address bar and hit enter to open the terminal, all commands are to be executed in this terminal.
3. Execute the command `git clone https://github.com/jianchang512/pyvideotrans`.
4. Continue with the command `cd pyvideotrans`.
5. Continue with `python -m venv venv`.
6. Continue with the command `.\venv\scripts\activate`, ensuring the command line starts with `(venv)`, otherwise, there's an error.
7. Execute `pip install -r requirements.txt --no-deps`, if there's a failure prompt,  try `pip install -r requirements.txt  --ignore-installed --no-deps`.
8. If you want to use CUDA acceleration, execute respectively

    `pip uninstall -y torch torchaudio`

    `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118`


9. To enable CUDA acceleration on Windows, you must have an NVIDIA card and have configured the CUDA11.8+ environment properly, see [CUDA acceleration support](https://github.com/jianchang512/pyvideotrans?tab=readme-ov-file#cuda-%E5%8A%A0%E9%80%9F%E6%94%AF%E6%8C%81).


10. Unzip ffmpeg.zip to the current source code directory, overwrite if prompted, ensure you can see ffmpeg.exe, ffprobe.exe, ytwin32.exe, in the ffmepg folder within the source code.

11. `python sp.py` to open the software interface.


# Tutorial and Documentation

Please check https://pyvideotrans.com/guide.html


# Voice Recognition Models:

   Download address: https://pyvideotrans.com/model.html

   Description and differences introduction: https://pyvideotrans.com/02.html


# Video Tutorials (Third-party)

[MacOS Source Code Deployment/Bilibili](https://www.bilibili.com/video/BV1tK421y7rd/)

[How to Set Video Translation Using Gemini Api/Bilibili](https://b23.tv/fED1dS3)

[How to Download and Install](https://www.bilibili.com/video/BV1Gr421s7cN/)


# Software Preview Screenshots

![image](https://github.com/jianchang512/pyvideotrans/assets/3378335/e5089358-a6e5-4989-9a50-1876c51dc2a7)


# Related Projects

[OTT: Local Offline Text Translation Tool](https://github.com/jianchang512/ott)

[Voice Clone Tool: Synthesize Speech with Any Voice Color](https://github.com/jianchang512/clone-voice)

[Voice Recognition Tool: Local Offline Speech-to-Text Tool](https://github.com/jianchang512/stt)

[Vocal Background Music Separator: Vocal and Background Music Separation Tool](https://github.com/jianchang512/vocal-separate)

[Improved version of GPT-SoVITS's api.py](https://github.com/jianchang512/gptsovits-api)


## Acknowledgements

> The main open source projects this program relies on:

1. ffmpeg
2. PySide6
3. edge-tts
4. faster-whisper
5. openai-whisper
6. pydub

