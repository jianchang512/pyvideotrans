[English Readme](./README_EN.md)  /  [👑Donate to this project](./about.md) 

# Video Translation and Dubbing Tool

>
> This is a video translation and dubbing tool that can translate a video from one language to a specified language, automatically generating and adding subtitles and dubbing in that language.
>
> Voice recognition uses `faster-whisper` `openai-whisper` offline models.
>
> Text translation supports `microsoft | google | baidu | tencent | chatGPT | Azure | Gemini | DeepL | DeepLX | Offline translation OTT`,
>
> Text-to-speech synthesis supports `Microsoft Edge tts` `Openai TTS-1` `Elevenlabs TTS` `Custom TTS server API` `GPT-SoVITS` [clone-voice](https://github.com/jianchang512/clone-voice)
>
> Allows retaining background accompaniment music, etc. (based on uvr5)
> 
> Supported languages: Simplified and Traditional Chinese, English, Korean, Japanese, Russian, French, German, Italian, Spanish, Portuguese, Vietnamese, Thai, Arabic, Turkish, Hungarian, Hindi

# Main Uses and How to Use

【Translate videos and dubbing】Set various options as needed, freely configure combinations, to achieve translation and dubbing, automatic acceleration/deceleration, merging, etc.

【Recognize subtitles without translation】Select a video file, choose the source language of the video, and then 【recognize text from video voice】and automatically export subtitle files to the target folder.

【Extract subtitles and translate】Select a video file, choose the source language, set the target language you want to translate to, then 【recognize text from video voice】and translate it to the target language, then export bilingual subtitle files to the target folder.

【Combine subtitles and video】Select a video, then drag and drop existing subtitle files to the right-hand subtitle area, set both the source and target languages to the language used in the subtitles, then choose the dubbing type and character, and start execution.

【Create dubbing for subtitles】Drag and drop local subtitle files to the right-side subtitle editor, then choose the target language, dubbing type and character, to generate the dubbed audio file to the target folder.

【Recognize text from audio and video】Drag and drop videos or audios to the recognition window, to recognize the text and export it in SRT subtitle format.

【Synthesize speech from text】Take a section of text or subtitles, and use the specified dubbing character to generate dubbing.

【Separate audio from video】Separate video files into audio files and silent videos.

【Combine audio, video, and subtitles】Merge audio files, video files, and subtitle files into one video file.

【Audio and video format conversion】Mutual conversion between various formats.

【Text subtitle translation】Translate text or SRT subtitle files into other languages.

【Separate vocal and background music】Separate the human voice and background music in the video into two audio files.

【Download YouTube videos】Download videos from YouTube.

----

https://github.com/jianchang512/pyvideotrans/assets/3378335/dd3b6a33-2b64-4cab-b556-79f768b111c5


[Youtube demo](https://www.youtube.com/playlist?list=PLVWPFvHklPATE7g3z18JWybF95-ODSDD9)



# Download precompiled exe version for Windows (other systems use source code deployment)

0. [Click to download the precompiled version, unzip, then double-click sp.exe](https://github.com/jianchang512/pyvideotrans/releases)

1. Unzip to an English path and ensure the path does not contain spaces. After unzipping, double-click sp.exe (if you encounter permission issues, you can right-click to open with administrator privileges)

3. It is not anti-virus proof, false positives from anti-virus software may occur, which can be ignored or you can deploy from the source code

4. Note: It must be used after unzipping, do not double-click to use it directly within the zip package, and do not move the sp.exe file to other locations after unzipping



# Source Code Deployment

1. Set up a Python environment from 3.10 to 3.11, recommended 3.10
2. `git clone https://github.com/jianchang512/pyvideotrans`
3. `cd pyvideotrans`
4. `python -m venv venv`
5. On Win execute `%cd%/venv/scripts/activate`, on Linux and Mac execute `source ./venv/bin/activate`
6. `pip install -r requirements.txt`, if you encounter version conflict errors, use `pip install -r requirements.txt --no-deps`
7. If you want to enable CUDA acceleration on Windows and Linux, continue with `pip uninstall -y torch` to uninstall, then run `pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cu121`. (Must have Nvidia card and CUDA environment configured)
8. Additionally on Linux, if using CUDA acceleration, install with `pip install nvidia-cublas-cu11 nvidia-cudnn-cu11`

9. Unzip ffmpeg.zip to the root directory on Win (ffmpeg.exe file), and on Linux and Mac, please install ffmpeg yourself, you can "Baidu or Google" for specific methods

10. `python sp.py` to open the software interface

11. If CUDA acceleration support is required, an NVIDIA graphics card is needed on the device. For specific installation precautions, see below [CUDA Acceleration Support](https://github.com/jianchang512/pyvideotrans?tab=readme-ov-file#cuda-%E5%8A%A0%E9%80%9F%E6%94%AF%E6%8C%81)

12. On Ubuntu, you might also need to install the Libxcb library, use the following command:

```	
sudo apt-get update
sudo apt-get install libxcb-cursor0	
```

13. On Mac, you might need to run `brew install libsndfile` to install libsndfile

# How to Use

1. Choose video: Click to select mp4/avi/mov/mkv/mpeg videos, multiple videos can be selected;

2. Save to..: If not chosen, it defaults to generating in the `_video_out` in the same directory, and at the same time, bilingual subtitle files in the original and target languages will be created in the srt folder in that directory

3. Translation channel: Choose from microsoft | google | baidu | tencent | chatGPT | Azure | Gemini | DeepL | DeepLX | OTT translation channels

4. Proxy address: If your region cannot directly access Google/chatGPT, you need to set up a proxy in the Network Proxy of the software interface, for example, if using v2ray, fill in `http://127.0.0.1:10809`, if clash, then fill in `http://127.0.0.1:7890`. If you have changed the default port or are using other proxy software, fill in as needed

5. Original language: Choose the language category of the video to be translated

6. Target language: Choose the language category into which you want to translate

7. TTS and dubbing character: After choosing the target language for translation, you can choose from the dubbing options, the dubbing character;
   
   Hard subtitles:
   Refers to subtitles that are always displayed and cannot be hidden, if you want subtitles to be displayed during web play, please choose hard subtitle embedding, which can be set through font size in videotrans/set.ini

   Hard subtitles (double):
   Display target language subtitles and original language subtitles on separate lines

   Soft subtitles:
   If the player supports subtitle management, you can display or hide subtitles. This method will not show subtitles when playing on the web, and some domestic players may not support it. You need to place the generated video's name-matching srt file and video in one directory to display

   Soft subtitles (double):
   Will embed subtitles in two languages, which can be switched via the subtitle display/hide function of the player

8. Voice recognition model: Choose from base/small/medium/large-v2/large-v3, with recognition results getting better, but recognition speed getting slower and memory requirements getting larger each time; built-in base model, other models need to be downloaded separately, unzipped and put into the "current software directory/models" directory. If the GPU memory is less than 4G, do not use large-v3

   Overall recognition: The model will automatically handle sentence segmentation for the entire audio. Do not choose overall recognition for large videos to avoid crashes due to insufficient video memory

   Pre-split: Suitable for very large videos, first cut into 1-minute segments for sequential recognition and segmentation

   Equal division: Split the video into equal seconds, with each subtitle being approximately equal in length, controlled by interval_split in set.ini

    [Download all models](https://github.com/jianchang512/stt/releases/tag/0.0)

    **Special Attention**

    Faster models: If you have downloaded the faster model, after unzipping, copy the "models--Systran--faster-whisper-xx" folder inside the zip to the models directory. After unzipping and copying, the folder list under models directory should look like this
    ![](https://github.com/jianchang512/stt/assets/3378335/5c972f7b-b0bf-4732-a6f1-253f42c45087)

    Openai models: If you have downloaded the openai model, after unzipping, directly copy the .pt files inside to the models folder. 

9. Dubbing pace: Fill in a number between -90 and +90, the same sentence requires different amounts of time under different language voices, therefore dubbing may result in asynchrony of voice, picture, and subtitles. You can adjust the rate here, negative numbers mean decelerate, positive numbers mean accelerate playback.

10. Aligning sound, picture, and subtitles: "Dubbing pace" "Automatic dubbing acceleration" "Automatic video deceleration" "Voice extension before and after"

>
> After translation, the pronunciation duration under different languages is different, for example, a sentence that takes 3s in Chinese might take 5s in English, leading to inconsistency in duration and video.
>
> 4 ways to solve this:
>
> 1. Set the dubbing rate, global acceleration (some TTS do not support)
>
> 2. Force dubbing acceleration to shorten the dubbing duration and align with the video
>
> 3. Force video slow down to extend the video duration and align with the dubbing.
>
> 4. If there are silent sections before and after, then extend to cover the silent area\n In actual use, the best effect is achieved by combining these 4 items
>
> For the principle implementation, please refer to the blog post https://juejin.cn/post/7343691521601290240
>

12. **CUDA Acceleration**: Confirm that your computer's graphics card is an Nvidia card, and you have configured the CUDA environment and driver, then select this option, the speed can be greatly improved. For specific configuration methods, see below [CUDA Acceleration Support](https://github.com/jianchang512/pyvideotrans?tab=readme-ov-file#cuda-%E5%8A%A0%E9%80%9F%E6%94%AF%E6%8C%81)

13. TTS: You can use edgeTTS and openai TTS-1 models, Elevenlabs, clone-voice, custom TTS, openai requires using the official interface or a third-party interface that has activated the tts-1 model, or choose clone-voice for original timbre dubbing. Also supports using your own tts service, fill in the API address in Settings menu - Custom TTS-API

14. Click the Start button the current progress and log will be displayed at the bottom, and the subtitles will be displayed in the text box on the right 

15. After the subtitle analysis is completed, it will pause awaiting editing of the subtitles, if no operation is performed, it will automatically continue to the next step after 30s. You can also edit the subtitles in the right subtitle area and then manually click to continue synthesis

16. In the subdirectory of the target folder named after the video, separate srt files in both languages, the original voice and dubbed wav files will be generated for further processing.

17. Set the role for the line: You can set a dubbing role for each line in the subtitle, first choose the TTS type and character on the left, then click "Set role for the line" in the lower right corner of the subtitle area, in the text behind each character name, fill in the line number that will use that character for dubbing, as shown in the following picture:
    ![](./images/p2.png)

18. Retain background music: If this option is selected, then the video's human voice and background accompaniment will first be separated, in which the background accompaniment will eventually be merged with the dubbing audio, and the final result video will retain the background accompaniment. **Note**: This function is based on uvr5. If you do not have enough Nvidia GPU memory, such as 8GB or more, it is recommended to choose carefully as it may be very slow and consume a lot of resources. If the video is relatively large, it is recommended to choose a separate video separation tool, such as uvr5 or vocal-separate https://juejin.cn/post/7341617163353341986

19. Original timbre clone dubbing clone-voice: First install and deploy the [clone-voice](https://github.com/jianchang512/clone-voice) project, download and configure the "text-to-sound" model, then in this software's TTS type, choose "clone-voice" and the dubbing character selects "clone" to realize dubbing using the original video's voice. When using this method, it is recommended to select "Retain background music" to eliminate background noise for better effect.

20. Using GPT-SoVITS for dubbing: First install and deploy the GPT-SoVITS project, then start the GPT-SoVITS's api.py, and fill in the interface address and reference audio, etc., in the video translation and dubbing software's settings menu - GPT-SoVITS API.

GPT-SoVITS's own api.py does not support mixed Chinese and English pronunciation. If support is needed, please [click to download this file](https://github.com/jianchang512/gptsovits-api/releases/tag/v0.1), copy the api2.py inside the compressed package to the root directory of GPT-SoVITS, and start it the same way as the original api.py, you can refer to the usage tutorial https://juejin.cn/post/7343138052973297702

21. In `videotrans/chatgpt.txt` `videotrans/azure.txt` `videotrans/gemini.txt` respectively, you can edit the chatGPT, AzureGPT, Gemini Pro prompts, you must pay attention to `{lang}` representing the target language for translation, do not delete or modify. Make sure the prompts tell AI to return content line by line after translating it, and the number of returned lines must match the number of lines sent.

22. Adding Background Music: This function is similar to "Retaining Background Music," but the implementation method is different, it can only be used in "Standard Function Mode" and "Subtitles Create Dubbing" mode.
"Adding Background Music" pre-selects an audio file from the local computer as the background sound, which is displayed in the text box on the right, and when processing the result video, the audio is mixed in, the final video will play the background audio file.

If "Retain Background Music" is also selected, the original video's background music will also be retained.

After adding background music, if you no longer want it, simply delete the content displayed in the text box on the right.


# Frequently Asked Questions

1. Error prompted when using Google Translate or chatGPT

   In China, both Google and the official chatGPT interface require a VPN.

2. Global proxy is used, but it doesn't seem to work

   You need to set the specific proxy address in the software interface "Network Proxy", formatted as http://127.0.0.1:port number

3. FFmpeg does not exist prompt

   First, check to make sure that the ffmpeg.exe, ffprobe.exe files exist in the root directory of the software
   
4. CUDA is activated on Windows but is showing errors

   A: [First, check the detailed installation method](https://juejin.cn/post/7318704408727519270), to ensure that you have installed the required CUDA tools correctly. If errors persist, [download cuBLAS](https://github.com/jianchang512/stt/releases/download/0.0/cuBLAS_win.7z), unzip it, and copy the dll files to C:/Windows/System32.

   B: If it is confirmed not related to A, then check if the video is encoded in H264 mp4. Some HD videos are encoded in H265, which is not supported. Try converting to H264 video in the "Video Toolbox".

   C: Under GPU, hardware decoding and encoding of videos have strict requirements for data accuracy, with almost zero tolerance for errors. Even a slight mistake can lead to failure, and due to differences in graphics card models, driver versions, CUDA versions, ffmpeg versions, compatibility errors can easily occur. Currently, a fallback has been added; if the process fails on the GPU, it will automatically revert to CPU software codec. Error information will be recorded in the logs directory when a failure occurs.

5. Getting a 'model does not exist' prompt?

   [Download all models here](https://github.com/jianchang512/stt/releases/tag/0.0)

   **Models are divided into two categories:**

   One category is for the "faster models".

   After downloading and unzipping, you will see folders in the format "models--Systran--faster-whisper-xxx", where xxx represents the model name, such as base/small/medium/large-v3, etc. Just copy that folder directly into this directory.

   After downloading all faster models, the current models folder should contain these folders:

   models--Systran--faster-whisper-base
   models--Systran--faster-whisper-small
   models--Systran--faster-whisper-medium
   models--Systran--faster-whisper-large-v2
   models--Systran--faster-whisper-large-v3

   The other category is for "openai models", which after downloading and unzipping, give you .pt files directly, like base.pt/small.pt/medium.pt/large-v3.pt. Copy this pt file directly into this folder.

   After downloading all openai models, the current models folder should show base.pt, small.pt, medium.pt, large-v1.pt, large-v3.pt directly.

6. Prompt for 'directory does not exist or permission error'

   Right-click on sp.exe and open with administrator privileges.

7. Error prompt with no detailed error information

   Open the logs directory, find the newest log file and scroll to the bottom to see the error information.

8. The large-v3 model is very slow

   If you do not have an Nvidia GPU, or the CUDA environment is not properly configured, or if the VRAM is less than 8GB, do not use this model as it will be very slow and may cause stuttering.

9. Prompt for missing cublasxx.dll file

   Sometimes an error that "cublasxx.dll does not exist" may be encountered, at which point cuBLAS needs to be downloaded, and then the dll files copied to the system directory.

   [Click to download cuBLAS](https://github.com/jianchang512/stt/releases/download/0.0/cuBLAS_win.7z), then copy the dll files into C:/Windows/System32.
   
   [cuBLAS.and.cuDNN_win_v4](https://github.com/Purfview/whisper-standalone-win/releases/download/libs/cuBLAS.and.cuDNN_win_v4.7z)

11. How to use custom timbre

   Go to the settings menu - Custom TTS-API and fill in your tts server interface address.

   A POST request will send application/www-urlencode data to the API address provided:

```
# Data sent in the request:

text: The text/string to be synthesized

language: The language code of the text (zh-cn, zh-tw, en, ja, ko, ru, de, fr, tr, th, vi, ar, hi, hu, es, pt, it)/string

voice: The name of the voice actor/character/string

rate: The value for speeding up or slowing down, 0 or '+' or '%' or '-' followed by a number, representing the percentage of the acceleration or deceleration based on the normal speed/string

ostype: Operating system type win32 or mac or linux/string

extra: Additional parameters/string

# Expected JSON format data returned from the interface:
{
    code:0 when synthesis is successful, a number >0 represents failure
    msg:ok when synthesis is successful, otherwise it is the reason for failure
    data: On successful synthesis, returns the complete URL of the mp3 file, used for downloading within the software. Empty when there is a failure
}


```


13. Subtitles and voice unable to align

> After translation, pronunciation duration varies in different languages, for example, a sentence that is 3s in Chinese might take 5s in English, resulting in inconsistency with the video length.
>
> Two solutions:
>
>     1. Force dubbing to play at a faster speed to shorten the dubbing duration and align with the video.
>
>     2. Force the video to play at a slower pace to extend the video's duration and align with the dubbing.

14. Subtitles not displaying or are garbled

> By using soft synthesized subtitles: subtitles are embedded as separate files into the video and can be extracted again. If supported by the player, subtitles can be enabled or disabled in the player's subtitle management.
>
> Note that many domestic players require the srt subtitle file to be in the same directory as the video with the same name in order to load soft subtitles. It may also be necessary to convert the srt file to GBK encoding to avoid garbled text.

15. How to switch software interface language/Chinese or English

Open the `videotrans/set.ini` file in the software directory, and then fill in the language code after `lang=`, where `zh` stands for Chinese and `en` stands for English. Restart the software after making the change.

```

;The default interface follows the system and can also be specified manually here, zh=Chinese interface, en=English interface.
;默认界面跟随系统，也可以在此手动指定，zh=中文界面，en=英文界面
lang =


```

16. Crashes before completion

If CUDA is enabled and the computer has installed the CUDA environment but cudnn has not been manually installed and configured, you will encounter this issue. Install cudnn that matches with CUDA. For example, if you have installed CUDA 12.3, you will need to download cudnn for cuda12.x package, then unzip it, and copy the three folders inside to the CUDA installation directory. For the specific tutorial, refer to 
https://juejin.cn/post/7318704408727519270.

If cudnn is installed according to the tutorial and still crashes, it is very likely due to insufficient GPU memory. You can switch to using the medium model. When VRAM is less than 8GB, try to avoid using the largev-3 model, especially when the video is larger than 20MB, otherwise, it may crash due to insufficient memory.

17. How to adjust subtitle font size

If embedding hard subtitles, you can adjust the font size by modifying the `fontsize=0` in `videotrans/set.ini` to a suitable value. 0 represents the default size, and 20 represents a font size of 20 pixels.

18. Errors on macOS

OSError: ctypes.util.find_library() did not manage to locate a library called 'sndfile'

Solution:

Find the libsndfile installation location. If installed via brew, it's generally located at `/opt/homebrew/Cellar/libsndfile`. Then add this path to the environment variable: `export DYLD_LIBRARY_PATH=/opt/homebrew/Cellar/libsndfile/1.2.2/lib:$DYLD_LIBRARY_PATH`.

19. GPT-SoVITS API does not support mixed Chinese and English pronunciation

The api.py that comes with GPT-SoVITS does not support mixed Chinese and English pronunciation. If needed, please [click to download this file](https://github.com/jianchang512/stt/releases/download/0.0/GPT-SoVITS.api.py.zip), and replace the existing api.py of GPT-SoVITS with the one from the compressed package.

20. Are there detailed tutorials?

There is a documentation website at https://pyvideotrans.com, but since it's inconvenient to upload images there, updates are slow. Please check the Juejin blog for the latest tutorials at https://juejin.cn/user/4441682704623992/columns.

Or you can follow my WeChat public account, which basically has the same content as the Juejin blog. Search WeChat to view the public account `pyvideotrans`.

# Advanced Settings - videotrans/set.ini

**Please do not adjust randomly unless you know what will happen**



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
audio_rate=2.5

;Maximum permissible slowdown times of the video frequency, default 0, that is, no restriction, you need to set a number greater than 1-20, for example, 1 = on behalf of not slowing down, 20 = down to 1/20 = 0.05 the original speed, pay attention to how to set up the limit, then the subtitles and the screen will not be able to be aligned
;视频频最大允许慢速倍数，默认0，即不限制，需设置大于1-20的数字，比如1=代表不慢速，20=降为1/20=0.05原速度，注意如何设置了限制，则字幕和画面将无法对齐
video_rate=0

;Number of simultaneous translations, 1-20, not too large, otherwise it may trigger the translation api frequency limitation
;同时翻译的数量，1-20，不要太大，否则可能触发翻译api频率限制
trans_thread=10

;Hard subtitles can be set here when the subtitle font size, fill in the integer numbers, such as 12, on behalf of the font size of 12px, 20 on behalf of the size of 20px, 0 is equal to the default size
;硬字幕时可在这里设置字幕字体大小，填写整数数字，比如12，代表字体12px大小，20代表20px大小，0等于默认大小
fontsize=14


;背景声音音量降低或升高幅度，大于1升高，小于1降低
backaudio_volume=0.5

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

; For pre-split and overall , the minimum silence segment ms to be used as the basis for cutting, default 100ms, i.e., and max seconds.
;用于 预先分割 和 整体识别 时，作为切割依据的最小静音片段ms，默认200ms 以及最大句子时长
overall_silence=200
overall_maxsecs=3


; For  equal-division, the minimum silence segment ms to be used as the basis for cutting, default 500ms, i.e., only silence greater than or equal to 500ms will be segmented.
;用于   均等分割时，作为切割依据的最小静音片段ms，默认500ms，即只有大于等于500ms的静音处才分割
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

# CUDA Acceleration Support

**Install CUDA Tools** [Detailed installation method on Windows](https://juejin.cn/post/7318704408727519270)

It's essential to have both CUDA and cuDNN installed; otherwise, a crash may occur.

On Linux, use `pip install nvidia-cublas-cu11 nvidia-cudnn-cu11`.

After installation, execute `python testcuda.py` or double-click on testcuda.exe. If all outputs are ok, it is confirmed to be working.

Sometimes you might encounter an error saying "cublasxx.dll does not exist." If this error occurs and your CUDA configuration is correct but persistent recognition errors occur, you need to download cuBLAS and then copy the dll files to the system directory.

[Click to download cuBLAS](https://github.com/jianchang512/stt/releases/download/0.0/cuBLAS_win.7z), then unzip it and copy the dll files to C:/Windows/System32.

# CLI Command Line Mode

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1yDGPWRyXeZ1GWqkOpdJDv4nA_88HNm01?usp=sharing)

cli.py is a command-line execution script, and `python cli.py` is the simplest way to execute it.

The parameters it accepts are:

`-m mp4 video absolute address`

Detailed configuration parameters can be set in the cli.ini located in the same directory as cli.py. Other mp4 video addresses to be processed can also be configured through the command line parameter `-m mp4 video absolute address`, like `python cli.py -m D:/1.mp4`.

Within cli.ini are the complete parameters, with the first parameter `source_mp4` representing the video to be processed. Command-line parameters will take precedence over `source_mp4` if passed using `-m`.

`-c configuration file address`

You can also copy cli.ini to another location, and then specify the configuration file to use with the `-c cli.ini absolute path address` command-line parameter, for example, `python cli.py -c E:/conf/cli.ini`, which will use the configuration information from that file, ignoring the project directory configuration file.

`-cuda` does not need a value to follow; merely adding it signifies the enablement of CUDA acceleration (if available) `python cli.py -cuda`.

Example: `python cli.py -cuda -m D:/1.mp4`.


## Specific Parameters and Descriptions in cli.ini

```
;Command Line Arguments
;Absolute address of the video to be processed, use forward slash as path separator, can also be passed after -m in the command line arguments
source_mp4=
;Network proxy address, mandatory for Google chatGPT official China
proxy=http://127.0.0.1:10809
;Directory for output result files
target_dir=
;Video pronunciation language, choose from here: zh-cn zh-tw en fr de ja ko ru es th it pt vi ar tr
source_language=zh-cn
;Language for speech recognition, no need to fill in
detect_language=
;Language to translate into: zh-cn zh-tw en fr de ja ko ru es th it pt vi ar tr
target_language=en
;Language for soft subtitles embedding, no need to fill in
subtitle_language=
;true=Enable CUDA
cuda=false
;Role name, find openaiTTS role names "alloy, echo, fable, onyx, nova, shimmer" from voice_list.json for corresponding language roles. Find elevenlabsTTS role names from elevenlabs.json
voice_role=en-CA-ClaraNeural
; Dubbing acceleration value, must start with a + or - sign, + means accelerate, - means decelerate, ending with %
voice_rate=+0%
;Options include edgetTTS openaiTTS elevenlabsTTS
tts_type=edgeTTS
;Silent segment, unit in ms
voice_silence=500
;all=Overall recognition, split=Recognition after pre-splitting sound segments
whisper_type=all
;Options for speech recognition model: base small medium large-v3
whisper_model=base
;Translation channel, options include google baidu chatGPT Azure Gemini tencent DeepL DeepLX
translate_type=google
;0=Do not embed subtitles, 1=Embed hard subtitles, 2=Embed soft subtitles
subtitle_type=1
;true=Auto-accelerate dubbing
voice_autorate=false
;true=Auto-slow video
video_autorate=false
;Interface address for deepl translation
deepl_authkey=asdgasg
;Address for configured deeplx service
deeplx_address=http://127.0.0.1:1188
;Tencent translation id
tencent_SecretId=
;Tencent translation key
tencent_SecretKey=
;Baidu translation id
baidu_appid=
;Baidu translation secret
baidu_miyue=
;Key for elevenlabstts
elevenlabstts_key=
;chatGPT interface address, ending with /v1, third-party interface addresses can be filled in
chatgpt_api=
;Key for chatGPT
chatgpt_key=
;chatGPT model, options include gpt-3.5-turbo gpt-4
chatgpt_model=gpt-3.5-turbo
;Azure's API interface address
azure_api=
;Key for Azure
azure_key=
;Azure's model name, options include gpt-3.5-turbo gpt-4
azure_model=gpt-3.5-turbo
;Key for Google Gemini
gemini_key=

```

# Software Preview Screenshot
![image](https://github.com/jianchang512/pyvideotrans/assets/3378335/28cf7079-dc97-4666-abf3-abb030ae2ea2)


# Related Projects

[OTT: Local offline text translation tool](https://github.com/jianchang512/ott)

[Clone Voice Tool: Synthesize speech with any timbre](https://github.com/jianchang512/clone-voice)

[STT: Local offline voice recognition to text tool](https://github.com/jianchang512/stt)

[Vocal Separate: Vocal and background music separation tool](https://github.com/jianchang512/vocal-separate)

[Improved version of GPT-SoVITS's api.py](https://github.com/jianchang512/gptsovits-api)

## Acknowledgements

> This program relies mainly on the following open-source projects

1. ffmpeg
2. PySide6
3. edge-tts
4. faster-whisper
5. openai-whisper
6. pydub
