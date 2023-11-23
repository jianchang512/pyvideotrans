[English](./README_ENG.md) / [文档](https://v.wonyes.org/preview.html) / [加入Discord讨论](https://discord.gg/evkPeKJddD) /  [clone-voice 声音克隆](https://github.com/jianchang512/clone-voice)

# 视频翻译和配音工具

>
> 这是一个视频翻译配音工具，可将一种语言的视频翻译为另一种语言配音和字幕的视频。
>
> 语音识别基于 `openai-whisper` 离线模型.
>
> 文字翻译支持 `google|baidu|tencent|chatGPT|DeepL|DeepLX` ，
>
> 文字合成语音支持 `Microsoft Edge tts` `Openai TTS-1`.
>

## 主要用途和使用方式
<details>
<summary>【翻译和配音】 A语言的视频处理后，转变为B语言配音的视频，并显示B语言字幕</summary>
<p></p>
<blockquote>
点击选择待翻译的视频文件，然后依次选定源视频语言、目标语言、配音类型和角色、字幕嵌入类型，开始执行
</blockquote>

</details>


<details>
<summary>【已有字幕配音并嵌入视频】 将本地已有的字幕文件进行配音，和已有的视频素材合并，组成有配音和字幕的视频(拖拽已有字幕到右侧编辑区)</summary>
<p></p>
<blockquote>
选择本地打算添加字幕或配音的视频，然后将已有的字幕文件拖拽到右侧字幕区，选定源语言和目标语言、配音类型和角色，开始执行
</blockquote>

</details>

<details>
<summary>【对已有字幕进行配音】 仅仅对已有的本地字幕配音，然后生成配音后的wav音频文件(不要选择视频，仅拖拽已有字幕到右侧编辑区，然后选择目标语言和配音角色)</summary>
<p></p>
<blockquote>
将本地的字幕文件拖拽到右侧字幕编辑器，然后选择目标语言、配音类型和角色，开始执行
</blockquote>

</details>

<details>

<summary>【从视频提取字幕】 选择视频，然后选择“不嵌入字幕”，配音角色为“No”</summary>
<p></p>
<blockquote>选择视频文件，选择视频源语言，其他无需选择，开始执行</blockquote>

</details>

<details>
<summary>【输出资源】 经过处理后，将在目标文件夹中创建视频同名子目录，输出“原语言srt字幕”、“目标语言srt字幕”、“配音后的wav音频文件”，以便于进一步进行其他处理</summary>
<p></p>
<blockquote>根据你的选择情况， 在目标文件夹下会生成 源语言字幕.srt、目标语言字幕.srt、源声音.wav、配音后.wav、未截断配音-nocut.wav，以便进行其他处理</blockquote>

</details>

<details>
<summary>【视频工具箱】 附带一个简单的视频工具箱，可进行音视频分离、音视频字幕合并、语音识别、语音合成、格式转化、摄像头麦克风录制</summary>
<p></p>
<blockquote>点击菜单栏-工具-视频工具箱，如图![](./images/p6.png)</blockquote>

</details>



----



https://github.com/jianchang512/pyvideotrans/assets/3378335/f9c463d1-0881-49c0-acaa-b9a4bbad4354



# 使用预编译版本方法

0. 只可用于 win10 win11 系统/Mac下需自行拉取源码编译

1. 从 release 中下载最新版，解压，双击 sp.exe

2. 原始视频：选择mp4/avi/mov/mkv/mpeg视频,可选择多个视频；

3. 输出视频目录：如果不选择，则默认生成在同目录下的 `_video_out`，同时在该目录下的srt文件夹中将创建原语言和目标语言的两种字幕文件

4. 选择翻译：可选 google、baidu、chatGPT、DeepL、DeepLX、tencent 翻译渠道

5. 网络代理地址：如果你所在地区无法直接访问 google/chatGPT，需要在软件界面 网络代理 中设置代理，比如若使用 v2ray ，则填写 `http://127.0.0.1:10809`,若clash，则填写 `http://127.0.0.1:7890`. 如果你修改了默认端口或使用的其他代理软件，则按需填写

6. 视频原始语言：选择待翻译视频里的语言种类

7. 翻译目标语言：选择希望翻译到的语言种类

8. 选择配音：选择翻译目标语言后，可从配音选项中，选择配音角色；
   
   硬字幕: 是指始终显示字幕，不可隐藏，如果希望网页中播放时也有字幕，请选择硬字幕嵌入

   软字幕: 如果播放器支持字幕管理，可显示或者隐藏字幕，该方式网页中播放时不会显示字幕，某些国产播放器可能不支持,需要将生成的视频同名srt文件和视频放在一个目录下才会显示

   **如果“既不嵌入字幕又不选择配音角色”将只生成字幕文件**

9. 语音识别模型: 选择 base/small/medium/large/large-v3, 识别效果越来越好，但识别速度越来越慢，所需内存越来越大，第一次将需要下载模型，默认 base,可以预先单独下载模型后，放到 `当前软件目录/models`目录下.

   **整体识别/预先分割**: 整体识别是指直接发送整个语音文件给模型，由模型进行处理，分割可能更精确，但也可能造出30s长度的单字幕，适合有明确静音的音频;  预先分割时指先将音频按10s左右长度切割后再分别发送给模型处理。

   **模型单独下载地址**

    [tiny模型](https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt)
    
    [base模型](https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt)

    [small模型](https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt)

    [medium模型](https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt)

    [large模型](https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a/large.pt)

    [large-v3模型](https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt)

    [VLC解码器下载](https://www.videolan.org/vlc/)

    [FFmepg下载(编译版已自带)](https://www.ffmpeg.org/)

10. 配音语速：填写 -90到+90 之间的数字，同样一句话在不同语言语音下，所需时间是不同的，因此配音后可能声画字幕不同步，可以调整此处语速，负数代表降速，正数代表加速播放。

11. 音视频对齐: 分别是“配音自动加速”和“视频自动降速”

>
> 翻译后不同语言下发音时长不同，比如一句话中文3s，翻译为英文可能5s，导致时长和视频不一致。
> 
> 2种解决方式:
>
>     1. 强制配音加速播放，以便缩短配音时长和视频对齐
> 
>     2. 强制视频慢速播放，以便延长视频时长和配音对齐。
> 
> 两者只可选其一
>  
 
  
12. 静音片段: 填写100到2000的数字，代表毫秒，默认 500，即以大于等于 500ms 的静音片段为区间分割语音

13. CUDA加速：确认你的电脑显卡为 N卡，并且已配置好CUDA环境和驱动，则开启选择此项，速度能极大提升

14. TTS: 可用 edgeTTS 和 openai TTS模型中选择要合成语音的角色，openai需要使用官方接口或者开通了tts-1模型的三方接口

15. 点击 开始按钮 底部会显示当前进度和日志，右侧文本框内显示字幕

16. **字幕解析完成后，将暂停等待修改字幕，如果不做任何操作，60s后将自动继续下一步。也可以在右侧字幕区编辑字幕，然后手动点击继续合成**

17. 将在目标文件夹中视频同名的子目录内，分别生成两种语言的字幕srt文件、原始语音和配音后的wav文件，以方便进一步处理


## 注意事项:

**字幕显示问题**
> 
> 采用软合成字幕：字幕作为单独文件嵌入视频，可再次提取出，如果播放器支持，可在播放器字幕管理中启用或禁用字幕；
> 注意很多国内播放器必须将srt字幕文件和视频放在同一目录下且名字相同，才能加载软字幕，并且可能需要将srt文件转为GBK编码，否则显示乱码，
> 

**字幕语音对齐问题**

> 翻译后不同语言下发音时长不同，比如一句话中文3s，翻译为英文可能5s，导致时长和视频不一致。
> 2种解决方式:
>     1. 强制配音加速播放，以便缩短配音时长和视频对齐
>     2. 强制视频慢速播放，以便延长视频时长和配音对齐。
> 两者只可选其一



# 源码部署

1. 配置好 python 3.9+ 环境
2. `git clone https://github.com/jianchang512/pyvideotrans`
3. `cd pyvideotrans`
4. CPU版`pip install -r requirements.txt`，GPU版 `pip install -r requirements-gpt.txt`
5. 解压 ffmpeg.zip 到根目录下 (ffmpeg.exe文件)
6. `python sp.py` 打开软件界面, `python cli.py` 命令行执行
7. 如果希望打包为exe的话，请使用命令 `pyinstaller sp.py`,不要添加 ` -F` 参数，否则可能闪退(tensorflow缘故)

## CLI 命令行方式使用
<details>
<summary>点开查看具体使用方法</summary>

>
> 按照上述源码部署方式部署好后，执行 `python cli.py`，可在命令行下执行
> 

### 支持的参数

**--source_mp4**： 【必填】待翻译视频路径，以.mp4结尾

**--target_dir**：  翻译后视频存放位置，默认存放源视频目录下的 _video_out 文件夹

**--source_language**：视频语言代码,默认`en` ( zh-cn | zh-tw | en | fr | de | ja | ko | ru | es | th | it | pt | vi | ar )

**--target_language**：目标语言代码,默认`zh-cn` ( zh-cn | zh-tw | en | fr | de | ja | ko | ru | es | th | it | pt | vi | ar )

    zh-cn: Simplified_Chinese
    zh-tw: Traditional_Chinese
    en: English
    fr: French
    de: German
    ja: Japanese
    ko: Korean
    ru: Russian
    es: Spanish
    th: Thai
    it: Italian
    pt: Portuguese
    vi: Vietnamese
    ar: Arabic


**--proxy**：填写 http 代理地址，默认 None,如果所在地区无法访问google，需要填写，例如: `http://127.0.0.1:10809`

**--subtitle_type**：1 嵌入硬字幕，2 嵌入软字幕。

    硬字幕: 是指始终显示字幕，不可隐藏，如果希望网页中播放时也有字幕，请选择硬字幕嵌入

    软字幕: 如果播放器支持字幕管理，可显示或者隐藏字幕，该方式网页中播放时不会显示字幕，某些国产播放器可能不支持


**--voice_role**：根据所选目标语言代码，填写对应的角色名，注意角色名的前2个字母需要和目标语言代码的前2个字母一致，如果不知道该怎么填写，执行`python cli.py show_vioce` 将显示每种语言对应可用的角色名称

	zh: zh-HK-HiuGaaiNeural, zh-HK-HiuMaanNeural, zh-HK-WanLungNeural, zh-CN-XiaoxiaoNeural, zh-CN-XiaoyiNeural, zh-CN-YunjianNeural, zh-CN-YunxiNeural
    , zh-CN-YunxiaNeural, zh-CN-YunyangNeural, zh-CN-liaoning-XiaobeiNeural, zh-TW-HsiaoChenNeural, zh-TW-YunJheNeural, zh-TW-HsiaoYuNeural, zh-CN-shaa
    nxi-XiaoniNeural
    en: en-AU-NatashaNeural, en-AU-WilliamNeural, en-CA-ClaraNeural, en-CA-LiamNeural, en-HK-SamNeural, en-HK-YanNeural, en-IN-NeerjaExpressiveNeural,
    en-IN-NeerjaNeural, en-IN-PrabhatNeural, en-IE-ConnorNeural, en-IE-EmilyNeural, en-KE-AsiliaNeural, en-KE-ChilembaNeural, en-NZ-MitchellNeural, en-
    NZ-MollyNeural, en-NG-AbeoNeural, en-NG-EzinneNeural, en-PH-JamesNeural, en-PH-RosaNeural, en-SG-LunaNeural, en-SG-WayneNeural, en-ZA-LeahNeural, e
    n-ZA-LukeNeural, en-TZ-ElimuNeural, en-TZ-ImaniNeural, en-GB-LibbyNeural, en-GB-MaisieNeural, en-GB-RyanNeural, en-GB-SoniaNeural, en-GB-ThomasNeur
    al, en-US-AriaNeural, en-US-AnaNeural, en-US-ChristopherNeural, en-US-EricNeural, en-US-GuyNeural, en-US-JennyNeural, en-US-MichelleNeural, en-US-R
    ogerNeural, en-US-SteffanNeural
    fr: fr-BE-CharlineNeural, fr-BE-GerardNeural, fr-CA-AntoineNeural, fr-CA-JeanNeural, fr-CA-SylvieNeural, fr-FR-DeniseNeural, fr-FR-EloiseNeural, fr
    -FR-HenriNeural, fr-CH-ArianeNeural, fr-CH-FabriceNeural
    de: de-AT-IngridNeural, de-AT-JonasNeural, de-DE-AmalaNeural, de-DE-ConradNeural, de-DE-KatjaNeural, de-DE-KillianNeural, de-CH-JanNeural, de-CH-Le
    niNeural    
    ja: ja-JP-KeitaNeural, ja-JP-NanamiNeural
    ko: ko-KR-InJoonNeural, ko-KR-SunHiNeural    
    ru: ru-RU-DmitryNeural, ru-RU-SvetlanaNeural
    es: es-AR-ElenaNeural, es-AR-TomasNeural, es-BO-MarceloNeural, es-BO-SofiaNeural, es-CL-CatalinaNeural, es-CL-LorenzoNeural, es-CO-GonzaloNeural, e
    s-CO-SalomeNeural, es-CR-JuanNeural, es-CR-MariaNeural, es-CU-BelkysNeural, es-CU-ManuelNeural, es-DO-EmilioNeural, es-DO-RamonaNeural, es-EC-Andre
    aNeural, es-EC-LuisNeural, es-SV-LorenaNeural, es-SV-RodrigoNeural, es-GQ-JavierNeural, es-GQ-TeresaNeural, es-GT-AndresNeural, es-GT-MartaNeural,
    es-HN-CarlosNeural, es-HN-KarlaNeural, es-MX-DaliaNeural, es-MX-JorgeNeural, es-NI-FedericoNeural, es-NI-YolandaNeural, es-PA-MargaritaNeural, es-P
    A-RobertoNeural, es-PY-MarioNeural, es-PY-TaniaNeural, es-PE-AlexNeural, es-PE-CamilaNeural, es-PR-KarinaNeural, es-PR-VictorNeural, es-ES-AlvaroNe
    ural, es-ES-ElviraNeural, es-US-AlonsoNeural, es-US-PalomaNeural, es-UY-MateoNeural, es-UY-ValentinaNeural, es-VE-PaolaNeural, es-VE-SebastianNeura
    l
	th: th-TH-NiwatNeural, th-TH-PremwadeeNeural
	it: it-IT-DiegoNeural, it-IT-ElsaNeural, it-IT-IsabellaNeural
	pt: pt-BR-AntonioNeural, pt-BR-FranciscaNeural, pt-PT-DuarteNeural, pt-PT-RaquelNeural
    vi: vi-VN-HoaiMyNeural, vi-VN-NamMinhNeural
	ar: ar-DZ-AminaNeural, ar-DZ-IsmaelNeural, ar-BH-AliNeural, ar-BH-LailaNeural, ar-EG-SalmaNeural, ar-EG-ShakirNeural, ar-IQ-BasselNeural, ar-IQ-Ran
    aNeural, ar-JO-SanaNeural, ar-JO-TaimNeural, ar-KW-FahedNeural, ar-KW-NouraNeural, ar-LB-LaylaNeural, ar-LB-RamiNeural, ar-LY-ImanNeural, ar-LY-Oma
    rNeural, ar-MA-JamalNeural, ar-MA-MounaNeural, ar-OM-AbdullahNeural, ar-OM-AyshaNeural, ar-QA-AmalNeural, ar-QA-MoazNeural, ar-SA-HamedNeural, ar-S
    A-ZariyahNeural, ar-SY-AmanyNeural, ar-SY-LaithNeural, ar-TN-HediNeural, ar-TN-ReemNeural, ar-AE-FatimaNeural, ar-AE-HamdanNeural, ar-YE-MaryamNeural, ar-YE-SalehNeural

**--voice_rate**：负数降低配音语速，正数加快配音语速，默认`0`

**--voice_silence**: 输入100-2000之间的数字，表示静音段的最小毫秒，默认为 500。

**--voice_autorate**: 如果翻译后的音频时长超过原时长，是否强制加速播放翻译后的音频，以便对齐时长

**--whisper_model**: 默认为base，可选 base / small / medium / large，效果越来好，速度越来越慢。



**cli示例**

`python cli.py --source_mp4 "D:/video/ex.mp4" --source_language en --target_language zh-cn --proxy "http://127.0.0.1:10809" --voice_replace zh-CN-XiaoxiaoNeural`

上述意思是，将源语言为英文的 D:/video/ex.mp4 视频，翻译为中文视频，设置代理 http://127.0.0.1:10809 使用配音角色为 zh-CN-XiaoxiaoNeural

`python cli.py --source_mp4 "D:/video/ex.mp4" --source_language zh-cn --target_language en  --proxy "http://127.0.0.1"1080
9"  --voice_replace en-US-AriaNeural --voice_autorate  --whisper_model small`

上述意思是，将源语言为中文的 D:/video/ex.mp4 视频，翻译为英文视频，设置代理 http://127.0.0.1:10809 使用配音角色为 en-US-AriaNeural，如果翻译后的语音时长大于原语音，则自动加速，文字识别模型采用 small 模型

</details>
# 软件预览截图

![](./images/p1.png?b)
![](./images/p2.png?b)
![](./images/p3.png?b)
![](./images/p4.png?b)
![](./images/p5.png?b)
![](./images/p6.png?b)
![](./images/p7.png?b)
![](./images/cli.png?c)


# 视频前后对比

[Demo 原视频和翻译后视频](https://www.wonyes.org/demo.html)

[Youtube demo](https://youtu.be/skLtE1XnO6Q)


# CUDA 加速支持

1. 预编译版部分功能支持使用CUDA：如果你的显卡是 Nvidia，可以根据显卡驱动版本和操作系统版本，去安装对应的 
   [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads) ,建议预先将显卡驱动升级到最新版，再去安装。要完整支持CUDA，需要使用源码版在自己电脑部署

2. 源码版使用CUDA：需要安装 `pip install -r requirements-gpu.txt` 而不是 `requirements.txt`

3. CUDA 环境配置相对复杂，遇到问题多搜索


# 致谢

> 本程序依赖这些开源项目

1. pydub
2. ffmpeg
3. PyQt5
4. SpeechRecognition
5. edge-tts
6. openai-whisper
7. opencv-python
