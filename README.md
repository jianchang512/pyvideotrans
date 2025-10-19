[简体中文](docs/README_CN.md)

> **Sponsored Links**
>
> ## Recall.ai - Meeting Transcription API
>
> If you’re looking for a transcription API for meetings, consider checking out [Recall.ai](https://www.recall.ai/product/meeting-transcription-api), an API that works with Zoom, Google Meet, Microsoft Teams, and more. Recall.ai diarizes by pulling the speaker data and separate audio streams from the meeting platforms, which means 100% accurate speaker diarization with actual speaker names.



# Video Translation and Dubbing Tool

This is a powerful **open-source video translation, transcription, and speech synthesis software**, dedicated to seamlessly converting a video from one language to another, complete with dubbing and subtitles.


## Core Features at a Glance

*   **Fully Automatic Video and Audio Translation**: Intelligently recognizes and transcribes speech in audio/video to generate a source language subtitle file, translates it into the target language, creates a dubbed audio track, and finally, synthesizes the new audio and subtitles into the original video in a single, seamless process.
*   **Speech Transcription / Audio-to-Subtitles**: Batch transcribes human speech from video or audio files into accurate, timestamped SRT subtitle files.
*   **Speech Synthesis / Text-to-Speech (TTS)**: Utilizes various advanced TTS channels to generate high-quality, natural-sounding dubbing for your text or SRT subtitle files.
*   **SRT Subtitle File Translation**: Supports batch translation of SRT subtitle files, preserving the original timecodes and formatting, and offers various bilingual subtitle styles.


##  How the Software Works

Before you begin, it's crucial to understand the core workflow of this software:

**First, the `human speech` in the audio or video is processed through a [Speech Recognition Channel] to generate a subtitle file. Then, this subtitle file is translated into the specified target language via a [Translation Channel]. Next, the translated subtitles are used by the selected [Dubbing Channel] to generate dubbed audio. Finally, the subtitles, new audio, and original video are embedded and synchronized to complete the video translation process.**
*   **Can process**: Any audio or video containing human speech, regardless of whether it has embedded subtitles.
*   **Cannot process**: Videos that only contain background music and hard-coded subtitles with no spoken words. This software cannot directly extract hard-coded subtitles from the video frames.



## Pre-packaged Version (For Windows 10/11 only. macOS/Linux users, please follow the source code deployment instructions)

> Packaged with PyInstaller. It has not been code-signed or obfuscated, so antivirus software may flag it as a potential threat. Please add it to your antivirus's allowlist or use the source code deployment method.

0. [Click here to download the pre-packaged version](https://github.com/jianchang512/pyvideotrans/releases). After downloading, extract it to a directory path that contains only English characters and no spaces, then double-click `sp.exe`.

1. Extract to a path containing only English characters and no spaces. After extraction, double-click `sp.exe` (if you encounter permission issues, right-click and run as administrator).

2. Note: You must run the application after extracting it. Do not run it directly from within the compressed archive. Do not move the `sp.exe` file to another location after extraction.



## macOS Source Code Deployment

0. Open a terminal window and execute the following commands one by one.
	
	> Before proceeding, ensure you have Homebrew installed. If not, you need to install it first.
	>
	> Command to install Homebrew:  `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
	>
	> After installation, run: `eval $(brew --config)`
	>

    ```
    brew install libsndfile
    brew install ffmpeg
    brew install git
    brew install python@3.10
    ```

    Continue with:

    ```
    export PATH="/usr/local/opt/python@3.10/bin:$PATH"
    source ~/.bash_profile 
	source ~/.zshrc
    ```



1. Create a folder with a path containing no spaces or Chinese characters, and navigate into it in your terminal.
2. In the terminal, run the command: `git clone https://github.com/jianchang512/pyvideotrans`
3. Run the command: `cd pyvideotrans`
4. Continue with: `python3.10 -m venv venv`
5. Run the command: `source ./venv/bin/activate`. After execution, verify that your terminal prompt now starts with `(venv)`. The following commands must be run while the virtual environment is active.
6. Run `pip3 install -r requirements.txt`. 
7. Run `python3.10 sp.py` to launch the application GUI.



## Linux Source Code Deployment

0. For CentOS/RHEL-based systems, execute the following commands in order to install Python 3.10:

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

1. For Ubuntu/Debian-based systems, execute the following commands to install Python 3.10:

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


**Open a terminal and run `python3 -V`. If it displays "Python 3.10.x", the installation was successful.**


1. Create a folder with a path containing no spaces or Chinese characters, and open a terminal in that directory.
3. In the terminal, run the command: `git clone https://github.com/jianchang512/pyvideotrans`
4. Run the command: `cd pyvideotrans`
5. Continue with: `python3 -m venv venv`
6. Run the command: `source ./venv/bin/activate`. After execution, verify that your terminal prompt now starts with `(venv)`. The following commands must be run while the virtual environment is active.
7. Run `pip3 install -r requirements.txt`. 
8. To enable CUDA acceleration, run the following commands:

    `pip3 uninstall -y torch torchaudio`

    `pip3 install torch torchaudio --index-url https://download.pytorch.org/whl/cu126`

    `pip3 install nvidia-cublas-cu12 nvidia-cudnn-cu12`

9. For Linux, to enable CUDA acceleration, you must have an NVIDIA GPU and a properly configured CUDA 12.x+ environment. Please search for "Linux CUDA installation" for guides.


10. Run `python3 sp.py` to launch the application GUI.




## Deploying with UV: Reference Documentation

- Install `uv` beforehand, then run the command `uv sync` in the project directory.


## Source Deployment Troubleshooting

1. By default, this project uses ctranslate2 version 4.x, which only supports CUDA 12.x. If your CUDA version is lower than 12 and you cannot upgrade, please uninstall ctranslate2 and reinstall a compatible version with the following commands:

```
pip uninstall -y ctranslate2
pip install ctranslate2==3.24.0
```

2. If you encounter an error like `xx module not found`, open the `requirements.txt` file, find the line for the `xx` module, and remove the version specifier (e.g., remove `==1.2.3`).




# Tutorials and Documentation

Please visit https://pyvideotrans.com




# Software Preview

![](https://pvtr2.pyvideotrans.com/1760079781627_image.png)


## Acknowledgments

> This program relies on several key open-source projects:

1. [ffmpeg](https://github.com/FFmpeg/FFmpeg)
2. [PySide6](https://pypi.org/project/PySide6/)
3. [edge-tts](https://github.com/rany2/edge-tts)
4. [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
5. [openai-whisper](https://github.com/openai/whisper)
6. [pydub](https://github.com/jiaaro/pydub)



