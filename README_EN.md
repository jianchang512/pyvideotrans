[简体中文](./README.md) / [👑 Donate buy me a coffee](https://ko-fi.com/jianchang512) / [Discord](https://discord.gg/TMCM2PfHzQ) / [Twitter](https://twitter.com/mortimer_wang)
## Video Translation and Dubbing Toolkit

>
> This is a video translation and dubbing tool that can translate a video in one language into another language with dubbing and subtitles.
>
> Voice recognition is based on the `openai-whisper` offline model.
>
> Text translation supports `google|baidu|tencent|chatGPT|Azure|Gemini|DeepL|DeepLX`.
>
> Text-to-speech synthesis supports `Microsoft Edge tts` `Openai TTS-1`.
>

## Main Use Cases and How to Use

【Translate Video and Dub】Set each option as needed, freely configure combinations to achieve translation and dubbing, automatic speed increase or decrease, merging, etc

【Extract Subtitles Without Translation】Select video files, select the video source language, then recognize the text from the video and automatically export subtitle files to the target folder

【Extract Subtitles and Translate】Select a video file, select the video source language, set the desired translation target language, then recognize the text from the video and translate it into the target language, then export bilingual subtitle files to the target folder

【Subtitles and Video Merging】Select the video, then drag the existing subtitle file to the right subtitle area, set both the source and target languages to the language used in the subtitles, then select the dubbing type and role, and start execution

【Creating Dubbing for Subtitles】Drag local subtitle files to the right subtitle editor, then select the target language, dubbing type and role, the dubbed audio file will be generated in the target folder

【Text Recognition for Audio and Video】Drag the video or audio to the recognition window, it will recognize the text and export it in the form of srt subtitles

【Text to Speech Synthesis】Generate a dubbing for a piece of text or subtitle using a specified dubbing role

【Separate Audio from Video】Separate video files into audio files and silent videos

【Audio, Video, and Subtitle Merging】Merge audio files, video files, and subtitle files into one video file

【Audio and Video Format Conversion】Conversion between various formats
【Text and srt Translation】Text and srt Translation to other language




https://github.com/jianchang512/pyvideotrans/assets/3378335/e02cf259-95d1-4044-85ca-0bb70c808145


[Youtube demo](https://youtu.be/-S7jptiDdtc)


## Usage of Precompiled EXE Version

[EXE Version Download Link](https://github.com/jianchang512/pyvideotrans/releases)

0. Only available for win10 win11 systems/Mac needs to compile from source code

1. [Download the latest version from release](https://github.com/jianchang512/pyvideotrans/releases), decompress, double click sp.exe


## Source Code Deployment

1. Set up the Python 3.9->3.11 environment.
2. `git clone https://github.com/jianchang512/pyvideotrans`
3. `cd pyvideotrans`
4. `python -m venv venv`
5. For Windows, run `%cd%/venv/scripts/activate`; for Linux and Mac, run `source ./venv/bin/activate`.
6. `pip install -r requirements.txt`, if version conflict error occurred, please executable `pip install -r requirements.txt --no-deps`
7. For Windows, unzip ffmpeg.zip to the root directory (ffmpeg.exe file); for Linux and Mac, download the corresponding version of ffmpeg from the [ffmpeg official website](https://ffmpeg.org/download.html), unzip it to the root directory, and make sure to place the executable file ffmepg directly in the root directory.
8. Open the software interface by running `python sp.py`.
9. If CUDA acceleration support is needed, the device must have an NVIDIA GPU. For specific installation steps, see [CUDA Acceleration Support](https://github.com/jianchang512/pyvideotrans?tab=readme-ov-file#cuda-%E5%8A%A0%E9%80%9F%E6%94%AF%E6%8C%81).



## Instructions for use

1. Original Video: Choose mp4/avi/mov/mkv/mpeg videos, you can select multiple videos;

2. Output Video Directory: If not selected, it will be generated in `_video_out` in the same directory by default, and two types of subtitle files in the source and target languages will be created in the srt folder in that directory

3. Select Translation: Google|Baidu|Tencent|ChatGPT|Azure|Gemini|DeepL|DeepLX translation channels can be selected

4. Network Proxy Address: If your region cannot directly access Google/ChatGPT, you need to set a proxy in the software interface network proxy. For example, if you use v2ray, fill in `http://127.0.0.1:10809`, if clash, fill in `http://127.0.0.1:7890`. If you have changed the default port or are using other proxy software, fill it in as needed

5. Video Original Language: Select the language type in the video to be translated

6. Translation Target Language: Select the language type you hope to translate into

7. Select Dubbing: After selecting the translation target language, you can select the dubbing role from the dubbing options;
   
   Hard Subtitles: Permanently display subtitles that cannot be hidden, if you want subtitles when playing on the web page, please choose hard subtitles embedded

   Soft Subtitles: If the player supports subtitle management, it can display or hide subtitles, this method will not display subtitles when playing on the web page, some domestic players may not support it, need to put the generated video and the same name srt file and video in one directory to display


8. Voice recognition model: Select base/small/medium/large/large-v3, the recognition effect is getting better and better, but the recognition speed is getting slower and slower, and more memory is needed, the first time will need to download the model, default base, can download the model separately in advance Put it in the `current software directory/models` directory.

   Whole recognition / pre-segmentation: whole recognition refers to directly sending the whole voice file to the model for processing, segmentation may be more accurate, but it may also make a single subtitle of 30s length, suitable for audio with clear silence; pre-segmentation refers to the audio in advance It is cut into about 10s length and then sent to the model for processing separately.

   **Single download address for model**

    [tiny model](https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt)
    
    [base model](https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt)

    [small model](https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt)

    [medium model](https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt)

    [large model](https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a/large.pt)

    [large-v3 model](https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt)

    [VLC decoder download](https://www.videolan.org/vlc/)

    [FFmepg download (compiled version included)](https://www.ffmpeg.org/)

9. Dubbing speed: Fill in a number between -90 and +90, the same sentence under different language voices, the required time is different, so after dubbing, the sound and picture subtitles may be out of sync, you can adjust the language speed here, negative numbers represent Slow down, positive numbers represent accelerated playback.

10. Audio and video alignment: They are "dubbing automatic acceleration" and "video automatic slowdown"

> 
> The pronunciation duration in different languages after translation is different. For example, a sentence in Chinese is 3s, which may be 5s when translated into English, leading to inconsistent duration and video.
> 
> 2 solutions:
>
>     1. Forced dubbing to speed up and play, in order to shorten the dubbing duration and align with the video
> 
>     2. Forced video to play slowly, in order to prolong the video duration and align with the dubbing.
> 
> Only one of the two can be chosen
>  

  
11. Silent Segment: Fill in a number between 100 and 2000, in milliseconds, default is 500, that is, voice is divided into sections with silent segments of 500ms or more

12. **CUDA Acceleration**: Confirm that your computer's graphics card is an N card and that the CUDA environment and drivers have been properly configured, then turn on this option for greatly improved speed. For the specific configuration method, see below [CUDA Acceleration Support](https://github.com/jianchang512/pyvideotrans?tab=readme-ov-file#cuda-%E5%8A%A0%E9%80%9F%E6%94%AF%E6%8C%81)

13. TTS: Available in edgeTTS and openai TTS model, choose the role to synthesize the voice, openai needs to use the official interface or a third-party interface that has opened up the tts-1 model

14. Click the start button to display the current progress and log at the bottom, and the subtitle is displayed in the right text box

15. After the subtitle analysis is completed, it will pause and wait for the subtitle to be modified. If no operation is performed, it will automatically continue the next step after 60s. You can also edit the subtitle in the right subtitle area and then manually click to continue synthesis

16. In the subfolder of the software directory, find the srt folder with the same name as the video file to generate two files, the suffix is the original language and the target language text subtitle file.

17. Set line role：You can set the pronunciation role for each line in the subtitle. First, select the TTS type and role on the left, and then click "Set line role" in the lower right corner of the subtitle area. In the text after each character name, fill in the line number that you want to use for dubbing, as shown in the following figure:

    ![](./images/pen2.png)


## Notes:

**Subtitle Display Problem**
>
> When using soft combined subtitles: The subtitles are embedded in the video as separate files, can be extracted again, and can be enabled or disabled in the player's subtitle management if the player supports it.
>
> Please note that many domestic players require the srt subtitle file and the video to be placed in the same directory and named the same to load the soft subtitles, and the srt file may need to be converted to GBK encoding, otherwise it will display garbled characters.
>

**Subtitle Voice Alignment Problem**

> The pronunciation duration may vary in different languages after translation. For example, a sentence in Chinese is 3s, but when translated into English, it might take 5s, resulting in an inconsistency with the video duration.
>
> There are two solutions:
>
>     1. Force dubbing to play faster to shorten the dubbing duration and align with the video.
>
>     2. Force the video to play slower to extend the video duration and align with the dubbing.
>
> You can only choose one of the two.


**Background Music Issue**

The tool only recognizes vocals and saves vocals, meaning there will be no original background music in the audio after dubbing. If you need to retain the background music, please use the [Vocal Background Music Separation Project](https://github.com/jianchang512/vocal-separate) to extract the background music and then merge it with the dubbing file.

**Language Cloning and Custom Voice**

Currently, this feature is not supported. If needed, you can first recognize the subtitles, then use another [voice cloning project](https://github.com/jiangchang512/clone-voice), input the subtitle srt file, choose a custom voice to synthesize into an audio file, and then generate a new video.



**Issues with large/large-v3 models**

If you don't have a NVIDIA GPU or if you didn't configure the CUDA environment correctly, do not use these two models, as they will be very slow and laggy.

**Prompt ffmpeg error**
If you have enabled CUDA and encountered this problem, please update the display card driver and then reconfigure the CUDA environment.



## CUDA Acceleration Support

**Install CUDA Toolkit**

If your computer is equipped with a Nvidia graphics card, you should first upgrade your graphics card driver to the latest version, then install the corresponding [CUDA Toolkit 11.8](https://developer.nvidia.com/cuda-downloads) and [cudnn for CUDA11.X](https://developer.nvidia.com/rdp/cudnn-archive).

After successful installation, press `Win + R`, type `cmd` and press Enter, then type `nvcc --version` in the pop-up window to confirm that the version information is displayed. Similar to this picture ![image](https://github.com/jianchang512/pyvideotrans/assets/3378335/e68de07f-4bb1-4fc9-bccd-8f841825915a)

Then continue to type `nvidia-smi`, confirm that there's output information and that you can see the cuda version number. Similar to this picture ![image](https://github.com/jianchang512/pyvideotrans/assets/3378335/71f1d7d3-07f9-4579-b310-39284734006b)

If the installation is correct, the precompiled version can now be used with CUDA. If not, you need to reinstall.

## Software Preview Screenshots

![](./images/pen1.png?d)

## Comparison of Videos Before and After

[Demo original video and translated video](https://www.wonyes.org/demo.html)




## Acknowledgements

> This program relies on these open source projects:

1. pydub
2. ffmpeg
3. PyQt5
4. SpeechRecognition
5. edge-tts
6. openai-whisper
