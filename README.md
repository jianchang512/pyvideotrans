# [English](./README_ENG.md)

这是一个视频翻译工具，可将一种语言的视频翻译为另一种语言和配音的视频。
语音识别基于 `openai-whisper` 离线模型、文字翻译使用`google`翻译接口，文字合成语音使用 `Microsoft Edge tts`，背景音乐去除使用 `Spleeter`,无需购买任何商业接口，也无需付费




https://github.com/jianchang512/pyvideotrans/assets/3378335/27af2313-1717-43c2-9853-6d4b1d3ecdf4



# 使用预编译版本方法

0. 只可用于 win10 win11 系统 (编译版非最新，建议源码部署)
1. 从 release 中下载最新版，解压，双击 sp.exe
2. 原始视频目录：选择mp4视频；
3. 输出视频目录：如果不选择，则默认生成在同目录下的 `_video_out`
3. 网络代理地址：如果你所在地区无法直接访问 google，需要在软件界面 网络代理 中设置代理，比如若使用 v2ray ，则填写 `http://127.0.0.1:10809`,若clash，则填写 `http://127.0.0.1:7890`. 如果你修改了默认端口或使用的其他代理软件，则按需填写
4. 视频原始语言：选择待翻译视频里的语言种类
5. 翻译目标语言：选择希望翻译到的语言种类   
6. 选择配音：选择翻译目标语言后，可从配音选项中，选择配音角色；
   
   嵌入字幕：是否翻译后将字幕嵌入视频 （该参数和“选择配音”必须至少设置其中一个,也就是不能“既不嵌入字幕又不选择配音角色”）
7. 文字识别模型: 选择 base/small/medium/large, 识别效果越来越好，但识别速度越来越慢，第一次将需要下载模型，默认 base   
8. 配音语速：填写 -90到+90 之间的数字，同样一句话在不同语言语音下，所需时间是不同的，因此配音后可能声画字幕不同步，可以调整此处语速，负数代表降速，正数代表加速播放。
9. 自动加速: 如果翻译后的语音时长大于原时长，并且这里确认选中，那么将强制加速播放该片段，以缩小时长
10. 去除背景音：若选中可尝试删掉背景音乐，以使结果更准确
11. 静音片段: 填写100到2000的数字，代表毫秒，默认 500，即以大于等于 500ms 的静音片段为区间分割语音
12. 点击 开始按钮 底部会显示当前进度和日志，右侧文本框内显示字幕
    
> 原始视频统一使用mp4格式，处理速度快，网络兼容性好
> 
> 采用软合成字幕：字幕作为单独文件嵌入视频，可再次提取出，如果播放器支持，可在播放器字幕管理中启用或禁用字幕；
> 
> 默认会在 原始视频目录 下生成同名的字幕文件 视频名.srt
> 
> 对于无法识别的语音将直接复制原语音


# 源码部署

1. 配置好 python 3.9+ 环境
2. `git clone https://github.com/jianchang512/pyvideotrans`
3. `cd pyvideotrans`
4. `pip install -r requirements.txt`
5. 解压 ffmpeg.zip 到根目录下 (ffmpeg.exe文件)
6. 解压 pretrained_models.zip 在根目录下(Spleeter模型文件)   
6. `python sp.py` 打开软件界面, `python cli.py` 命令行执行
7. 如果使用去除背景音功能，第一次需要下载模型，会比较耗时。你可以解压pretrained_models.zip 到当前项目根下

# cli 方式使用

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

**--insert_subtitle**：是否翻译后将字幕嵌入视频 （该参数和 --voice_role 必须至少设置其中一个,也就是不能“既不嵌入字幕又不选择配音角色”）

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

**--remove_background**：是否移除背景音，如果传入该参数即代表去除背景音



**cli示例**

`python cli.py --source_mp4 "D:/video/ex.mp4" --source_language en --target_language zh-cn --proxy "http://127.0.0.1:10809" --voice_replace zh-CN-XiaoxiaoNeural`

上述意思是，将源语言为英文的 D:/video/ex.mp4 视频，翻译为中文视频，设置代理 http://127.0.0.1:10809 使用配音角色为 zh-CN-XiaoxiaoNeural

`python cli.py --source_mp4 "D:/video/ex.mp4" --source_language zh-cn --target_language en  --proxy "http://127.0.0.1"1080
9"  --voice_replace en-US-AriaNeural --voice_autorate  --whisper_model small`

上述意思是，将源语言为中文的 D:/video/ex.mp4 视频，翻译为英文视频，设置代理 http://127.0.0.1:10809 使用配音角色为 en-US-AriaNeural，如果翻译后的语音时长大于原语音，则自动加速，文字识别模型采用 small 模型


# 软件预览截图

![](./images/p1.png?a)
![](./images/cli.png?b)


# 视频前后对比

[demo / Original Video and Translated Video](https://www.wonyes.org/demo.html)

[![Youtube demo](https://i9.ytimg.com/vi_webp/F0U8JTBkCYA/mq1.webp?sqp=CKjEhKoG-oaymwEmCMACELQB8quKqQMa8AEB-AHUCYAC0AWKAgwIABABGBMgSCh_MA8=&rs=AOn4CLCCC4UjoQWuX0_LcCHUb17D9CLjfA)](https://youtu.be/F0U8JTBkCYA)

# 可能的问题

> 翻译使用 requests 请求 google api，然后提取，过于频繁可能会被限制。


# 致谢

> 本程序依赖这些开源项目

1. pydub
2. ffmpeg
3. PyQt5
4. SpeechRecognition
5. edge-tts
6. Spleeter
7. openai-whisper
