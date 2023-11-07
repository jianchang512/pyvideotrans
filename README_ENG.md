# [简体中文](./README.md)

This is a video translation tool that can translate videos from one language to another language and provide dubbed videos. 

The speech recognition is based on the offline model 'openai-whisper', the text translation uses the 'Google Translate|Baidu|ChatGPT' interface, and the text-to-speech synthesis uses 'Microsoft Edge TTS'. In addition



https://github.com/jianchang512/pyvideotrans/assets/3378335/98ab5ef9-64ee-4e77-8989-c58acccf7923



# Instructions for using the precompiled version:

0. Can only be used on win10 win11 systems.
1. Download the latest version from the release, extract it, and double-click on sp.exe.
2. Original video directory: Select the mp4 video.
3. Output video directory: If not selected, it will default to generating in the same directory as `_video_out`.
4. Choose translation: Google, Baidu, ChatGPT can be selected, and the latter two need to click on "Set Translation Key" to set corresponding information
5. Network proxy address: If you are unable to access Google directly in your region, you need to set up a proxy in the software interface under Network Proxy. For example, if you are using v2ray, enter `http://127.0.0.1:10809`. If using Clash, enter `http://127.0.0.1:7890`. If you have modified the default port or are using other proxy software, please fill in accordingly.
6. Original video language: Select the language of the video to be translated.
7. Target translation language: Select the desired language for translation.
8. Select dubbing: After selecting the target translation language, you can choose a dubbing role from the dubbing options.
   
   Embedded subtitles:display regardless,doesnot hide them.

    Soft subtitles: If player supports it, you can control display or hiding of .To display subtitles when playing in website,choose embeded subtitles option.
   
   **‘neither embedding subtitles nor selecting voiceover characters’ is not allowed**
   
9. Text recognition model: Choose base/small/medium/large. The recognition effect improves as the model size increases, but the recognition speed slows down. The base model is the default and needs to be downloaded for the first time.

   If you need, download models before running it, save to `This soft dir/models`
   
   **download models link**

   
    [tiny](https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt)
    
    [base](https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt)

    [small](https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt)

    [medium](https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt)

    [large](https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a/large.pt)
   

       

10. Dubbing speed: Enter a number between -90 and +90. The length of the same sentence varies under different language synthesizations. Therefore, the dubbing may not be synchronized with the subtitles. Adjust the speed here, where negative numbers indicate slowing down and positive numbers indicate speeding up.
11. Auto acceleration: If the duration of the translated speech is longer than the original duration and you checked here, the segment will be forced to be accelerated to reduce the length.
12. Silent segments: Enter a number between 100 and 2000, representing milliseconds. The default is 500, which means segments with silences equal to or longer than 500ms will be used as the basis for splitting the speech.
13. Click "Start", he execution will proceed, and the current progress will be displayed on the right. The subtitles will be displayed in the white text box at the bottom.
14. After the subtitle parsing is completed, it will pause and wait for the subtitle to be modified. If no action is taken, it will automatically continue to the next step after 60 seconds. You can also edit subtitles in the subtitle area on the right, and then manually click to continue synthesizing


> The original video should be in mp4 format for fast processing and good network compatibility.
> 
> Soft-coded subtitles are used – subtitles are embedded as separate files in the video and can be extracted again. If supported by the player, you can enable or disable subtitles in the player's subtitle management.
> 
> By default, a subtitle file with the same name as the original video will be generated in the original video directory as "video_name.srt".
> 
> Unrecognized speech will be directly copied from the original audio.

# Source Code Deployment

1. Set up a Python 3.9+ environment.
2. Clone the repository: `git clone https://github.com/jianchang512/pyvideotrans`
3. Navigate to the cloned repository: `cd pyvideotrans`
4. Install the required packages: `pip install -r requirements.txt`
5. Unzip `ffmpeg.zip` in the root directory.Unzip `pretrained_models.zip` in the root directory.
6. Run `python sp.py` to open the software interface. Run `python cli.py` cli mode 
7. If packing, execute `pyinstaller sp.py`, don't add `-w -F` param else will exit (because tensorflow)

# CLI Usage

> After deploying the source code as mentioned above, execute `python cli.py` to use it in the command line.


### Supported Parameters

**--source_mp4**: [Required] Path of the video to be translated, must end with .mp4.

**--target_dir**: Directory to store the translated video. By default, it is stored in the "_video_out" folder in the source video directory.

**--source_language**: Language code of the video. Default is `en` (zh-cn | zh-tw | en | fr | de | ja | ko | ru | es | th | it | pt | vi | ar)

**--target_language**: Language code of the target language. Default is `zh-cn` (zh-cn | zh-tw | en | fr | de | ja | ko | ru | es | th | it | pt | vi | ar)

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

**--proxy**: Specify an HTTP proxy address. Default is None. If you are unable to access Google from your location, you need to provide a proxy address. For example: `http://127.0.0.1:10809`

**--subtitle_type**:  1 Embed subtitle, 2 soft subtitle.

Embedded subtitles: display regardless,doesnot hide them.

Soft subtitles: If player supports it, you can control display or hiding of .
To display subtitles when playing in website,choose embeded subtitles option.

   **neither embedding subtitles nor selecting voiceover characters is not allowed**.

**--voice_role**: Provide the corresponding character name based on the target language code. Make sure the first two letters of the character name match the first two letters of the target language code. If you are unsure how to fill in this parameter, run `python cli.py show_voice` to display the available character names for each language.

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


**--voice_rate**: Adjust the speed of the voice dubbing. Use negative numbers to decrease the speed and positive numbers to increase it. The default value is `0`


**--voice_silence**: Enter a number between 100 and 2000, indicating the minimum duration of a silent section in milliseconds. The default is 500.

**--voice_autorate**: If the translated audio is longer than the original duration, can it be automatically accelerated to align with the original duration

**--whisper_model**: The default is base. Choose from base, small, medium, or large. As the model size increases, the translation effect improves but the speed slows down.


**CLI Example**

`python cli.py --source_mp4 "D:/video/ex.mp4" --source_language en --target_language zh-cn --proxy "http://127.0.0.1:10809" --voice_role zh-CN-XiaoxiaoNeural`

> In the above example, it translates the video located at "D:/video/ex.mp4" from English to Chinese, sets the proxy to "http://127.0.0.1:10809", and uses the voice replacement of "zh-CN-XiaoxiaoNeural".

`python cli.py --source_mp4 "D:/video/ex.mp4" --source_language zh-cn --target_language en  --proxy "http://127.0.0.1"1080
9"  --voice_role en-US-AriaNeural --voice_autorate  --whisper_model small`

> The above means to translate the video D:/video/ex.mp4 with the source language as Chinese to the target language as English. Set the proxy as http://127.0.0.1:10809 and use the voiceover role en-US-AriaNeural. If the translated audio duration is longer than the original audio, it will automatically be accelerated. The text recognition model for speech recognition is set to use the small model.


# Software Preview Screenshots

![](./images/pen1.png?a)
![](./images/cli.png?a)

# Video Comparison Before and After Translation

[demo / Original Video and Translated Video](https://www.wonyes.org/demo.html)

[Youtube demo](https://youtu.be/-WAyWjJPSEk)


# Potential Issues

The translation process uses requests to make calls to the Google API, and frequent calls may trigger rate limits.

# Acknowledgments

This program relies on the following open-source projects.

1. pydub
2. ffmpeg
3. PyQt5
4. SpeechRecognition
5. edge-tts
6. Spleeter
7. openai-whisper
