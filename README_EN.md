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
> Allows to keep background backing music etc. (based on uvr5) Turkish, Hungarian, Hindi
>
> Supported languages: Chinese Simplified and Traditional, English, Korean, Japanese, Russian, French, German, Italian, Spanish, Portuguese, Vietnamese, Thai, Arabic, Turkish, Hungarian, Hindi
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



[Youtube demo](https://www.youtube.com/playlist?list=PLVWPFvHklPATE7g3z18JWybF95-ODSDD9)



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

    **Special Note**

    Master model: If you download the master model, unzip it after downloading and copy the "models--Systran--faster-whisper-xx" folder into the models directory, the list of folders in the models directory after unzipping and copying is as follows
    ![](https://github.com/jianchang512/stt/assets/3378335/5c972f7b-b0bf-4732-a6f1-253f42c45087)

    Openai models: If you download openai models, you can copy the .pt file directly to the models folder.


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

;####################
;#######################
;如果你不确定修改后将会带来什么影响，请勿随意修改，修改前请做好备份， 如果出问题请恢复
;If you are not sure of the impact of the modification, please do not modify it, please make a backup before modification, and restore it if something goes wrong.

;升级前请做好备份，升级后按照原备份重新修改。请勿直接用备份文件覆盖，因为新版本可能有新增配置
;Please make a backup before upgrading, and re-modify according to the original backup after upgrading. Please don't overwrite the backup file directly, because the new version may have added

;The default interface follows the system and can also be specified manually here, zh=Chinese interface, en=English interface.
;默认界面跟随系统，也可以在此手动指定，zh=中文界面，en=英文界面
lang =

;Video processing quality, integer 0-51, 0 = lossless processing with large size is very slow, 51 = lowest quality with smallest size is the fastest processing speed
;视频处理质量，0-51的整数，0=无损处理尺寸较大速度很慢，51=质量最低尺寸最小处理速度最快
crf=13

;The number of simultaneous voiceovers, 1-10, it is recommended not to be greater than 5, otherwise it is easy to fail
;同时配音的数量，1-10，建议不要大于5，否则容易失败
dubbing_thread=2

;Maximum audio acceleration, default 0, i.e. no limitation, you need to set a number greater than 1-100, such as 1.5, representing the maximum acceleration of 1.5 times, pay attention to how to set the limit, then the subtitle sound will not be able to be aligned
;音频最大加速倍数，默认0，即不限制，需设置大于1-100的数字，比如1.5，代表最大加速1.5倍，注意如何设置了限制，则字幕声音将无法对齐
audio_rate=0

;Maximum permissible slowdown times of the video frequency, default 0, that is, no restriction, you need to set a number greater than 1-20, for example, 1 = on behalf of not slowing down, 20 = down to 1/20 = 0.05 the original speed, pay attention to how to set up the limit, then the subtitles and the screen will not be able to be aligned
;视频频最大允许慢速倍数，默认0，即不限制，需设置大于1-20的数字，比如1=代表不慢速，20=降为1/20=0.05原速度，注意如何设置了限制，则字幕和画面将无法对齐
video_rate=0

;Number of simultaneous translations, 1-20, not too large, otherwise it may trigger the translation api frequency limitation
;同时翻译的数量，1-20，不要太大，否则可能触发翻译api频率限制
trans_thread=15

;Hard subtitles can be set here when the subtitle font size, fill in the integer numbers, such as 12, on behalf of the font size of 12px, 20 on behalf of the size of 20px, 0 is equal to the default size
;硬字幕时可在这里设置字幕字体大小，填写整数数字，比如12，代表字体12px大小，20代表20px大小，0等于默认大小
fontsize=14


;Number of translation error retries
;翻译出错重试次数
retries=5

;chatGPT model list
;可供选择的chatGPT模型，以英文逗号分隔
chatgpt_model=gpt-3.5-turbo,gpt-4,gpt-4-turbo-preview

;When separating the background sound, cut the clip, too long audio will exhaust the memory, so cut it and separate it, unit s, default 1800s, i.e. half an hour.
;背景音分离时切分片段，太长的音频会耗尽显存，因此切分后分离，单位s,默认 600s
separate_sec=600

;The number of seconds to pause before subtitle recognition is completed and waiting for translation, and the number of seconds to pause after translation and waiting for dubbing.
;字幕识别完成等待翻译前的暂停秒数，和翻译完等待配音的暂停秒数
countdown_sec=30

;Accelerator cuvid or cuda
;硬件编码设备，cuvid或cuda
hwaccel=cuvid

; Accelerator output format = cuda or nv12
;硬件输出格式，nv12或cuda
hwaccel_output_format=nv12

;not decode video before use -c:v h264_cuvid,false=use -c:v h264_cuvid, true=dont use
;Whether to disable hardware decoding, true=disable, good compatibility; false=enable, there may be compatibility errors on some hardware.
;是否禁用硬件解码，true=禁用，兼容性好；false=启用，可能某些硬件上有兼容错误
no_decode=true

;cuda data type when recognizing subtitles from video, int8 = consumes fewer resources, faster, lower precision, float32 = consumes more resources, slower, higher precision, int8_float16 = device of choice
;从视频中识别字幕时的cuda数据类型，int8=消耗资源少，速度快，精度低，float32=消耗资源多，速度慢，精度高，int8_float16=设备自选
cuda_com_type=float32

;中文语言的视频时，用于识别的提示词，可解决简体识别为繁体问题。但注意，有可能直接会将提示词作为识别结果返回
initial_prompt_zh=

; whisper thread 0 is equal cpu core, 
;字幕识别时，cpu进程
whisper_threads=4

;whisper num_worker
;字幕识别时，同时工作进程
whisper_worker=1

;Subtitle recognition accuracy adjustment, 1-5, 1 = consume the lowest resources, 5 = consume the most, if the video memory is sufficient, can be set to 5, may achieve more accurate recognition results
;字幕识别时精度调整，1-5，1=消耗资源最低，5=消耗最多，如果显存充足，可以设为5，可能会取得更精确的识别结果
beam_size=5
best_of=5

;Enable custom mute segmentation when in subtitle overall recognition mode, true=enable, can be set to false to disable when video memory is insufficient.
;字幕整体识别模式时启用自定义静音分割片段，true=启用，显存不足时，可以设为false禁用
vad=true

;0 = less GPU resources but slightly worse results, 1 = more GPU resources and better results
;0=占用更少GPU资源但效果略差，1=占用更多GPU资源同时效果更好
temperature=1

;Same as temperature, true=better with more GPUs, false=slightly worse with fewer GPUs.
;同 temperature, true=占用更多GPU效果更好，false=占用更少GPU效果略差
condition_on_previous_text=true

; For pre-split and equal-division, the minimum silence segment ms to be used as the basis for cutting, default 500ms, i.e., only silence greater than or equal to 500ms will be segmented.
;用于 预先分割 和 均等分割时，作为切割依据的最小静音片段ms，默认500ms，即只有大于等于500ms的静音处才分割
voice_silence=500

;Seconds per slice for equal-division, default 10s, i.e. each subtitle is approximately 10s long.
;用于均等分割时的每个切片时长 秒，默认 10s,即每个字幕时长大约都是10s
interval_split=10

;CJK subtitle number of characters in a line length, more than this will be line feed.
;中日韩字幕一行长度字符个数，多于这个将换行
cjk_len=30

;Other language line breaks, more than this number of characters will be a line break.
;其他语言换行长度，多于这个字符数量将换行
other_len=60


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

   [Address for all model downloads](https://github.com/jianchang512/stt/releases/tag/0.0)

    **The models are divided into two categories:**

    One is for "Faster Models".

    After downloading and unzipping, you will see a folder like "models--Systran--faster-whisper-xxx", xxx stands for the model name, such as base/small/medium/large-v3, etc. After unzipping, you can directly copy the folder to this directory. After unzipping, copy the folder directly to this directory.

    If all the master models are downloaded, you should see these folders under the current models folder

    models--Systran--faster-whisper-base
    models--Systran--faster-whisper-small
    models--Systran--faster-whisper-medium
    models--Systran--faster-whisper-large-v2
    models--Systran-faster-whisper-large-v3


    The other type is for "openai models", after downloading and unzipping, it is directly xx.pt file, such as base.pt/small.pt,/medium.pt/large-v3.pt, directly copy the pt file to this folder.

    If all openai models are downloaded, you should see base.pt, small.pt, medium.pt, large-v1.pt, large-v3.pt directly in the current models folder.


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




17. How to adjust subtitle font size

If you are embedding hard subtitles, you can adjust the font size by changing the fontsize=0 in videotrans/set.ini to an appropriate value. 0 is the default size, 20 means the font size is 20 pixels.



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

![image](https://github.com/jianchang512/pyvideotrans/assets/3378335/38494396-1be7-4fbe-803a-624a208431f5)


[Youtube](https://www.youtube.com/playlist?list=PLVWPFvHklPATE7g3z18JWybF95-ODSDD9)


# Comparison of Videos Before and After

[Demo original video and translated video](https://www.wonyes.org/demo.html)




# Acknowledgements

> Some open source projects this program relies on (part of)

1. ffmpeg
2. PyQt5
3. edge-tts
4. faster-whisper
