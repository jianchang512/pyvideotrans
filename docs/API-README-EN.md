# API Interface Documentation

Default interface address: http://127.0.0.1:9011

> You can change the IP and port by creating a host.txt file in the same directory as api.py(api.exe), for example, the content of host.txt is as follows:
>
> 127.0.0.1:9801, then the interface address will become http://127.0.0.1:9801

## Interface List

### `/tts` - Subtitle Synthesis Voice Interface

#### Request Data Type
`Content-Type: application/json`

#### Request Parameters

| Parameter Name    | Data Type | Required | Default Value | Optional Values | Description |
| ---------------- | --------- | -------- | ------------- | --------------- | ----------- |
| name              | String    | Yes      | None          | None            | The absolute path of the required subtitle or valid srt subtitle format content |
| tts_type          | Number    | Yes      | None          | 0-11            | Voiceover channels, specific values correspond to channel names, see below |
| voice_role        | String    | Yes      | None          | -                | Corresponding voiceover channel role name. Edge-tts/azure-tts/302.ai(azure model) role names vary depending on the selected target language, see below |
| target_language   | String    | Yes      | None          | Language codes for required voiceover | Simplified Chinese(zh-cn), Traditional Chinese(zh-tw), English(en), French(fr), German(de), Japanese(ja), Korean(ko), Russian(ru), Spanish(es), Thai(th), Italian(it), Portuguese(pt), Vietnamese(vi), Arabic(ar), Turkish(tr), Hindi(hi), Hungarian(hu), Ukrainian(uk), Indonesian(id), Malay(ms), Kazakh(kk), Czech(cs), Polish(pl), Dutch(nl), Swedish(sv) |
| voice_rate        | String    | No       | None          | Speed up `+number%`, slow down `-number%` | Voiceover speed adjustment |
| volume            | String    | No       | None          | Increase volume `+number%`, decrease volume `-number%` | Volume change value (effective only for edge-tts voiceover channel) |
| pitch             | String    | No       | None          | Raise pitch `+numberHz`, lower pitch `-numberHz` | Pitch change value (effective only for edge-tts voiceover channel) |
| out_ext           | String    | No       | wav           | mp3\|wav\|flac\|aac | Output voiceover file type |
| voice_autorate    | Boolean   | No       | False         | True\|False     | Whether to automatically increase speaking speed |

> **tts_type 0-11 represent**
> 0=Edge-TTS
> 1=CosyVoice
> 2=ChatTTS
> 3=302.AI
> 4=FishTTS
> 5=Azure-TTS"
> 6=GPT-SoVITS
> 7=clone-voice
> 8=OpenAI TTS
> 9=Elevenlabs.io
> 10=Google TTS
> 11=Custom TTS API

#### Return Data Type
JSON format

#### Return Example
Success:
```json
{
     "code": 0,
     "msg": "ok",
     "task_id": "task id"
}
```

Failure:
```json
{
     "code": 1,
     "msg": "Error message"
}
```

#### Request Example
```python
requests.post("http://127.0.0.1:9011/tts", json={
     "name": "C:/users/c1/videos/zh0.srt",
     "voice_role": "zh-CN-YunjianNeural",
     "target_language_code": "zh-cn",
     "voice_rate": "+0%",
     "volume": "+0%",
     "pitch": "+0Hz",
     "tts_type": "0",
     "out_ext": "mp3",
     "voice_autorate": True,
})
```

----

### `/translate_srt` - Subtitle Translation Interface

#### Request Data Type
`Content-Type: application/json`

#### Request Parameters

| Parameter Name    | Data Type | Required | Default Value | Optional Values | Description |
| ---------------- | --------- | -------- | ------------- | --------------- | ----------- |
| name              | String    | Yes      | None          | None            | The absolute path of the required subtitle or valid srt subtitle format content |
| translate_type    | Integer   | Yes      | None          | 0-14            | Represents translation channels, details see below |
| target_language   | String    | Yes      | None          | -                | Simplified Chinese(zh-cn), Traditional Chinese(zh-tw), English(en), French(fr), German(de), Japanese(ja), Korean(ko), Russian(ru), Spanish(es), Thai(th), Italian(it), Portuguese(pt), Vietnamese(vi), Arabic(ar), Turkish(tr), Hindi(hi), Hungarian(hu), Ukrainian(uk), Indonesian(id), Malay(ms), Kazakh(kk), Czech(cs), Polish(pl), Dutch(nl), Swedish(sv) |
| source_code       | String    | No       | None          | -                | Simplified Chinese(zh-cn), Traditional Chinese(zh-tw), English(en), French(fr), German(de), Japanese(ja), Korean(ko), Russian(ru), Spanish(es), Thai(th), Italian(it), Portuguese(pt), Vietnamese(vi), Arabic(ar), Turkish(tr), Hindi(hi), Hungarian(hu), Ukrainian(uk), Indonesian(id), Malay(ms), Kazakh(kk), Czech(cs), Polish(pl), Dutch(nl), Swedish(sv) |

> **translate_type translation channels 0-14**
> 0=Google Translate
> 1=Microsoft Translator
> 2=302.AI
> 3=Baidu Translate
> 4=DeepL
> 5=DeepLx
> 6=Offline Translation OTT
> 7=Tencent Translator
> 8=OpenAI ChatGPT
> 9=Local Large Model and Compatible AI
> 10=Byte Volcano Engine
> 11=AzureAI GPT
> 12=Gemini
> 13=Custom Translation API
> 14=FreeGoogle Translate

#### Return Data Type
JSON format

#### Return Example
Success:
```json
{
     "code": 0,
     "msg": "ok",
     "task_id": "task id"
}
```

Failure:
```json
{
     "code": 1,
     "msg": "Error message"
}
```

#### Request Example
```python
requests.post("http://127.0.0.1:9011/translate_srt", json={
     "name": "C:/users/c1/videos/zh0.srt",
     "target_language": "en",
     "translate_type": 0
})
```

----

### `/recogn` - Speech Recognition, Audio/Video to Subtitle Interface

#### Request Data Type
`Content-Type: application/json`

#### Request Parameters

| Parameter Name    | Data Type | Required | Default Value | Optional Values | Description |
| ---------------- | --------- | -------- | ------------- | --------------- | ----------- |
| name              | String    | Yes      | None          | None            | The absolute path of the required audio or video |
| recogn_type       | Number    | Yes      | None          | 0-6             | Speech recognition mode, 0=faster-whisper local model recognition, 1=openai-whisper local model recognition, 2=Google recognition API, 3=zh_recogn Chinese recognition, 4=doubao model recognition, 5=Custom recognition API, 6=OpenAI recognition API |
| model_name        | String    | Yes      | None          | -                | When choosing faster-whisper/openai-whisper mode, you must enter the model name |
| detect_language   | String    | Yes      | None          | -                | Chinese(zh), English(en), French(fr), German(de), Japanese(ja), Korean(ko), Russian(ru), Spanish(es), Thai(th), Italian(it), Portuguese(pt), Vietnamese(vi), Arabic(ar), Turkish(tr), Hindi(hi), Hungarian(hu), Ukrainian(uk), Indonesian(id), Malay(ms), Kazakh(kk), Czech(cs), Polish(pl), Dutch(nl), Swedish(sv) |
| split_type        | String    | No       | all           | all\|avg         | Split type, all=overall recognition, avg=equal split |
| is_cuda           | Boolean   | No       | False         | True\|False     | Whether to enable CUDA acceleration |

#### Return Data Type
JSON format

#### Return Example
Success:
```json
{
     "code": 0,
     "msg": "ok",
     "task_id": "task id"
}
```

Failure:
```json
{
     "code": 1,
     "msg": "Error message"
}
```

#### Request Example
```python
requests.post("http://127.0.0.1:9011/recogn", json={
     "name": "C:/Users/c1/Videos/10ass.mp4",
     "recogn_type": 0,
     "split_type": "overall",
     "model_name": "tiny",
     "is_cuda": False,
     "detect_language": "zh",
})
```

----

### `/trans_video` - Video Full Translation Interface

#### Request Data Type
`Content-Type: application/json`

#### Request Parameters

| Parameter Name    | Data Type | Required | Default Value | Optional Values | Description |
| ---------------- | --------- | -------- | ------------- | --------------- | ----------- |
| name              | String    | Yes      | None          | None            | The absolute path of the required audio or video |
| recogn_type       | Number    | Yes      | None          | 0-6             | Speech recognition mode, 0=faster-whisper local model recognition, 1=openai-whisper local model recognition, 2=Google recognition API, 3=zh_recogn Chinese recognition, 4=doubao model recognition, 5=Custom recognition API, 6=OpenAI recognition API |
| model_name        | String    | Yes      | None          | -                | When choosing faster-whisper/openai-whisper mode, you must enter the model name |
| translate_type    | Integer   | Yes      | None          | 0-14            | Translation channels, see below |
| target_language   | String    | Yes      | None          | -                | Target language for translation, simplified Chinese(zh-cn), traditional Chinese(zh-tw), English(en), French(fr), German(de), Japanese(ja), Korean(ko), Russian(ru), Spanish(es), Thai(th), Italian(it), Portuguese(pt), Vietnamese(vi), Arabic(ar), Turkish(tr), Hindi(hi), Hungarian(hu), Ukrainian(uk), Indonesian(id), Malay(ms), Kazakh(kk), Czech(cs), Polish(pl), Dutch(nl), Swedish(sv) |
| source_language   | String    | Yes      | None          | -                | Language spoken by humans in the audio, simplified Chinese(zh-cn), traditional Chinese(zh-tw), English(en), French(fr), German(de), Japanese(ja), Korean(ko), Russian(ru), Spanish(es), Thai(th), Italian(it), Portuguese(pt), Vietnamese(vi), Arabic(ar), Turkish(tr), Hindi(hi), Hungarian(hu), Ukrainian(uk), Indonesian(id), Malay(ms), Kazakh(kk), Czech(cs), Polish(pl), Dutch(nl), Swedish(sv) |
| tts_type          | Number    | Yes      | None          | 0-11            | Voiceover channels, see below |
| voice_role        | String    | Yes      | None          | -                | Corresponding voiceover channel role name. Edge-tts/azure-tts/302.ai(azure model) role names vary depending on the selected target language, see below |
| voice_rate        | String    | No       | None          | Speed up `+number%`, slow down `-number%` | Voiceover speed adjustment |
| volume            | String    | No       | None          | Increase volume `+number%`, decrease volume `-number%` | Volume change value (effective only for edge-tts voiceover channel) |
| pitch             | String    | No       | None          | Raise pitch `+numberHz`, lower pitch `-numberHz` | Pitch change value (effective only for edge-tts voiceover channel) |
| out_ext           | String    | No       | wav           | mp3\|wav\|flac\|aac | Output voiceover file type |
| voice_autorate    | Boolean   | No       | False         | True\|False     | Whether to automatically increase speaking speed |
| subtitle_type     | Integer   | No       | 0             | 0-4             | Subtitle embedding type, 0=No subtitle embedding, 1=Embed hard subtitles, 2=Embed soft subtitles, 3=Embed dual hard subtitles, 4=Embed dual soft subtitles |
| append_video      | Boolean   | No       | False         | True\|False     | Whether to extend the video end |
| only_video        | Boolean   | No       | False         | True\|False     | Whether to only generate video files |

> **translate_type translation channels 0-14**
> 0=Google Translate
> 1=Microsoft Translator
> 2=302.AI
> 3=Baidu Translate
> 4=DeepL
> 5=DeepLx
> 6=Offline Translation OTT
> 7=Tencent Translator
> 8=OpenAI ChatGPT
> 9=Local Large Model and Compatible AI
> 10=Byte Volcano Engine
> 11=AzureAI GPT
> 12=Gemini
> 13=Custom Translation API
> 14=FreeGoogle Translate

> **tts_type voiceover channels 0-11 represent**
> 0=Edge-TTS
> 1=CosyVoice
> 2=ChatTTS
> 3=302.AI
> 4=FishTTS
> 5=Azure-TTS
> 6=GPT-SoVITS
> 7=clone-voice
> 8=OpenAI TTS
> 9=Elevenlabs.io
> 10=Google TTS
> 11=Custom TTS API

#### Return Data Type
JSON format

#### Return Example
Success:
```json
{
     "code": 0,
     "msg": "ok",
     "task_id": "task id"
}
```

Failure:
```json
{
     "code": 1,
     "msg": "Error message"
}
```

#### Request Example
```python
requests.post("http://127.0.0.1:9011/trans_video", json={
     "name": "C:/Users/c1/Videos/10ass.mp4",
     "recogn_type": 0,
     "split_type": "overall",
     "model_name": "tiny",
     "detect_language": "zh",
     "translate_type": 0,
     "source_language": "zh-cn",
     "target_language": "en",
     "tts_type": 0,
     "voice_role": "zh-CN-YunjianNeural",
     "voice_rate": "+0%",
     "volume": "+0%",
     "pitch": "+0Hz",
     "voice_autorate": True,
     "video_autorate": True,
     "is_separate": False,
     "back_audio": "",
     "subtitle_type": 1,
     "append_video": False,
     "is_cuda": False,
})
```

----

### `/task_status` - Get Task Progress Interface

#### Request Data Type
`GET` or `POST`

#### Request Parameters

| Parameter Name    | Data Type | Required | Description |
| ---------------- | --------- | -------- | ----------- |
| task_id           | String    | Yes      | Task ID     |

#### Return Data Type
JSON format

#### Return Example
In progress:
```json
{
     "code": -1,
     "msg": "Synthesizing sound"
}
```

Success:
```json
{
     "code": 0,
     "msg": "ok",
     "data": {
         "absolute_path": ["/data/1.srt", "/data/1.mp4"],
         "url": ["http://127.0.0.1:9011/task_id/1.srt"]
     }
}
```

Failure:
```json
{
     "code": 1,
     "msg": "Task does not exist"
}
```

#### Request Example
```python
requests.post("http://127.0.0.1:9011/task_status", json={
     "task_id": "06c238d250f0b51248563c405f1d7294"
})
```

---

## Translation Channel Numbers Corresponding to translate_type 0-14

- 0=Google Translate
- 1=Microsoft Translator
- 2=302.AI
- 3=Baidu Translate
- 4=DeepL
- 5=DeepLx
- 6=Offline Translation OTT
- 7=Tencent Translator
- 8=OpenAI ChatGPT
- 9=Local Large Model and Compatible AI
- 10=Byte Volcano Engine
- 11=AzureAI GPT
- 12=Gemini
- 13=Custom Translation API
- 14=FreeGoogle Translate

## Voiceover Channel Names Corresponding to tts_type 0-11

- 0=Edge-TTS
- 1=CosyVoice
- 2=ChatTTS
- 3=302.AI
- 4=FishTTS
- 5=Azure-TTS
- 6=GPT-SoVITS
- 7=clone-voice
- 8=OpenAI TTS
- 9=Elevenlabs.io
- 10=Google TTS
- 11=Custom TTS API

## edge-tts Language Codes and Role Name Mapping

```
{
   "ar": [
    "No",
     "ar-DZ-AminaNeural",
     "ar-DZ-IsmaelNeural",
     "ar-BH-AliNeural",
     "ar-BH-LailaNeural",
     "ar-EG-SalmaNeural",
     "ar-EG-ShakirNeural",
     "ar-IQ-BasselNeural",
     "ar-IQ-RanaNeural",
     "ar-JO-SanaNeural",
     "ar-JO-TaimNeural",
     "ar-KW-FahedNeural",
     "ar-KW-NouraNeural",
     "ar-LB-LaylaNeural",
     "ar-LB-RamiNeural",
     "ar-LY-ImanNeural",
     "ar-LY-OmarNeural",
     "ar-MA-JamalNeural",
     "ar-MA-MounaNeural",
     "ar-OM-AbdullahNeural",
     "ar-OM-AyshaNeural",
     "ar-QA-AmalNeural",
     "ar-QA-MoazNeural",
     "ar-SA-HamedNeural",
     "ar-SA-ZariyahNeural",
     "ar-SY-AmanyNeural",
     "ar-SY-LaithNeural",
     "ar-TN-HediNeural",
     "ar-TN-ReemNeural",
     "ar-AE-FatimaNeural",
     "ar-AE-HamdanNeural",
     "ar-YE-MaryamNeural",
     "ar-YE-SalehNeural"
   ],
   "zh": [
    "No",
     "zh-HK-HiuGaaiNeural",
     "zh-HK-HiuMaanNeural",
     "zh-HK-WanLungNeural",
     "zh-CN-XiaoxiaoNeural",
     "zh-CN-XiaoyiNeural",
     "zh-CN-YunjianNeural",
     "zh-CN-YunxiNeural",
     "zh-CN-YunxiaNeural",
     "zh-CN-YunyangNeural",
     "zh-CN-liaoning-XiaobeiNeural"
   ],
   "cs": [
    "No",
     "cs-CZ-AntoninNeural",
     "cs-CZ-VlastaNeural"
   ],
   "nl": [
    "No",
     "nl-BE-ArnaudNeural",
     "nl-BE-DenaNeural",
     "nl-NL-ColetteNeural",
     "nl-NL-FennaNeural",
     "nl-NL-MaartenNeural"
   ],
   "en": [
    "No",
     "en-AU-NatashaNeural",
     "en-AU-WilliamNeural",
     "en-CA-ClaraNeural",
     "en-CA-LiamNeural",
     "en-HK-SamNeural",
     "en-HK-YanNeural",
     "en-IN-NeerjaExpressiveNeural",
     "en-IN-NeerjaNeural",
     "en-IN-PrabhatNeural",
     "en-IE-ConnorNeural",
     "en-IE-EmilyNeural",
     "en-KE-AsiliaNeural",
     "en-KE-ChilembaNeural",
     "en-NZ-MitchellNeural",
     "en-NZ-MollyNeural",
     "en-NG-AbeoNeural",
     "en-NG-EzinneNeural",
     "en-PH-JamesNeural",
     "en-US-AvaNeural",
     "en-US-AndrewNeural",
     "en-US-EmmaNeural",
     "en-US-BrianNeural",
     "en-PH-RosaNeural",
     "en-SG-LunaNeural",
     "en-SG-WayneNeural",
     "en-ZA-LeahNeural",
     "en-ZA-LukeNeural",
     "en-TZ-ElimuNeural",
     "en-TZ-ImaniNeural",
     "en-GB-LibbyNeural",
     "en-GB-MaisieNeural",
     "en-GB-RyanNeural",
     "en-GB-SoniaNeural",
     "en-GB-ThomasNeural",
     "en-US-AnaNeural",
     "en-US-AriaNeural",
     "en-US-ChristopherNeural",
     "en-US-EricNeural",
     "en-US-GuyNeural",
     "en-US-JennyNeural",
     "en-US-MichelleNeural",
     "en-US-RogerNeural",
     "en-US-SteffanNeural"
   ],
   "fr": [
    "No",
     "fr-BE-CharlineNeural",
     "fr-BE-GerardNeural",
     "fr-CA-ThierryNeural",
     "fr-CA-AntoineNeural",
     "fr-CA-JeanNeural",
     "fr-CA-SylvieNeural",
     "fr-FR-VivienneMultilingualNeural",
     "fr-FR-RemyMultilingualNeural",
     "fr-FR-DeniseNeural",
     "fr-FR-EloiseNeural",
     "fr-FR-HenriNeural",
     "fr-CH-ArianeNeural",
     "fr-CH-FabriceNeural"
   ],
   "de": [
    "No",
     "de-AT-IngridNeural",
     "de-AT-JonasNeural",
     "de-DE-SeraphinaMultilingualNeural",
     "de-DE-FlorianMultilingualNeural",
     "de-DE-AmalaNeural",
     "de-DE-ConradNeural",
     "de-DE-KatjaNeural",
     "de-DE-KillianNeural",
     "de-CH-JanNeural",
     "de-CH-LeniNeural"
   ],
   "hi": [
    "No",
     "hi-IN-MadhurNeural",
     "hi-IN-SwaraNeural"
   ],
   "hu": [
    "No",
     "hu-HU-NoemiNeural",
     "hu-HU-TamasNeural"
   ],
   "id": [
    "No",
     "id-ID-ArdiNeural",
     "id-ID-GadisNeural"
   ],
   "it": [
    "No",
     "it-IT-GiuseppeNeural",
     "it-IT-DiegoNeural",
     "it-IT-ElsaNeural",
     "it-IT-IsabellaNeural"
   ],
   "ja": [
    "No",
     "ja-JP-KeitaNeural",
     "ja-JP-NanamiNeural"
   ],
   "kk": [
    "No",
     "kk-KZ-AigulNeural",
     "kk-KZ-DauletNeural"
   ],
   "ko": [
    "No",
     "ko-KR-HyunsuNeural",
     "ko-KR-InJoonNeural",
     "ko-KR-SunHiNeural"
   ],
   "ms": [
    "No",
     "ms-MY-OsmanNeural",
     "ms-MY-YasminNeural"
   ],
   "pl": [
    "No",
     "pl-PL-MarekNeural",
     "pl-PL-ZofiaNeural"
   ],
   "pt": [
    "No",
     "pt-BR-ThalitaNeural",
     "pt-BR-AntonioNeural",
     "pt-BR-FranciscaNeural",
     "pt-PT-DuarteNeural",
     "pt-PT-RaquelNeural"
   ],
   "ru": [
    "No",
     "ru-RU-DmitryNeural",
     "ru-RU-SvetlanaNeural"
   ],
   "es": [
    "No",
     "es-AR-ElenaNeural",
     "es-AR-TomasNeural",
     "es-BO-MarceloNeural",
     "es-BO-SofiaNeural",
     "es-CL-CatalinaNeural",
     "es-CL-LorenzoNeural",
     "es-ES-XimenaNeural",
     "es-CO-GonzaloNeural",
     "es-CO-SalomeNeural",
     "es-CR-JuanNeural",
     "es-CR-MariaNeural",
     "es-CU-BelkysNeural",
     "es-CU-ManuelNeural",
     "es-DO-EmilioNeural",
     "es-DO-RamonaNeural",
     "es-EC-AndreaNeural",
     "es-EC-LuisNeural",
     "es-SV-LorenaNeural",
     "es-SV-RodrigoNeural",
     "es-GQ-JavierNeural",
     "es-GQ-TeresaNeural",
     "es-GT-AndresNeural",
     "es-GT-MartaNeural",
     "es-HN-CarlosNeural",
     "es-HN-KarlaNeural",
     "es-MX-DaliaNeural",
     "es-MX-JorgeNeural",
     "es-NI-FedericoNeural",
     "es-NI-YolandaNeural",
     "es-PA-MargaritaNeural",
     "es-PA-RobertoNeural",
     "es-PY-MarioNeural",
     "es-PY-TaniaNeural",
     "es-PE-AlexNeural",
     "es-PE-CamilaNeural",
     "es-PR-KarinaNeural",
     "es-PR-VictorNeural",
     "es-ES-AlvaroNeural",
     "es-ES-ElviraNeural",
     "es-US-AlonsoNeural",
     "es-US-PalomaNeural",
     "es-UY-MateoNeural",
     "es-UY-ValentinaNeural",
     "es-VE-PaolaNeural",
     "es-VE-SebastianNeural"
   ],
   "sv": [
    "No",
     "sv-SE-MattiasNeural",
     "sv-SE-SofieNeural"
   ],
   "th": [
    "No",
     "th-TH-NiwatNeural",
     "th-TH-PremwadeeNeural"
   ],
   "tr": [
    "No",
     "tr-TR-AhmetNeural",
     "tr-TR-EmelNeural"
   ],
   "uk": [
    "No",
     "uk-UA-OstapNeural",
     "uk-UA-PolinaNeural"
   ],
   "vi": [
    "No",
     "vi-VN-HoaiMyNeural",
     "vi-VN-NamMinhNeural"
   ]
}
```

## Azure-tts and 302.ai selection of Azure model language codes and role name mapping
```
{
   "ar": [
    "No",
     "ar-AE-FatimaNeural",
     "ar-AE-HamdanNeural",
     "ar-BH-LailaNeural",
     "ar-BH-AliNeural",
     "ar-DZ-AminaNeural",
     "ar-DZ-IsmaelNeural",
     "ar-EG-SalmaNeural",
     "ar-EG-ShakirNeural",
     "ar-IQ-RanaNeural",
     "ar-IQ-BasselNeural",
     "ar-JO-SanaNeural",
     "ar-JO-TaimNeural",
     "ar-KW-NouraNeural",
     "ar-KW-FahedNeural",
     "ar-LB-LaylaNeural",
     "ar-LB-RamiNeural",
     "ar-LY-ImanNeural",
     "ar-LY-OmarNeural",
     "ar-MA-MounaNeural",
     "ar-MA-JamalNeural",
     "ar-OM-AyshaNeural",
     "ar-OM-AbdullahNeural",
     "ar-QA-AmalNeural",
     "ar-QA-MoazNeural",
     "ar-SA-ZariyahNeural",
     "ar-SA-HamedNeural",
     "ar-SY-AmanyNeural",
     "ar-SY-LaithNeural",
     "ar-TN-ReemNeural",
     "ar-TN-HediNeural",
     "ar-YE-MaryamNeural",
     "ar-YE-SalehNeural"
   ],

   "cs": [
    "No",
     "cs-CZ-VlastaNeural",
     "cs-CZ-AntoninNeural"
   ],

   "de": [
    "No",
     "de-AT-IngridNeural",
     "de-AT-JonasNeural",
     "de-CH-LeniNeural",
     "de-CH-JanNeural",
     "de-DE-KatjaNeural",
     "de-DE-ConradNeural",
     "de-DE-AmalaNeural",
     "de-DE-BerndNeural",
     "de-DE-ChristophNeural",
     "de-DE-ElkeNeural",
     "de-DE-GiselaNeural",
     "de-DE-KasperNeural",
     "de-DE-KillianNeural",
     "de-DE-KlarissaNeural",
     "de-DE-KlausNeural",
     "de-DE-LouisaNeural",
     "de-DE-MajaNeural",
     "de-DE-RalfNeural",
     "de-DE-TanjaNeural",
     "de-DE-FlorianMultilingualNeural",
     "de-DE-SeraphinaMultilingualNeural"
   ],

   "en": [
    "No",
     "en-AU-NatashaNeural",
     "en-AU-WilliamNeural",
     "en-AU-AnnetteNeural",
     "en-AU-CarlyNeural",
     "en-AU-DarrenNeural",
     "en-AU-DuncanNeural",
     "en-AU-ElsieNeural",
     "en-AU-FreyaNeural",
     "en-AU-JoanneNeural",
     "en-AU-KenNeural",
     "en-AU-KimNeural",
     "en-AU-NeilNeural",
     "en-AU-TimNeural",
     "en-AU-TinaNeural",
     "en-CA-ClaraNeural",
     "en-CA-LiamNeural",
     "en-GB-SoniaNeural",
     "en-GB-RyanNeural",
     "en-GB-LibbyNeural",
     "en-GB-AbbiNeural",
     "en-GB-AlfieNeural",
     "en-GB-BellaNeural",
     "en-GB-ElliotNeural",
     "en-GB-EthanNeural",
     "en-GB-HollieNeural",
     "en-GB-MaisieNeural",
     "en-GB-NoahNeural",
     "en-GB-OliverNeural",
     "en-GB-OliviaNeural",
     "en-GB-ThomasNeural",
     "en-HK-YanNeural",
     "en-HK-SamNeural",
     "en-IE-EmilyNeural",
     "en-IE-ConnorNeural",
     "en-IN-NeerjaNeural",
     "en-IN-PrabhatNeural",
     "en-KE-AsiliaNeural",
     "en-KE-ChilembaNeural",
     "en-NG-EzinneNeural",
     "en-NG-AbeoNeural",
     "en-NZ-MollyNeural",
     "en-NZ-MitchellNeural",
     "en-PH-RosaNeural",
     "en-PH-JamesNeural",
     "en-SG-LunaNeural",
     "en-SG-WayneNeural",
     "en-TZ-ImaniNeural",
     "en-TZ-ElimuNeural",
     "en-US-AvaNeural",
     "en-US-AndrewNeural",
     "en-US-EmmaNeural",
     "en-US-BrianNeural",
     "en-US-JennyNeural",
     "en-US-GuyNeural",
     "en-US-AriaNeural",
     "en-US-DavisNeural",
     "en-US-JaneNeural",
     "en-US-JasonNeural",
     "en-US-SaraNeural",
     "en-US-TonyNeural",
     "en-US-NancyNeural",
     "en-US-AmberNeural",
     "en-US-AnaNeural",
     "en-US-AshleyNeural",
     "en-US-BrandonNeural",
     "en-US-ChristopherNeural",
     "en-US-CoraNeural",
     "en-US-ElizabethNeural",
     "en-US-EricNeural",
     "en-US-JacobNeural",
     "en-US-JennyMultilingualNeural",
     "en-US-MichelleNeural",
     "en-US-MonicaNeural",
     "en-US-RogerNeural",
     "en-US-RyanMultilingualNeural",
     "en-US-SteffanNeural",
     "en-US-AIGenerate1Neural",
     "en-US-AIGenerate2Neural",
     "en-US-AndrewMultilingualNeural",
     "en-US-AvaMultilingualNeural",
     "en-US-BlueNeural",
     "en-US-BrianMultilingualNeural",
     "en-US-EmmaMultilingualNeural",
     "en-US-AlloyMultilingualNeural",
     "en-US-EchoMultilingualNeural",
     "en-US-FableMultilingualNeural",
     "en-US-OnyxMultilingualNeural",
     "en-US-NovaMultilingualNeural",
     "en-US-ShimmerMultilingualNeural",
     "en-US-AlloyMultilingualNeuralHD",
     "en-US-EchoMultilingualNeuralHD",
     "en-US-FableMultilingualNeuralHD",
     "en-US-OnyxMultilingualNeuralHD",
     "en-US-NovaMultilingualNeuralHD",
     "en-US-ShimmerMultilingualNeuralHD",
     "en-ZA-LeahNeural",
     "en-ZA-LukeNeural"
   ],
   "es": [
    "No",
     "es-AR-ElenaNeural",
     "es-AR-TomasNeural",
     "es-BO-SofiaNeural",
     "es-BO-MarceloNeural",
     "es-CL-CatalinaNeural",
     "es-CL-LorenzoNeural",
     "es-CO-SalomeNeural",
     "es-CO-GonzaloNeural",
     "es-CR-MariaNeural",
     "es-CR-JuanNeural",
     "es-CU-BelkysNeural",
     "es-CU-ManuelNeural",
     "es-DO-RamonaNeural",
     "es-DO-EmilioNeural",
     "es-EC-AndreaNeural",
     "es-EC-LuisNeural",
     "es-ES-ElviraNeural",
     "es-ES-AlvaroNeural",
     "es-ES-AbrilNeural",
     "es-ES-ArnauNeural",
     "es-ES-DarioNeural",
     "es-ES-EliasNeural",
     "es-ES-EstrellaNeural",
     "es-ES-IreneNeural",
     "es-ES-LaiaNeural",
     "es-ES-LiaNeural",
     "es-ES-NilNeural",
     "es-ES-SaulNeural",
     "es-ES-TeoNeural",
     "es-ES-TrianaNeural",
     "es-ES-VeraNeural",
     "es-ES-XimenaNeural",
     "es-GQ-TeresaNeural",
     "es-GQ-JavierNeural",
     "es-GT-MartaNeural",
     "es-GT-AndresNeural",
     "es-HN-KarlaNeural",
     "es-HN-CarlosNeural",
     "es-MX-DaliaNeural",
     "es-MX-JorgeNeural",
     "es-MX-BeatrizNeural",
     "es-MX-CandelaNeural",
     "es-MX-CarlotaNeural",
     "es-MX-CecilioNeural",
     "es-MX-GerardoNeural",
     "es-MX-LarissaNeural",
     "es-MX-LibertoNeural",
     "es-MX-LucianoNeural",
     "es-MX-MarinaNeural",
     "es-MX-NuriaNeural",
     "es-MX-PelayoNeural",
     "es-MX-RenataNeural",
     "es-MX-YagoNeural",
     "es-NI-YolandaNeural",
     "es-NI-FedericoNeural",
     "es-PA-MargaritaNeural",
     "es-PA-RobertoNeural",
     "es-PE-CamilaNeural",
     "es-PE-AlexNeural",
     "es-PR-KarinaNeural",
     "es-PR-VictorNeural",
     "es-PY-TaniaNeural",
     "es-PY-MarioNeural",
     "es-SV-LorenaNeural",
     "es-SV-RodrigoNeural",
     "es-US-PalomaNeural",
     "es-US-AlonsoNeural",
     "es-UY-ValentinaNeural",
     "es-UY-MateoNeural",
     "es-VE-PaolaNeural",
     "es-VE-SebastianNeural"
   ],


   "fr": [
    "No",
     "fr-BE-CharlineNeural",
     "fr-BE-GerardNeural",
     "fr-CA-SylvieNeural",
     "fr-CA-JeanNeural",
     "fr-CA-AntoineNeural",
     "fr-CA-ThierryNeural",
     "fr-CH-ArianeNeural",
     "fr-CH-FabriceNeural",
     "fr-FR-DeniseNeural",
     "fr-FR-HenriNeural",
     "fr-FR-AlainNeural",
     "fr-FR-BrigitteNeural",
     "fr-FR-CelesteNeural",
     "fr-FR-ClaudeNeural",
     "fr-FR-CoralieNeural",
     "fr-FR-EloiseNeural",
     "fr-FR-JacquelineNeural",
     "fr-FR-JeromeNeural",
     "fr-FR-JosephineNeural",
     "fr-FR-MauriceNeural",
     "fr-FR-YvesNeural",
     "fr-FR-YvetteNeural",
     "fr-FR-RemyMultilingualNeural",
     "fr-FR-VivienneMultilingualNeural"
   ],


   "hi": [
    "No",
     "hi-IN-SwaraNeural",
     "hi-IN-MadhurNeural"
   ],
   "hu": [
    "No",
     "hu-HU-NoemiNeural",
     "hu-HU-TamasNeural"
   ],

   "id": [
    "No",
     "id-ID-GadisNeural",
     "id-ID-ArdiNeural"
   ],

   "it": [
    "No",
     "it-IT-ElsaNeural",
     "it-IT-IsabellaNeural",
     "it-IT-DiegoNeural",
     "it-IT-BenignoNeural",
     "it-IT-CalimeroNeural",
     "it-IT-CataldoNeural",
     "it-IT-FabiolaNeural",
     "it-IT-FiammaNeural",
     "it-IT-GianniNeural",
     "it-IT-ImeldaNeural",
     "it-IT-IrmaNeural",
     "it-IT-LisandroNeural",
     "it-IT-PalmiraNeural",
     "it-IT-PierinaNeural",
     "it-IT-RinaldoNeural",
     "it-IT-GiuseppeNeural"
   ],
   "ja": [
    "No",
     "ja-JP-NanamiNeural",
     "ja-JP-KeitaNeural",
     "ja-JP-AoiNeural",
     "ja-JP-DaichiNeural",
     "ja-JP-MayuNeural",
     "ja-JP-NaokiNeural",
     "ja-JP-ShioriNeural",
     "ja-JP-MasaruMultilingualNeural"
   ],

   "kk": [
    "No",
     "kk-KZ-AigulNeural",
     "kk-KZ-DauletNeural"
   ],
   "ko": [
    "No",
     "ko-KR-SunHiNeural",
     "ko-KR-InJoonNeural",
     "ko-KR-BongJinNeural",
     "ko-KR-GookMinNeural",
     "ko-KR-JiMinNeural",
     "ko-KR-SeoHyeonNeural",
     "ko-KR-SoonBokNeural",
     "ko-KR-YuJinNeural",
     "ko-KR-HyunsuNeural"
   ],

   "ms": [
    "No",
     "ms-MY-YasminNeural",
     "ms-MY-OsmanNeural"
   ],
   "nl": [
    "No",
     "nl-BE-DenaNeural",
     "nl-BE-ArnaudNeural",
     "nl-NL-FennaNeural",
     "nl-NL-MaartenNeural",
     "nl-NL-ColetteNeural"
   ],
   "pl": [
    "No",
     "pl-PL-AgnieszkaNeural",
     "pl-PL-MarekNeural",
     "pl-PL-ZofiaNeural"
   ],

   "pt": [
    "No",
     "pt-BR-FranciscaNeural",
     "pt-BR-AntonioNeural",
     "pt-BR-BrendaNeural",
     "pt-BR-DonatoNeural",
     "pt-BR-ElzaNeural",
     "pt-BR-FabioNeural",
     "pt-BR-GiovannaNeural",
     "pt-BR-HumbertoNeural",
     "pt-BR-JulioNeural",
     "pt-BR-LeilaNeural",
     "pt-BR-LeticiaNeural",
     "pt-BR-ManuelaNeural",
     "pt-BR-NicolauNeural",
     "pt-BR-ValerioNeural",
     "pt-BR-YaraNeural",
     "pt-BR-ThalitaNeural",
     "pt-PT-RaquelNeural",
     "pt-PT-DuarteNeural",
     "pt-PT-FernandaNeural"
   ],

   "ru": [
    "No",
     "ru-RU-SvetlanaNeural",
     "ru-RU-DmitryNeural",
     "ru-RU-DariyaNeural"
   ],

   "sv": [
    "No",
     "sv-SE-SofieNeural",
     "sv-SE-MattiasNeural",
     "sv-SE-HilleviNeural"
   ],
   "th": [
    "No",
     "th-TH-PremwadeeNeural",
     "th-TH-NiwatNeural",
     "th-TH-AcharaNeural"
   ],
   "tr": [
    "No",
     "tr-TR-EmelNeural",
     "tr-TR-AhmetNeural"
   ],
   "uk": [
    "No",
     "uk-UA-PolinaNeural",
     "uk-UA-OstapNeural"
   ],
   "vi": [
    "No",
     "vi-VN-HoaiMyNeural",
     "vi-VN-NamMinhNeural"
   ],
   "zh": [
    "No",
     "zh-CN-XiaoxiaoNeural",
     "zh-CN-YunxiNeural",
     "zh-CN-YunjianNeural",
     "zh-CN-XiaoyiNeural",
     "zh-CN-YunyangNeural",
     "zh-CN-XiaochenNeural",
     "zh-CN-XiaohanNeural",
     "zh-CN-XiaomengNeural",
     "zh-CN-XiaomoNeural",
     "zh-CN-XiaoqiuNeural",
     "zh-CN-XiaoruiNeural",
     "zh-CN-XiaoshuangNeural",
     "zh-CN-XiaoyanNeural",
     "zh-CN-XiaoyouNeural",
     "zh-CN-XiaozhenNeural",
     "zh-CN-YunfengNeural",
     "zh-CN-YunhaoNeural",
     "zh-CN-YunxiaNeural",
     "zh-CN-YunyeNeural",
     "zh-CN-YunzeNeural",
     "zh-CN-XiaochenMultilingualNeural",
     "zh-CN-XiaorouNeural",
     "zh-CN-XiaoxiaoDialectsNeural",
     "zh-CN-XiaoxiaoMultilingualNeural",
     "zh-CN-XiaoyuMultilingualNeural",
     "zh-CN-YunjieNeural",
     "zh-CN-YunyiMultilingualNeural",
     "zh-CN-guangxi-YunqiNeural",
     "zh-CN-henan-YundengNeural",
     "zh-CN-liaoning-XiaobeiNeural",
     "zh-CN-liaoning-YunbiaoNeural",
     "zh-CN-shaanxi-XiaoniNeural",
     "zh-CN-shandong-YunxiangNeural",
     "zh-CN-sichuan-YunxiNeural",
     "zh-HK-HiuMaanNeural",
     "zh-HK-WanLungNeural",
     "zh-HK-HiuGaaiNeural",
     "zh-TW-HsiaoChenNeural",
     "zh-TW-YunJheNeural",
     "zh-TW-HsiaoYuNeural"
   ]
}
```