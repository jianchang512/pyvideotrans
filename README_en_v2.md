[简体中文](./README.md) / [Donate to the project](./about.md) / [Join Discord](https://discord.gg/TMCM2PfHzQ)

# Video translation and dubbing tools

[Download the Windows pre-compiled version of the exe](https://github.com/jianchang512/pyvideotrans/releases)

>
> It is a video translation dubbing tool that translates a video in one language into a video in a specified language, automatically generates and adds subtitles and dubbing in that language.
>
> Speech recognition is based on `faster-whisper` an offline model
>
> Text translation support `google|baidu|tencent|chatGPT|Azure|Gemini|DeepL|DeepLX` ,
>
> Text-to-speech support `Microsoft Edge tts` `Openai TTS-1` `Elevenlabs TTS`
>

# Primary Uses and Usage

【Translate Video and Dub】Set each option as needed, freely configure the combination, and realize translation and dubbing, automatic acceleration and deceleration, merging, etc

[Extract Subtitles Without Translation] Select a video file and select the source language of the video, then the text will be recognized from the video and the subtitle file will be automatically exported to the destination folder

【Extract Subtitles and Translate】Select the video file, select the source language of the video, and set the target language to be translated, then the text will be recognized from the video and translated into the target language, and then the bilingual subtitle file will be exported to the destination folder

[Subtitle and Video Merge] Select the video, then drag and drop the existing subtitle file to the subtitle area on the right, set the source language and target language to the language of the subtitles, and then select the dubbing type and role to start the execution

【Create Dubbing for Subtitles】Drag and drop the local subtitle file to the subtitle editor on the right, then select the target language, dubbing type, and role, and transfer the generated dubbed audio file to the destination folder

[Audio and Video Text Recognition] Drag the video or audio to the recognition window, and the text will be recognized and exported to SRT subtitle format

[Synthesize Text into Speech] Generate a voiceover from a piece of text or subtitle using a specific dubbing role

Separate Audio from Video Separates video files into audio files and silent videos

【Audio and Video Subtitle Merge】Merge audio files, video files, and subtitle files into one video file

【Audio and Video Format Conversion】Conversion between various formats

【Subtitle Translation】Translate text or SRT subtitle files into other languages

----




https://github.com/jianchang512/pyvideotrans/assets/3378335/c3d193c8-f680-45e2-8019-3069aeb66e01



# Use win to precompile the exe version (other systems use source code for deployment)

0. [Click Download to download the pre-compiled version](https://github.com/jianchang512/pyvideotrans/releases)

1. It is recommended to decompress the data to the English path and the path does not contain spaces. After decompression, double-click sp.exe (if you encounter permission problems, you can right-click to open it with administrator permissions)

3. If no killing is done, domestic killing software may have false positives, which can be ignored or deployed using source code


# Source code deployment

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1yDGPWRyXeZ1GWqkOpdJDv4nA_88HNm01?usp=sharing)


1. Configure the Python 3.9->3.11 environment
2. `git clone https://github.com/jianchang512/pyvideotrans`
3. `cd pyvideotrans`
4. `python -m venv venv`
5. Run under win `%cd%/venv/scripts/activate`, Linux and Mac `source ./venv/bin/activate`
6. `pip install -r requirements.txt`If you encounter a version conflict, use `pip install -r requirements.txt --no-deps` (CUDA is not supported on MacOS, replace requirements.txt with requirements-mac.txt on Mac).
7. Extract ffmpeg.zip to the root directory (ffmpeg .exe file), Linux and Mac Please install ffmpeg by yourself, the specific method can be "Baidu or Google"
8. `python sp.py` Open the software interface
9. If you need to support CUDA acceleration, you need to have an NVIDIA graphics card on the device, see CUDA [Acceleration Support below for specific installation precautions](https://github.com/jianchang512/pyvideotrans?tab=readme-ov-file#cuda-%E5%8A%A0%E9%80%9F%E6%94%AF%E6%8C%81)


# How to use:

1. Original video: Select MP4/AVI/MOV/MKV/MPEG video, you can select multiple videos;

2. Output Video Directory: If you do not select this option, it will be generated in the same directory by default, `_video_out` and two subtitle files in the original language and target language will be created in the SRT folder in this directory

3. Select a translation: Select google|baidu|tencent|chatGPT|Azure|Gemini|DeepL|DeepLX translation channel

4. Web proxy address: If you can't directly access google/chatGPT in your region, you need to set up a proxy in the software interface Web Proxy, for example, if you use v2ray, fill `http://127.0.0.1:10809` in .  If you `http://127.0.0.1:7890`have modified the default port or other proxy software you are using, fill in the information as needed

5. Original Language: Select the language of the video to be translated

6. Target Language: Select the language you want to translate to

7. Select Dubbing: After selecting the target language for translation, you can select the dubbing role from the Dubbing options.
   
   Hard subtitles: Refers to always displaying subtitles, which cannot be hidden, if you want to have subtitles when playing in the web page, please select hard subtitle embedding

   Soft subtitles: If the player supports subtitle management, you can display or close subtitles, but subtitles will not be displayed when playing in the web page, some domestic players may not support it, and you need to put the generated video with the same name srt file and video in a directory to display


8. Speech recognition model: Select base/small/medium/large-v3, the recognition effect is getting better and better, but the recognition speed is getting slower and slower, and the memory required is getting larger and larger, the built-in base model, please download other models separately, unzip and put them in the `当前软件目录/models`directory

   Overall recognition/pre-segmentation: Integral recognition refers to sending the entire voice file directly to the model, which is processed by the model, and the segmentation may be more accurate, but it may also create a single subtitle with a length of 30s, which is suitable for audio with clear mute;  Pre-segmentation means that the audio is cut to a length of about 10 seconds and then sent to the model for processing.

    [All models are available for download](https://github.com/jianchang512/stt/releases/tag/0.0)
    
    After downloading, decompress and copy the models--systran--faster-whisper-xx folder in the compressed package to the models directory

    ![](https://github.com/jianchang512/stt/assets/3378335/5c972f7b-b0bf-4732-a6f1-253f42c45087)
 

    [FFmepg download (the compiled version comes with it).](https://www.ffmpeg.org/)

9. Dubbing speaking rate: fill in the number between -90 and +90, the same sentence in different languages, the time required is different, so the sound and picture subtitles may not be synchronized after dubbing, you can adjust the speaking speed here, negative numbers represent slow speed, positive numbers represent accelerated playback.

10. Audio and video alignment: "Automatic acceleration of voiceover" and "automatic slowing of video" respectively

>
> After translation, different languages have different pronunciation durations, such as a sentence in Chinese 3s, translated into English may be 5s, resulting in inconsistent duration and video.
> 
> There are 2 ways to solve it:
>
>     1. Force voiceovers to speed up playback to shorten voiceover duration and video alignment
> 
>     2. Force the video to play slowly so that the video length is longer and the voice over is aligned.
> 
> You can choose only one of the two
>  
 
  
11. Mute Clip: Enter a number from 100 to 2000, representing milliseconds, and the default is 500, that is, the muted segment greater than or equal to 500ms is used as the interval to split the voice

12. **CUDA Acceleration**: Confirm that your computer's graphics card is an N card, and the CUDA environment and driver have been configured, then enable this option, the speed can be greatly improved, and the specific configuration method is shown in the[ CUDA acceleration support below](https://github.com/jianchang512/pyvideotrans?tab=readme-ov-file#cuda-%E5%8A%A0%E9%80%9F%E6%94%AF%E6%8C%81)

13. TTS: You can use edgeTTS and openai TTS models to select the characters you want to synthesize voice, and openai needs to use the official interface or open the third-party interface of the TTS-1 model

14. Click the Start button at the bottom to display the current progress and logs, and the subtitles will be displayed in the text box on the right

15. After the subtitle parsing is completed, it will pause and wait for the subtitle to be modified, and if you don't do anything, it will automatically move on to the next step after 60s. You can also edit the subtitles in the subtitle area on the right, and then manually click to continue compositing

16. In the subdirectory of the video with the same name in the destination folder, the subtitle SRT file of the two languages, the original voice and the dubbed WAV file will be generated respectively to facilitate further processing

17. Set line role: You can set the pronunciation role for each line in the subtitles, first select the TTS type and role on the left, and then click "Set Line Role" at the bottom right of the subtitle area, and fill in the line number you want to use the role dubbing in the text behind each character name, as shown in the following figure:![](./images/p2.png)
    
# Advanced settings videotrans/set.ini

**Don't adjust it unless you know what's going to happen**

```
; Set the software interface language, where en represents English and zh represents Chinese
lang=

; Number of simultaneous voice acting threads
dubbing_ Thread=5

; Simultaneous translation lines
trans_thread=10

; Software waiting for subtitle modification countdown
countdown_sec=30

; Accelerate device cuvid or cuda
hwaccel=cuvid

; Accelerate device output format, nv12 or cuda
hwaccel_output_format=nv12

; Is hardware decoding used - c: v h264_ Cuvid true represents yes, false represents no
no_code=false

; In speech recognition, the data format is int8, float16, or float32
cuda_com_type=int8

; The number of speech recognition threads, where 0 represents the same number of CPU cores. If it occupies too much CPU, it can be changed to 4 here
whisper_threads=0

; Number of speech recognition work processes
whisper_worker=2

;Reducing these two numbers will use less graphics memory
beam_size=5
best_of=5

;Simultaneous execution quantity in pre split mode
split_threads=4
```



# CUDA acceleration support

**Install the CUDA tool** [for detailed installation methods](https://juejin.cn/post/7318704408727519270)

After installing CUDA, if there is a problem, perform `pip uninstall torch torchaudio torchvision` Uninstall[, then go to https://pytorch.org/get-started/locally/]() according to your OS type and CUDA version, select `pip3` the command,  change  to , `pip`and then copy the command to execute. 
 
After the installation is complete, execute If the `python testcuda.py` output is True, it is available  

Sometimes you get the error "cublasxx .dll does not exist", or you don't get this error, and the CUDA configuration is correct, but the recognition error always appears, you need to download cuBLAS and then copy the dll file to the system directory

[Click to download cuBLAS, ](https://github.com/jianchang512/stt/releases/download/0.0/cuBLAS_win.7z)unzip it, and copy the dll file to C:/Windows/System32


# frequently asked questions

1. Using Google Translate, it says error

   To use the official interface of google or chatGPT in China, you need to hang a ladder

2. A global proxy has been used, but it doesn't look like it's going to be a proxy

   You need to set a specific proxy address in the software interface "Network Proxy", such as http://127.0.0.1:7890

3. Tip: FFmepg does not exist

   First check to make sure that there are ffmpeg.exe, ffprobe.exe files in the root directory of the software, if they do not exist, unzip ffmpeg.7z, and put these 2 files in the root directory of the software

4. CUDA is enabled on windows, but an error is displayed

   A: [First of all, check the detailed installation method, ](https://juejin.cn/post/7318704408727519270)make sure you have installed the cuda related tools correctly, if there are still errors[, click to download cuBLAS](https://github.com/jianchang512/stt/releases/download/0.0/cuBLAS_win.7z), unzip and copy the dll file inside to C:/Windows/System32

   B: If you are sure that it has nothing to do with A, then please check whether the video is H264 encoded mp4, some HD videos are H265 encoded, this is not supported, you can try to convert to H264 video in the "Video Toolbox".

   C: Hardware decoding and encoding of video under GPU requires strict data correctness, and the fault tolerance rate is almost 0, any little error will lead to failure, plus the differences between different versions of graphics card model, driver version, CUDA version, ffmpeg version, etc., resulting in compatibility errors are easy to occur. At present, the fallback is added, and the CPU software is automatically used to encode and decode after failure on the GPU. When a failure occurs, an error message is recorded in the logs directory.

5. Prompts that the model does not exist

   After version 0.985, models need to be reinstalled, and the models directory is a folder for each model, not a pt file.
   To use the base model, make sure that the models/models--Systran--faster-whisper-base folder exists, if it doesn't exist, you need to download it and copy the folder to the models.
   If you want to use a small model, you need to make sure that the models/models--Systran--faster-whisper-small folder exists, if it doesn't exist, you need to download it and copy the folder to models.
   To use the medium model, make sure that the models/models--Systran--faster-whisper-medium folder exists, if it doesn't exist, you need to download it and copy the folder to the models.
   To use the large-v3 model, make sure that the models/models--Systran--faster-whisper-large-v3 folder exists, if it doesn't, you need to download it and copy the folder to the models.

   [All models are available for download](https://github.com/jianchang512/stt/releases/tag/0.0)

6. The directory does not exist or the permission is incorrect

   Right-click on sp..exe to open with administrator privileges

7. An error is prompted, but there is no detailed error information

   Open the logs directory, find the latest log file, and scroll to the bottom to see the error message.

8. The large-v3 model is very slow

   If you don't have an N-card GPU, or you don't have a CUDA environment configured, or the video memory is lower than 4G, please don't use this model, otherwise it will be very slow and stuttering

9. The cublasxx .dll file is missing

   Sometimes you encounter the error "cublasxx .dll does not exist", you need to download cuBLAS and copy the dll file to the system directory

   [Click to download cuBLAS, ](https://github.com/jianchang512/stt/releases/download/0.0/cuBLAS_win.7z)unzip it, and copy the dll file to C:/Windows/System32


10. Background music is lost.

   Only human voices are recognized and saved, so there will be no original background music in the dubbed audio. If you need to retain it, you can use the [voice-background music separation project](https://github.com/jianchang512/vocal-separate) to extract the background music, and then merge it with the dubbed file.

11. How to use custom voice.

   Currently, this feature is not supported. If needed, you can first recognize the subtitles, and then use another [voice cloning project](https://github.com/jiangchang512/clone-voice), enter the subtitle srt file, select the customized voice to synthesize the audio file, and then recreate the video.
   
13. Captions can't be aligned in speech

> After translation, different languages have different pronunciation durations, such as a sentence in Chinese 3s, translated into English may be 5s, resulting in inconsistent duration and video.
> 
> There are 2 ways to solve it:
> 
>     1. Force voiceovers to speed up playback to shorten voiceover duration and video alignment
> 
>     2. Force the video to play slowly so that the video length is longer and the voice over is aligned.
> 
> You can choose only one of the two
   

14. Subtitles do not appear or display garbled characters

> 
> Soft composite subtitles: subtitles are embedded in the video as a separate file, which can be extracted again, and if the player supports it, subtitles can be enabled or disabled in the player's subtitle management;
> 
> Note that many domestic players must put the srt subtitle file and the video in the same directory and the same name in order to load the soft subtitles, and you may need to convert the srt file to GBK encoding, otherwise it will display garbled characters.
> 

15. How to switch the software interface language/Chinese or English

If the set.ini file does not exist in the software directory `videtrans/set.ini`,  `lang=`then fill in the language code`zh`, representing Chinese, `en`representing English, and then restart the software

```

[GUI]
;GUI show language ,set en or zh  eg.  lang=en
lang =

```

# CLI command-line mode

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1yDGPWRyXeZ1GWqkOpdJDv4nA_88HNm01?usp=sharing)


cli.py is a command-line execution script and`python cli.py` is the easiest way to execute it

Parameters received:

`-m mp4`

The specific configuration parameters can be configured in the CLI.ini located in the same directory as cli.py, and other MP4 video addresses to be processed can also be configured by command-line parameters `-m mp4视频绝对地址` , such as `python cli.py -m D:/1.mp4`.

cli.ini is the complete parameters, the first parameter `source_mp4`represents the video to be processed, if the command line passes parameters through -m, then use the command line argument, otherwise use this`source_mp4`

`-c cli.ini file path`

You can also copy cli.ini to another location `-c cli.ini的绝对路径地址` and specify the configuration file to use from the command line  , for example, `python cli.py -c E:/conf/cli.ini` it will use the configuration information in the file and ignore the configuration file in the project directory. 

`-cuda`There is no need to follow the value, just add it to enable CUDA acceleration (if available) `python cli.py -cuda`

Example:`python cli.py -cuda -m D:/1.mp4`

## Specific parameters and descriptions in cli.ini

```
;Command line parameters
;Absolute address of the video to be processed. Forward slash as a path separator, can also be passed after -m in command line parameters
source_mp4=
;Network proxy address, google chatGPT official China needs to be filled in
proxy=http://127.0.0.1:10809
;Output result file to directory
target_dir=
;Video speech language, select from here zh-cn zh-tw en fr de ja ko ru es th it pt vi ar tr
source_language=zh-cn
;Speech recognition language, no need to fill in
detect_language=
;Language to translate to zh-cn zh-tw en fr de ja ko ru es th it pt vi ar tr
target_language=en
;Language when embedding soft subtitles, no need to fill in
subtitle_language=
;true=Enable CUDA
cuda=false
;Role name, role names of openaiTTS "alloy,echo,fable,onyx,nova,shimmer", role names of edgeTTS can be found in the corresponding language roles in voice_list.json. Role names of elevenlabsTTS can be found in elevenlabs.json
voice_role=en-CA-ClaraNeural
; Dubbing acceleration value, must start with + or -, + means acceleration, - means deceleration, ends with %
voice_rate=+0%
;Optional edgetTTS openaiTTS elevenlabsTTS
tts_type=edgeTTS
;Silent segment, unit ms
voice_silence=500
;all=whole recognition, split=pre-split sound segment recognition
whisper_type=all
;Speech recognition model optional, base small medium large-v3
whisper_model=base
;Translation channel, optional google baidu chatGPT Azure Gemini tencent DeepL DeepLX
translate_type=google
;0=Do not embed subtitles, 1=Embed hard subtitles, 2=Embed soft subtitles
subtitle_type=1
;true=Automatic dubbing acceleration
voice_autorate=false
;true=Automatic video slowdown
video_autorate=false
;deepl translation interface address
deepl_authkey=asdgasg
;Interface address of own configured deeplx service
deeplx_address=http://127.0.0.1:1188
;Tencent translation id
tencent_SecretId=
;Tencent translation key
tencent_SecretKey=
;Baidu translation id
baidu_appid=
;Baidu translation key
baidu_miyue=
; key of elevenlabstts
elevenlabstts_key=
;chatgpt api, ending with /v1, third party interface address can be filled in
chatgpt_api=
;key of chatGPT
chatgpt_key=
;chatgpt model, optional gpt-3.5-turbo gpt-4
chatgpt_model=gpt-3.5-turbo
; Azure's api interface address
azure_api=
;key of Azure
azure_key=
; Azure model name, optional gpt-3.5-turbo gpt-4
azure_model=gpt-3.5-turbo
;key of google Gemini
gemini_key=

```

# Screenshot of the software preview

![](./images/p1.png?c)

[Youtube demo](https://youtu.be/-S7jptiDdtc)

# Video Tutorials (Third Party)

[Deploy the source code on Mac/B station](https://b23.tv/RFiTmlA)

[Use Gemini API to set up a method/b station for video translation](https://b23.tv/fED1dS3)


# Related Projects

[Voice Cloning Tool: Synthesize voices with arbitrary timbres](https://github.com/jianchang512/clone-voice)

[Speech recognition tool: A local offline speech recognition to text tool](https://github.com/jianchang512/stt)

[Vocal and background music separation: A minimalist tool for separating vocals and background music, localized web page operations](https://github.com/jianchang512/stt)

## Thanks

> This program mainly relies on some open source projects

1. ffmpeg
2. PyQt5
3. edge-tts
4. faster-whisper


