# [简体中文](./README_ENG.md)

This is a video translation tool that can translate videos from one language to another language and provide dubbed videos. 

The speech recognition is based on the offline model 'openai-whisper', the text translation uses the 'Google Translate' interface, and the text-to-speech synthesis uses 'Microsoft Edge TTS'. In addition, the background music removal is done using 'Spleeter'. It does not require purchasing any commercial interfaces or any fees.

# Instructions for using the precompiled version:

0. This version is only compatible with Windows 10 and Windows 11 systems.
1. Download the latest version from the release section, unzip it, and double-click on "sp.exe".
2. Click on the "Wait Video" button to select an MP4 video for translation. If you don't choose an output directory, the video will be generated in the default directory "_video_out".
3. If you are unable to access Google directly in your region, you need to set up a proxy in the "Proxy" (network proxy) section of the software interface. For example, if you are using v2ray, enter "http://127.0.0.1:10809"; if you are using Clash, enter "http://127.0.0.1:7890". If you have modified the default port or are using other proxy software, fill in the appropriate information.
4. Dubbing selection: After selecting the target language, you can choose a dubbing character from the dubbing options.
5. Remove background music: Select "Yes" to attempt removing the background music and make the results more accurate.
6. Dubbing speed: The time required for the same sentence in different languages may vary, so the subtitles may not be synchronized after dubbing. You can adjust the speed here. Negative numbers represent slowdown, while positive numbers represent accelerated playback.
7. Click on "Start" (Start Execution). It will first check if it can connect to Google services. If it is successful, it will start the execution. The progress will be displayed on the right side, and the subtitles will be shown in the white text box at the bottom.
8. The original videos should be in MP4 format, as it is fast to process and has good network compatibility.
9. Soft-encoded subtitles are used, which are embedded as separate files in the video and can be extracted again. If supported by the video player, you can enable or disable subtitles in the player's subtitle management.
10. By default, a subtitle file with the same name as the original video will be generated in the original video directory (video_name.srt).
11. Unrecognized speech will be directly copied from the original audio.
12. If you use the background music removal function for the first time, you will need to download the model, which may take some time. You can download the compressed file "2stems.zip" and extract the files to the directory "pretrained_models/2stems". [**Download Model Package**](https://github.com/jianchang512/pyvideotrans/releases/download/v0.3/2stems.zip)

# Source Code Deployment

1. Set up a Python 3.9+ environment.
2. Clone the repository: `git clone https://github.com/jianchang512/pyvideotrans`
3. Navigate to the cloned repository: `cd pyvideotrans`
4. Install the required packages: `pip install -r requirements.txt`
5. Unzip `ffmpeg.zip` in the root directory.
6. Run `python sp.py` to open the software interface.
7. If you plan to use the background music removal feature, you will need to download the model, which may take some time. You can download the compressed file "2stems.zip" and extract the files to the directory "\pretrained_models/2stems". [**Download Model Package**](https://github.com/jianchang512/pyvideotrans/releases/download/v0.3/2stems.zip)

# CLI Usage

> After deploying the source code as mentioned above, execute `python cli.py` to use it in the command line.
>

### Supported Parameters

**--source_mp4**: [Required] Path of the video to be translated, must end with .mp4.

**--target_dir**: Directory to store the translated video. By default, it is stored in the "_video_out" folder in the source video directory.

**--source_language**: Language code of the video. Default is `en` (zh-cn | zh-tw | en | fr | de | ja | ko | ru | es | th | it | pt | vi | ar)

**--target_language**: Language code of the target language. Default is `zh-cn` (zh-cn | zh-tw | en | fr | de | ja | ko | ru | es | th | it | pt | vi | ar)

**--proxy**: Specify an HTTP proxy address. Default is None. If you are unable to access Google from your location, you need to provide a proxy address. For example: `http://127.0.0.1:10809`

**--voice_replace**: Provide the corresponding character name based on the target language code. Make sure the first two letters of the character name match the first two letters of the target language code. If you are unsure how to fill in this parameter, run `python cli.py show_voice` to display the available character names for each language.


    af: af-ZA-AdriNeural, af-ZA-WillemNeural
    sq: sq-AL-AnilaNeural, sq-AL-IlirNeural
    am: am-ET-AmehaNeural, am-ET-MekdesNeural
    ar: ar-DZ-AminaNeural, ar-DZ-IsmaelNeural, ar-BH-AliNeural, ar-BH-LailaNeural, ar-EG-SalmaNeural, ar-EG-ShakirNeural, ar-IQ-BasselNeural, ar-IQ-Ran
    aNeural, ar-JO-SanaNeural, ar-JO-TaimNeural, ar-KW-FahedNeural, ar-KW-NouraNeural, ar-LB-LaylaNeural, ar-LB-RamiNeural, ar-LY-ImanNeural, ar-LY-Oma
    rNeural, ar-MA-JamalNeural, ar-MA-MounaNeural, ar-OM-AbdullahNeural, ar-OM-AyshaNeural, ar-QA-AmalNeural, ar-QA-MoazNeural, ar-SA-HamedNeural, ar-S
    A-ZariyahNeural, ar-SY-AmanyNeural, ar-SY-LaithNeural, ar-TN-HediNeural, ar-TN-ReemNeural, ar-AE-FatimaNeural, ar-AE-HamdanNeural, ar-YE-MaryamNeur
    al, ar-YE-SalehNeural
    az: az-AZ-BabekNeural, az-AZ-BanuNeural
    bn: bn-BD-NabanitaNeural, bn-BD-PradeepNeural, bn-IN-BashkarNeural, bn-IN-TanishaaNeural
    bs: bs-BA-GoranNeural, bs-BA-VesnaNeural
    bg: bg-BG-BorislavNeural, bg-BG-KalinaNeural
    my: my-MM-NilarNeural, my-MM-ThihaNeural
    ca: ca-ES-EnricNeural, ca-ES-JoanaNeural
    zh: zh-HK-HiuGaaiNeural, zh-HK-HiuMaanNeural, zh-HK-WanLungNeural, zh-CN-XiaoxiaoNeural, zh-CN-XiaoyiNeural, zh-CN-YunjianNeural, zh-CN-YunxiNeural
    , zh-CN-YunxiaNeural, zh-CN-YunyangNeural, zh-CN-liaoning-XiaobeiNeural, zh-TW-HsiaoChenNeural, zh-TW-YunJheNeural, zh-TW-HsiaoYuNeural, zh-CN-shaa
    nxi-XiaoniNeural
    hr: hr-HR-GabrijelaNeural, hr-HR-SreckoNeural
    cs: cs-CZ-AntoninNeural, cs-CZ-VlastaNeural
    da: da-DK-ChristelNeural, da-DK-JeppeNeural
    nl: nl-BE-ArnaudNeural, nl-BE-DenaNeural, nl-NL-ColetteNeural, nl-NL-FennaNeural, nl-NL-MaartenNeural
    en: en-AU-NatashaNeural, en-AU-WilliamNeural, en-CA-ClaraNeural, en-CA-LiamNeural, en-HK-SamNeural, en-HK-YanNeural, en-IN-NeerjaExpressiveNeural,
    en-IN-NeerjaNeural, en-IN-PrabhatNeural, en-IE-ConnorNeural, en-IE-EmilyNeural, en-KE-AsiliaNeural, en-KE-ChilembaNeural, en-NZ-MitchellNeural, en-
    NZ-MollyNeural, en-NG-AbeoNeural, en-NG-EzinneNeural, en-PH-JamesNeural, en-PH-RosaNeural, en-SG-LunaNeural, en-SG-WayneNeural, en-ZA-LeahNeural, e
    n-ZA-LukeNeural, en-TZ-ElimuNeural, en-TZ-ImaniNeural, en-GB-LibbyNeural, en-GB-MaisieNeural, en-GB-RyanNeural, en-GB-SoniaNeural, en-GB-ThomasNeur
    al, en-US-AriaNeural, en-US-AnaNeural, en-US-ChristopherNeural, en-US-EricNeural, en-US-GuyNeural, en-US-JennyNeural, en-US-MichelleNeural, en-US-R
    ogerNeural, en-US-SteffanNeural
    et: et-EE-AnuNeural, et-EE-KertNeural
    fil: fil-PH-AngeloNeural, fil-PH-BlessicaNeural
    fi: fi-FI-HarriNeural, fi-FI-NooraNeural
    fr: fr-BE-CharlineNeural, fr-BE-GerardNeural, fr-CA-AntoineNeural, fr-CA-JeanNeural, fr-CA-SylvieNeural, fr-FR-DeniseNeural, fr-FR-EloiseNeural, fr
    -FR-HenriNeural, fr-CH-ArianeNeural, fr-CH-FabriceNeural
    gl: gl-ES-RoiNeural, gl-ES-SabelaNeural
    ka: ka-GE-EkaNeural, ka-GE-GiorgiNeural
    de: de-AT-IngridNeural, de-AT-JonasNeural, de-DE-AmalaNeural, de-DE-ConradNeural, de-DE-KatjaNeural, de-DE-KillianNeural, de-CH-JanNeural, de-CH-Le
    niNeural
    el: el-GR-AthinaNeural, el-GR-NestorasNeural
    gu: gu-IN-DhwaniNeural, gu-IN-NiranjanNeural
    he: he-IL-AvriNeural, he-IL-HilaNeural
    hi: hi-IN-MadhurNeural, hi-IN-SwaraNeural
    hu: hu-HU-NoemiNeural, hu-HU-TamasNeural
    is: is-IS-GudrunNeural, is-IS-GunnarNeural
    id: id-ID-ArdiNeural, id-ID-GadisNeural
    ga: ga-IE-ColmNeural, ga-IE-OrlaNeural
    it: it-IT-DiegoNeural, it-IT-ElsaNeural, it-IT-IsabellaNeural
    ja: ja-JP-KeitaNeural, ja-JP-NanamiNeural
    jv: jv-ID-DimasNeural, jv-ID-SitiNeural
    kn: kn-IN-GaganNeural, kn-IN-SapnaNeural
    kk: kk-KZ-AigulNeural, kk-KZ-DauletNeural
    km: km-KH-PisethNeural, km-KH-SreymomNeural
    ko: ko-KR-InJoonNeural, ko-KR-SunHiNeural
    lo: lo-LA-ChanthavongNeural, lo-LA-KeomanyNeural
    lv: lv-LV-EveritaNeural, lv-LV-NilsNeural
    lt: lt-LT-LeonasNeural, lt-LT-OnaNeural
    mk: mk-MK-AleksandarNeural, mk-MK-MarijaNeural
    ms: ms-MY-OsmanNeural, ms-MY-YasminNeural
    ml: ml-IN-MidhunNeural, ml-IN-SobhanaNeural
    mt: mt-MT-GraceNeural, mt-MT-JosephNeural
    mr: mr-IN-AarohiNeural, mr-IN-ManoharNeural
    mn: mn-MN-BataaNeural, mn-MN-YesuiNeural
    ne: ne-NP-HemkalaNeural, ne-NP-SagarNeural
    nb: nb-NO-FinnNeural, nb-NO-PernilleNeural
    ps: ps-AF-GulNawazNeural, ps-AF-LatifaNeural
    fa: fa-IR-DilaraNeural, fa-IR-FaridNeural
    pl: pl-PL-MarekNeural, pl-PL-ZofiaNeural
    pt: pt-BR-AntonioNeural, pt-BR-FranciscaNeural, pt-PT-DuarteNeural, pt-PT-RaquelNeural
    ro: ro-RO-AlinaNeural, ro-RO-EmilNeural
    ru: ru-RU-DmitryNeural, ru-RU-SvetlanaNeural
    sr: sr-RS-NicholasNeural, sr-RS-SophieNeural
    si: si-LK-SameeraNeural, si-LK-ThiliniNeural
    sk: sk-SK-LukasNeural, sk-SK-ViktoriaNeural
    sl: sl-SI-PetraNeural, sl-SI-RokNeural
    so: so-SO-MuuseNeural, so-SO-UbaxNeural
    es: es-AR-ElenaNeural, es-AR-TomasNeural, es-BO-MarceloNeural, es-BO-SofiaNeural, es-CL-CatalinaNeural, es-CL-LorenzoNeural, es-CO-GonzaloNeural, e
    s-CO-SalomeNeural, es-CR-JuanNeural, es-CR-MariaNeural, es-CU-BelkysNeural, es-CU-ManuelNeural, es-DO-EmilioNeural, es-DO-RamonaNeural, es-EC-Andre
    aNeural, es-EC-LuisNeural, es-SV-LorenaNeural, es-SV-RodrigoNeural, es-GQ-JavierNeural, es-GQ-TeresaNeural, es-GT-AndresNeural, es-GT-MartaNeural,
    es-HN-CarlosNeural, es-HN-KarlaNeural, es-MX-DaliaNeural, es-MX-JorgeNeural, es-NI-FedericoNeural, es-NI-YolandaNeural, es-PA-MargaritaNeural, es-P
    A-RobertoNeural, es-PY-MarioNeural, es-PY-TaniaNeural, es-PE-AlexNeural, es-PE-CamilaNeural, es-PR-KarinaNeural, es-PR-VictorNeural, es-ES-AlvaroNe
    ural, es-ES-ElviraNeural, es-US-AlonsoNeural, es-US-PalomaNeural, es-UY-MateoNeural, es-UY-ValentinaNeural, es-VE-PaolaNeural, es-VE-SebastianNeura
    l
    su: su-ID-JajangNeural, su-ID-TutiNeural
    sw: sw-KE-RafikiNeural, sw-KE-ZuriNeural, sw-TZ-DaudiNeural, sw-TZ-RehemaNeural
    sv: sv-SE-MattiasNeural, sv-SE-SofieNeural
    ta: ta-IN-PallaviNeural, ta-IN-ValluvarNeural, ta-MY-KaniNeural, ta-MY-SuryaNeural, ta-SG-AnbuNeural, ta-SG-VenbaNeural, ta-LK-KumarNeural, ta-LK-S
    aranyaNeural
    te: te-IN-MohanNeural, te-IN-ShrutiNeural
    th: th-TH-NiwatNeural, th-TH-PremwadeeNeural
    tr: tr-TR-AhmetNeural, tr-TR-EmelNeural
    uk: uk-UA-OstapNeural, uk-UA-PolinaNeural
    ur: ur-IN-GulNeural, ur-IN-SalmanNeural, ur-PK-AsadNeural, ur-PK-UzmaNeural
    uz: uz-UZ-MadinaNeural, uz-UZ-SardorNeural
    vi: vi-VN-HoaiMyNeural, vi-VN-NamMinhNeural
    cy: cy-GB-AledNeural, cy-GB-NiaNeural
    zu: zu-ZA-ThandoNeural, zu-ZA-ThembaNeural


**--voice_rate**: Adjust the speed of the voice dubbing. Use negative numbers to decrease the speed and positive numbers to increase it. The default value is `10`, which represents an increase in speed.

**--remove_background**: Specify this parameter to remove the background music.


**CLI Example**

`python cli.py --source_mp4 "D:/video/ex.mp4" --source_language en --target_language zh-cn --proxy "http://127.0.0.1:10809" --voice_replace zh-CN-XiaoxiaoNeural`

In the above example, it translates the video located at "D:/video/ex.mp4" from English to Chinese, sets the proxy to "http://127.0.0.1:10809", and uses the voice replacement of "zh-CN-XiaoxiaoNeural".

# Software Preview Screenshots

![](./images/en1.png)
![](./images/cli.png)

# Video Comparison Before and After Translation

[Original Video](https://www.wonyes.org/images/raw.mp4)

[Translated Video](https://www.wonyes.org/images/new.mp4)

# Potential Issues

The translation process uses requests to make calls to the Google API, and frequent calls may trigger rate limits.

# Acknowledgments

This program relies on the following open-source projects.

1. pydub
2. ffmpeg
3. pysimpleGUI
4. googletrans
5. httpx
6. SpeechRecognition
7. edge-tts
8. Spleeter
9. openai-whisper