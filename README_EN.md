[简体中文](./README.md) / [👑 Donate buy me a coffee](https://ko-fi.com/jianchang512) / [Discord](https://discord.gg/TMCM2PfHzQ) / [Twitter](https://twitter.com/mortimer_wang)

# Video Translation and Dubbing Toolkit

>
> This is a video translation and dubbing tool that can translate a video in one language into another language with dubbing and subtitles.
>
> Voice recognition is based on the `faster-whisper` offline model.
>
> Text translation supports `google|baidu|tencent|chatGPT|Azure|Gemini|DeepL|DeepLX|OTT`.
>
> Text-to-speech synthesis supports `Microsoft Edge tts` `Openai TTS-1` `Elevenlabs TTS`
>

<a href="https://www.producthunt.com/products/translation-of-the-video?utm_source=badge-follow&utm_medium=badge&utm_souce=badge-translation&#0045;of&#0045;the&#0045;video" target="_blank"><img src="https://api.producthunt.com/widgets/embed-image/v1/follow.svg?product_id=557901&theme=light" alt="VideoTrans - video&#0032;translator&#0032;and&#0032;dubbing | Product Hunt" style="width: 250px; height: 54px;" width="250" height="54" /></a>


# Main Use Cases and How to Use

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





https://github.com/jianchang512/pyvideotrans/assets/3378335/dd3b6a33-2b64-4cab-b556-79f768b111c5





[Youtube demo](https://youtu.be/-S7jptiDdtc)



# Usage of Precompiled EXE Version

0. Only available for win10 win11 systems/Mac needs to compile from source code

1. [Click to download the latest version from release](https://github.com/jianchang512/pyvideotrans/releases), decompress, double click sp.exe


# Source Code Deployment

1. Set up the Python 3.9->3.11 environment.
2. `git clone https://github.com/jianchang512/pyvideotrans`
3. `cd pyvideotrans`
4. `python -m venv venv`
5. For Windows, run `%cd%/venv/scripts/activate`; for Linux and Mac, run `source ./venv/bin/activate`.
6. `pip install -r requirements.txt`
 
windows & linux if want use cuda，continue exec `pip uninstall -y torch`，then `pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cu121`

7. For Windows, unzip ffmpeg.zip to the root directory (ffmpeg.exe file); for Linux and Mac, Manually installing ffmpeg on your own
8. Open the software interface by running `python sp.py`.
9. If CUDA acceleration support is needed, the device must have an NVIDIA GPU. For specific installation steps, see [CUDA Acceleration Support](https://github.com/jianchang512/pyvideotrans?tab=readme-ov-file#cuda-%E5%8A%A0%E9%80%9F%E6%94%AF%E6%8C%81).



# Instructions for use

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

    [download models](https://github.com/jianchang512/stt/releases/tag/0.0)
    
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
    
18. Preserve Background Music: If this option is selected, the software will first separate the human voices and background accompaniment in the video. The background accompaniment will ultimately be merged with the voice-over audio. As a result, the final video will retain the background accompaniment. **Note**: This function is based on uvr5. If you do not have sufficient Nvidia GPU memory, such as 8GB or more, we recommend caution as this may be very slow and highly resource-intensive.

19.  Original voice clone dubbing: First install and deploy [clone voice](https://github.com/jianchang512/clone-voice) Project, download and configure the "text->speech" model, then select "clone-voice" in the TTS type in this software, and select "clone" for the dubbing role to achieve dubbing using the sound from the original video. When using this method, to ensure the effect, "separation of vocals and background music" will be mandatory. Please note that this feature is slow and consumes system resources.

20. You can modify the prompt words for chatGPT, AzureGPT, and Gemini Pro in the `videotrans/chatgpt.txt`, `videotrans/azure.txt`, and `videotrans/gemini.txt` files respectively. You must pay attention to the `{lang}` in the files, which represents the target language of translation. Do not delete or modify it. The prompt words should ensure that AI is informed to return the content after translation line by line, and the number of lines returned should be consistent with the number of lines given to it.


# Advanced Settings videotrans/set.ini

**Please do not make arbitrary adjustments unless you know what will happen**


```


;GUI show language ,set en or zh  eg.  lang=en
;默认界面跟随系统，也可以在此手动指定，zh=中文界面，en=英文界面
lang =

;0=video lossless processing but slow processing due to large size, 51=fast processing due to small size but lowest quality, default to 13
;视频处理质量，0-51的整数，0=无损处理尺寸较大速度很慢，51=质量最低尺寸最小处理速度最快
crf=13

;dubbing thread at same time, > 5 or greater may be forbid by api
;同时配音的数量，1-10，建议不要大于5，否则容易失败
dubbing_thread=5

;Simultaneous translation lines
;同时翻译的数量，1-20，不要太大，否则可能触发翻译api频率限制
trans_thread=15

;countdown sec
;字幕识别完成等待翻译前的暂停秒数，和翻译完等待配音的暂停秒数
countdown_sec=30

;Accelerator cuvid or cuda
;硬件编码设备，cuvid或cuda
hwaccel=cuvid

; Accelerator output format = cuda or nv12
;硬件输出格式，nv12或cuda
hwaccel_output_format=nv12

;not decode video before use -c:v h264_cuvid,false=use -c:v h264_cuvid, true=dont use
;是否禁用硬件解码，true=禁用，兼容性好；false=启用，可能某些硬件上有兼容错误
no_decode=true

;cuda data type int8 float16 float32, More and more graphics memory is being occupied
;从视频中识别字幕时的cuda数据类型，int8=消耗资源少，速度快，精度低，float32=消耗资源多，速度慢，精度高，int8_float16=设备自选
cuda_com_type=int8

; whisper thread 0 is equal cpu core, 
;字幕识别时，cpu进程
whisper_threads=4

;whisper num_worker
;字幕识别时，同时工作进程
whisper_worker=1

;Reducing these two numbers will use less graphics memory
;字幕识别时精度调整，1-5，1=消耗资源最低，5=消耗最多，如果显存充足，可以设为5，可能会取得更精确的识别结果
beam_size=1
best_of=1

;vad set to false,use litter GPU memory,true is more
;字幕识别时启用自定义静音分割片段，true=启用，显存不足时，可以设为false禁用
vad=true

;0 is use litter GPU,other is more
;0=占用更少GPU资源，1=占用更多GPU
temperature=0

;false is litter GPU,ture is more
;同 temperature, true=占用更多GPU，false=占用更少GPU
condition_on_previous_text=false


```



# Frequently Asked Questions

1. Using Google Translation, error is prompted.

   Domestically, using Google or the official interface of chatGPT requires a VPN.

2. Have used global proxy, but it doesn't seem to be going through proxy.

   Need to set specific proxy address in software interface "network proxy", such as http://127.0.0.1:7890

3. Prompting that FFmpeg does not exist.

   First, make sure there are ffmpeg.exe and ffprobe.exe files in the root directory of the software. If not, unzip ffmpeg.7z and put these two files in the root directory of the software.

4. CUDA is enabled on Windows, but errors are prompted.

   A: Firstly, refer to the [detailed installation method](https://juejin.cn/post/7318704408727519270) and confirm that you have successfully installed the related cuda tools. If errors still exist, [click here to download cuBLAS](https://github.com/jianchang512/stt/releases/download/0.0/cuBLAS_win.7z). After unzipping it, copy the dll files to C:/Windows/System32.

   B: If you are sure it is not related to A, check if the video is H264 encoded mp4. Some HD videos are H265 encoded, which is not supported. You can try to convert to H264 video in the "Video Toolbox".

5. Prompting that the model does not exist.

   After version 0.985, the model needs to be reinstalled. The folder under models directory is the folder of each model, not just pt files.
To use the base model, ensure that the models/models--Systran--faster-whisper-base directory exists. If it does not, download it and copy this directory to models. Similarly for small, medium, and large-v3 models.

   [Complete model download link](https://github.com/jianchang512/stt/releases/tag/0.0)

6. Prompting the directory does not exist or permission error.

   Right-click on sp.exe and open with administrator permission.

7. Prompting error, but no detailed error message.

   Open logs directory, look for the latest log file, scroll to the bottom to see error messages.

8. The large-v3 model is very slow.

   If you do not have a GPU, or have not set up the CUDA environment properly, or your GPU memory is less than 4G, please do not use this model, otherwise it will be very slow and lagging.

9. Prompting missing cublasxx.dll file.

   Sometimes you may encounter an error saying "cublasxx.dll does not exist", then you need to download cuBLAS and copy the dll file to the system directory.

   [Click here to download cuBLAS](https://github.com/jianchang512/stt/releases/download/0.0/cuBLAS_win.7z). Extract it and copy the dll files to C:/Windows/System32.
   
   [cuBLAS.and.cuDNN_win_v4](https://github.com/Purfview/whisper-standalone-win/releases/download/libs/cuBLAS.and.cuDNN_win_v4.7z)


11. How to use custom voice.

   Currently, this feature is not supported. If needed, you can first recognize the subtitles, and then use another [voice cloning project](https://github.com/jiangchang512/clone-voice), enter the subtitle srt file, select the customized voice to synthesize the audio file, and then recreate the video.

13. Subtitle voice cannot be aligned.

> Duration of pronunciation in different languages may vary after translation. For example, a sentence in Chinese may take 3s, in English could take 5s, leading to inconsistency in duration with the video.
>
> There are two solutions:
>
>     1. Force dubbing playback speeding up to shorten the duration to align with the video.
>
>     2. Force video to play at a slower speed to extend the duration to align with the dubbing.
>
> Can only choose one of two.

14. Subtitles do not display or display gibberish.

>
> Using soft synthesized subtitles: Subtitles are embedded into the video as separate files and can be extracted again. If the player supports it, you can enable or disable subtitles in the player's subtitle management.
>
> Note that many domestic players must put the srt subtitle file in the same directory as the video file and have the same name in order to load soft subtitles. Also, you might need to convert the srt file to GBK encoding, otherwise, gibberish will be displayed.
>

15. How to switch the software interface language/Chinese or English.

If there is no set.ini file in the software directory, create one first, then paste the following code into it, fill in the language code after `lang=`, `zh` stands for Chinese, `en` stands for English, then restart the software

```
[GUI]
;GUI show language ,set en or zh  eg.  lang=en
lang =

```

16. Crash before completion 

If CUDA is enabled and the computer has installed the CUDA environment, but CUDNN has not been manually installed and configured, this issue will occur. Please install CUDNN that matches CUDA. For example, if you have installed cuda12.3, you need to download the cudnn for cuda12. x compressed package, and then unzip the three folders inside and copy them to the cuda installation directory. Specific tutorial reference
https://juejin.cn/post/7318704408727519270

If cudnn crashes even after being installed according to the tutorial, there is a high probability that the GPU memory is insufficient. You can switch to using the medium model. When the memory is less than 8GB, try to avoid using the largev-3 model, especially when the video is larger than 20MB, otherwise it may run out of memory and crash


# CLI Command Line Mode

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1yDGPWRyXeZ1GWqkOpdJDv4nA_88HNm01?usp=sharing)

cli.py is a script executed from the command line and `python cli.py` is the simplest way to execute it.

Received parameters:

`-m absolute address of mp4 video`

The specific configuration parameters can be configured in cli.ini located in the same directory as cli.py. The address of other mp4 videos to be processed can also be configured by command line parameter `-m absolute address of mp4 video`, such as `python cli.py -m D:/1.mp4`.

The complete parameters are in cli.ini, the first parameter `source_mp4` represents the video to be processed. If the command line passes parameters through -m, the command line parameter will be used, otherwise, `source_mp4` will be used.

`-c configuration file address`

You can also copy cli.ini to another location and specify the configuration file to be used through `-c absolute path address of cli.ini` on the command line, such as `python cli.py -c E:/conf/cli.ini`, which will use the configuration information in this file and ignore the configuration file in the project directory.

`-cuda` does not need to follow the value, as long as it is added, it means to enable CUDA acceleration (if available) `python cli.py -cuda`

Example:`python cli.py -cuda -m D:/1.mp4`



## Specific parameters and explanations within cli.ini

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

# CUDA Acceleration Support

**[Install CUDA Toolkit article](https://juejin.cn/post/7318704408727519270)**


Both cuda and cudnn must be installed properly, otherwise it may crash.
After installing CUDA, if there are any issues, execute 'pip uninstall y torch', then execute 'pip install torch=2.1.2-- index URL' https://download.pytorch.org/whl/cu121 `.

after installed，executable `python testcuda.py`, if output all is True, its ok, else reinstall

if alert "not exists cublasxx.dll", [click to download cuBLAS](https://github.com/jianchang512/stt/releases/download/0.0/cuBLAS_win.7z)，extract and copy dll to C:/Windows/System32





# Software Preview Screenshots

![image](https://github.com/jianchang512/pyvideotrans/assets/3378335/06c4f47c-3f3d-4f01-a3a3-85077d4ba64d)

[Youtube](https://youtu.be/0Qo6nw2OCg4)


# Comparison of Videos Before and After

[Demo original video and translated video](https://www.wonyes.org/demo.html)




# Acknowledgements

> Some open source projects this program relies on (part of)

1. ffmpeg
2. PyQt5
3. edge-tts
4. faster-whisper
