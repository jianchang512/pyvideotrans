[简体中文](docs/README_CN.md)


> ## Recall.ai - Meeting Transcription API
>
> If you’re looking for a transcription API for meetings, consider checking out **[Recall.ai](https://www.recall.ai/product/meeting-transcription-api?utm_source=github&utm_medium=sponsorship&utm_campaign=jianchang512-pyvideotrans)** , an API that works with Zoom, Google Meet, Microsoft Teams, and more. Recall.ai diarizes by pulling the speaker data and separate audio streams from the meeting platforms, which means 100% accurate speaker diarization with actual speaker names.


## Video Translation & Dubbing Tool

This is a powerful **open-source video translation / audio transcription / speech synthesis tool**, dedicated to seamlessly converting videos from one language to another, complete with dubbed audio and subtitles.


## Core Features at a Glance

*   **Fully Automatic Video/Audio Translation**: Intelligently recognizes and transcribes voices in audio/video, generates source language subtitles, translates them to the target language, performs dubbing, and finally merges the new audio and subtitles into the original video—all in one go.
*   **Voice Transcription / Audio & Video to Subtitles**: Batch transcribes human speech from video or audio files into SRT subtitle files with precise time codes.
*   **Speech Synthesis / Text-to-Speech (TTS)**: Utilizes various advanced TTS channels to generate high-quality, natural-sounding voiceovers for your text or SRT subtitle files.
*   **SRT Subtitle Translation**: Supports batch translation of SRT subtitle files, preserving original timestamps and formatting, while providing multiple bilingual subtitle styles.
*   **Real-time Speech-to-Text**: Supports real-time microphone monitoring to convert speech into text.



## How It Works

Before getting started, please ensure you understand the core working mechanism of this software:

**First, the `human voice` in the audio or video is converted into a subtitle file via the [Speech Recognition Channel]. Next, this subtitle file is translated into the target language via the [Translation Channel]. Then, the translated subtitles are used to generate audio via the selected [Dubbing Channel]. Finally, the subtitles, audio, and original video are embedded and aligned to complete the video translation process.**

*   **Can Handle**: Any audio or video containing human speech, regardless of whether it has embedded subtitles.
*   **Cannot Handle**: Videos containing only background music and hardcoded subtitles but no spoken voice. This software also cannot directly extract hardcoded subtitles from video frames.



## Pre-packaged Version (Windows 10/11 Only, MacOS/Linux Use Source Code)

> Packed using PyInstaller. No antivirus evasion or signing has been applied; antivirus software may flag it as a virus. Please add it to your trust list or deploy from source.

0. [Click to download the pre-packaged version](https://github.com/jianchang512/pyvideotrans/releases), unzip it to a directory with **no spaces** in the path, and double-click `sp.exe`.

1. Unzip to an English path, ensuring the path contains no spaces. After unzipping, double-click `sp.exe` (If you encounter permission issues, right-click and run as administrator).

2. **Note**: You must unzip the file before use. Do not run it directly from inside the compressed archive, and do not move the `sp.exe` file to another location after unzipping.



## Source Code Deployment

> [Recommended: Install using `uv`. If you don't have `uv` yet, check the official installation guide.](https://docs.astral.sh/uv/getting-started/installation/)
>
> [Windows users can also check this guide for installing `uv` and `ffmpeg`.](https://pyvideotrans.com/zh/blog/uv-ffmpeg)

1. **Prerequisites for MacOS/Linux**

	**MacOS**: Execute the following commands to install the required libraries:
    ```bash
    brew install libsndfile

    brew install ffmpeg

    brew install git

    brew install python@3.10
    ```
	
	**Linux**: Install `ffmpeg` using `sudo yum install -y ffmpeg` or `apt-get install ffmpeg`.

2. Create a folder with **no spaces or Chinese characters** in its name. Open a terminal in that folder and execute:
	```bash
	git clone https://github.com/jianchang512/pyvideotrans
	cd pyvideotrans
	```
	> Alternatively, download the source code directly from https://github.com/jianchang512/pyvideotrans by clicking the green *Code* button, unzip it, and navigate to the directory containing `sp.py`.

3. Run `uv sync` to install modules. Depending on your network connection, this may take anywhere from a few minutes to over ten minutes. 

4. Run `uv run sp.py` to launch the software interface.


## Source Deployment Troubleshooting

1. By default, the software uses `ctranslate2` version 4.x, which only supports CUDA 12.x. If your CUDA version is lower than 12 and you cannot upgrade, please execute the following commands to uninstall `ctranslate2` and reinstall a compatible version:

```bash
uv remove ctranslate2

uv add ctranslate2==3.24.0
```




## Tutorials and Documentation

Please visit https://pyvideotrans.com



## Software Preview

![](https://pvtr2.pyvideotrans.com/1763635344886_2.png)



## Acknowledgements

> This program relies primarily on the following open-source projects:

1. [ffmpeg](https://github.com/FFmpeg/FFmpeg)
2. [PySide6](https://pypi.org/project/PySide6/)
3. [edge-tts](https://github.com/rany2/edge-tts)
4. [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
5. [openai-whisper](https://github.com/openai/whisper)
6. [pydub](https://github.com/jiaaro/pydub)
6. [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)



