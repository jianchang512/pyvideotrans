# API接口文档

默认接口地址地址 http://127.0.0.1:9011

> 可通过在api.py(api.exe)同级目录下创建 `host.txt`, 修改ip和端口，例如 `host.txt` 内容如下
>
> `127.0.0.1:9801`
>
> 则接口地址将变为 http://127.0.0.1:9801

## 启动方法

> 升级到v2.57+

1. 预打包版双击 `api.exe`,等待终端窗口显示 `API URL http://127.0.0.1:9011`
2. 源码版执行 `python api.py`

## 翻译/配音/识别渠道配置

某些渠道，例如翻译渠道：OpenAI ChatGPT/AzureGPT/Baidu/Tencent/DeepL等需要配置api url 和 key 等，如果要使用，请使用GUI界面在设置中配置相关信息

除了 翻译渠道Google/FreeGoole/Microsoft，配音渠道edge-tts，识别模式faster-whisper/openai-whisper外，其他渠道均需要单独配置。请打开GUI界面在菜单栏-设置中进行配置。

## 接口列表

### `/tts` - 根据字幕合成配音接口

#### 请求数据类型
`Content-Type: application/json`

#### 请求参数

| 参数名          | 数据类型 | 是否必选 | 默认值 | 可选值 | 描述 |
| --------------- | -------- | -------- | ------ | ------ | ---- |
| name            | 字符串   | 是       | 无     | 无     | 需要配音的srt字幕的绝对路径或合法的srt字幕格式内容 |
| tts_type        | 数字     | 是       | 无     | 0-11   | 配音渠道，具体值对应渠道名称见下 |
| voice_role      | 字符串   | 是       | 无     | - | 对应配音渠道的角色名.edge-tts/azure-tts/302.ai(azure模型)角色名根据所选目标语言不同而变化，具体见底部 |
| target_language | 字符串   | 是       | 无     | 需要配音的语言类型代码 | 简体中文zh-cn，繁体zh-tw，英语en，法语fr，德语de，日语ja，韩语ko，俄语ru，西班牙语es，泰国语th，意大利语it，葡萄牙语pt，越南语vi，阿拉伯语ar，土耳其语tr，印地语hi，匈牙利语hu，乌克兰语uk，印尼语id，马来语ms，哈萨克语kk，捷克语cs，波兰语pl，荷兰语nl，瑞典语sv |
| voice_rate      | 字符串   | 否       | 无     | 加速`+数字%`，减速`-数字%` | 语速加减值 |
| volume          | 字符串   | 否       | 无     | 增大音量`+数字%`，降低音量`-数字%` | 音量变化值（仅配音渠道为edge-tts生效） |
| pitch           | 字符串   | 否       | 无     | 调大音调`+数字Hz`,降低音量`-数字Hz` | 音调变化值（仅配音渠道为edge-tts生效） |
| out_ext         | 字符串   | 否       | wav    | mp3\|wav\|flac\|aac | 输出配音文件类型 |
| voice_autorate  | 布尔值   | 否       | False  | True\|False | 是否自动加快语速 |

**tts_type 0-11分别代表**

- 0=Edge-TTS
- 1=CosyVoice
- 2=ChatTTS
- 3=302.AI
- 4=FishTTS
- 5=Azure-TTS"
- 6=GPT-SoVITS
- 7=clone-voice
- 8=OpenAI TTS
- 9=Elevenlabs.io
- 10=Google TTS
- 11=自定义TTS API

#### 返回数据类型
JSON格式

#### 返回示例
成功时：
```json
{
    "code": 0,
    "msg": "ok",
    "task_id": "任务id"
}
```

失败时：
```json
{
    "code": 1,
    "msg": "错误信息"
}
```

#### 请求示例
```python
import requests
res=requests.post("http://127.0.0.1:9011/tts", json={
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
print(res.json())
```

----

### `/translate_srt` - 字幕翻译接口

#### 请求数据类型
`Content-Type: application/json`

#### 请求参数

| 参数名            | 数据类型 | 是否必选 | 默认值 | 可选值 | 描述 |
| ----------------- | -------- | -------- | ------ | ------ | ---- |
| name              | 字符串   | 是       | 无     | 无     | 需要翻译的srt字幕的绝对路径或合法的srt字幕格式内容 |
| translate_type    | 整数     | 是       | 无     | 0-14  | 0-14分别代表翻译渠道，详细见下 |
| target_language   | 字符串   | 是       | 无     | - | 简体中文zh-cn，繁体zh-tw，英语en，法语fr，德语de，日语ja，韩语ko，俄语ru，西班牙语es，泰国语th，意大利语it，葡萄牙语pt，越南语vi，阿拉伯语ar，土耳其语tr，印地语hi，匈牙利语hu，乌克兰语uk，印尼语id，马来语ms，哈萨克语kk，捷克语cs，波兰语pl，荷兰语nl，瑞典语sv |
| source_code       | 字符串   | 否       | 无     | - | 简体中文zh-cn，繁体zh-tw，英语en，法语fr，德语de，日语ja，韩语ko，俄语ru，西班牙语es，泰国语th，意大利语it，葡萄牙语pt，越南语vi，阿拉伯语ar，土耳其语tr，印地语hi，匈牙利语hu，乌克兰语uk，印尼语id，马来语ms，哈萨克语kk，捷克语cs，波兰语pl，荷兰语nl，瑞典语sv |

**translate_type 翻译渠道 0-14**

- 0=Google翻译
- 1=微软翻译
- 2=302.AI
- 3=百度翻译
- 4=DeepL
- 5=DeepLx
- 6=离线翻译OTT
- 7=腾讯翻译
- 8=OpenAI ChatGPT
- 9=本地大模型及兼容AI
- 10=字节火山引擎
- 11=AzureAI GPT
- 12=Gemini
- 13=自定义翻译API
- 14=FreeGoogle翻译

#### 返回数据类型
JSON格式

#### 返回示例
成功时：
```json
{
    "code": 0,
    "msg": "ok",
    "task_id": "任务id"
}
```

失败时：
```json
{
    "code": 1,
    "msg": "错误信息"
}
```

#### 请求示例
```python
import requests
res=requests.post("http://127.0.0.1:9011/translate_srt", json={
    "name": "C:/users/c1/videos/zh0.srt",
    "target_language": "en",
    "translate_type": 0
})
print(res.json())
```

----

### `/recogn` - 语音识别、音视频转字幕接口

#### 请求数据类型
`Content-Type: application/json`

#### 请求参数

| 参数名            | 数据类型 | 是否必选 | 默认值 | 可选值 | 描述 |
| ----------------- | -------- | -------- | ------ | ------ | ---- |
| name              | 字符串   | 是       | 无     | 无     | 需要翻译的音频或视频的绝对路径 |
| recogn_type       | 数字     | 是       | 无     | 0-6    | 语音识别模式,0=faster-whisper本地模型识别，1=openai-whisper本地模型识别，2=Google识别api，3=zh_recogn中文识别，4=豆包模型识别，5=自定义识别API，6=OpenAI识别API |
| model_name        | 字符串   | 是       | 无     | -  | 当选择faster-whisper/openai-whisper模式时必须填写模型名字 |
| detect_language   | 字符串   | 是       | 无     | - | 中文zh，英语en，法语fr，德语de，日语ja，韩语ko，俄语ru，西班牙语es，泰国语th，意大利语it，葡萄牙语pt，越南语vi，阿拉伯语ar，土耳其语tr，印地语hi，匈牙利语hu，乌克兰语uk，印尼语id，马来语ms，哈萨克语kk，捷克语cs，波兰语pl，荷兰语nl，瑞典语sv |
| split_type        | 字符串   | 否       | all    | all\|avg | 分割类型，all=整体识别，avg=均等分割 |
| is_cuda           | 布尔值   | 否       | False  | True\|False | 是否启用CUDA加速 |

#### 返回数据类型
JSON格式

#### 返回示例
成功时：
```json
{
    "code": 0,
    "msg": "ok",
    "task_id": "任务id"
}
```

失败时：
```json
{
    "code": 1,
    "msg": "错误信息"
}
```

#### 请求示例
```python
import requests
res=requests.post("http://127.0.0.1:9011/recogn", json={
    "name": "C:/Users/c1/Videos/10ass.mp4",
    "recogn_type": 0,
    "split_type": "overall",
    "model_name": "tiny",
    "is_cuda": False,
    "detect_language": "zh",
})
print(res.json())
```

----

### `/trans_video` - 视频完整翻译接口

#### 请求数据类型
`Content-Type: application/json`

#### 请求参数

| 参数名            | 数据类型 | 是否必选 | 默认值 | 可选值 | 描述 |
| ----------------- | -------- | -------- | ------ | ------ | ---- |
| name              | 字符串   | 是       | 无     | 无     | 需要翻译的音频或视频的绝对路径 |
| recogn_type       | 数字     | 是       | 无     | 0-6    | 语音识别模式,0=faster-whisper本地模型识别，1=openai-whisper本地模型识别，2=Google识别api，3=zh_recogn中文识别，4=豆包模型识别，5=自定义识别API，6=OpenAI识别API |
| model_name        | 字符串   | 是       | 无     | - | 当选择faster-whisper/openai-whisper模式时必须填写模型名字 |
| translate_type    | 整数     | 是       | 无     | 0-14 | 翻译渠道见下 |
| target_language   | 字符串   | 是       | 无     | - | 翻译到的目标语言，简中zh-cn，繁中zh-tw，英语en，法语fr，德语de，日语ja，韩语ko，俄语ru，西班牙语es，泰国语th，意大利语it，葡萄牙语pt，越南语vi，阿拉伯语ar，土耳其语tr，印地语hi，匈牙利语hu，乌克兰语uk，印尼语id，马来语ms，哈萨克语kk，捷克语cs，波兰语pl，荷兰语nl，瑞典语sv |
| source_language   | 字符串   | 是       | 无     | - | 音频中人类发声语言，简中zh-cn，繁中zh-tw，英语en，法语fr，德语de，日语ja，韩语ko，俄语ru，西班牙语es，泰国语th，意大利语it，葡萄牙语pt，越南语vi，阿拉伯语ar，土耳其语tr，印地语hi，匈牙利语hu，乌克兰语uk，印尼语id，马来语ms，哈萨克语kk，捷克语cs，波兰语pl，荷兰语nl，瑞典语sv |
| tts_type          | 数字     | 是       | 无     | 0-11   | 配音渠道见下 |
| voice_role        | 字符串   | 是       | 无     | - | 对应配音渠道的角色名.edge-tts/azure-tts/302.ai(azure模型)角色名根据所选目标语言不同而变化，具体见底部 |
| voice_rate        | 字符串   | 否       | 无     | 加速`+数字%`，减速`-数字%` | 语速加减值 |
| volume            | 字符串   | 否       | 无     | 增大音量`+数字%`，降低音量`-数字%` | 音量变化值（仅配音渠道为edge-tts生效） |
| pitch             | 字符串   | 否       | 无     | 调大音调`+数字Hz`,降低音量`-数字Hz` | 音调变化值（仅配音渠道为edge-tts生效） |
| out_ext           | 字符串   | 否       | wav    | mp3\|wav\|flac\|aac | 输出配音文件类型 |
| voice_autorate    | 布尔值   | 否       | False  | True\|False | 是否自动加快语速 |
| subtitle_type     | 整数     | 否       | 0      | 0-4    | 字幕嵌入类型 字幕嵌入类型，0=不嵌入字幕，1=嵌入硬字幕，2=嵌入软字幕，3=嵌入双硬字幕，4=嵌入双软字幕 |
| append_video      | 布尔值   | 否       | False  | True\|False | 是否延长视频末尾 |
| only_video        | 布尔值   | 否       | False  | True\|False | 是否只生成视频文件 |

**translate_type 翻译渠道 0-14**

- 0=Google翻译
- 1=微软翻译
- 2=302.AI
- 3=百度翻译
- 4=DeepL
- 5=DeepLx
- 6=离线翻译OTT
- 7=腾讯翻译
- 8=OpenAI ChatGPT
- 9=本地大模型及兼容AI
- 10=字节火山引擎
- 11=AzureAI GPT
- 12=Gemini
- 13=自定义翻译API
- 14=FreeGoogle翻译

**tts_type配音渠道 0-11分别代表**

- 0=Edge-TTS
- 1=CosyVoice
- 2=ChatTTS
- 3=302.AI
- 4=FishTTS
- 5=Azure-TTS"
- 6=GPT-SoVITS
- 7=clone-voice
- 8=OpenAI TTS
- 9=Elevenlabs.io
- 10=Google TTS
- 11=自定义TTS API

#### 返回数据类型
JSON格式

#### 返回示例
成功时：
```json
{
    "code": 0,
    "msg": "ok",
    "task_id": "任务id"
}
```

失败时：
```json
{
    "code": 1,
    "msg": "错误信息"
}
```

#### 请求示例
```python
import requests
res=requests.post("http://127.0.0.1:9011/trans_video", json={
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
print(res.json())
```

----

### `/task_status` - 获取任务进度接口

#### 请求数据类型
`GET` 或 `POST`

#### 请求参数

| 参数名          | 数据类型 | 是否必选 | 描述 |
| --------------- | -------- | -------- | ---- |
| task_id         | 字符串   | 是       | 任务id |

#### 返回数据类型
JSON格式

#### 返回示例
进行中时：
```json
{
    "code": -1,
    "msg": "正在合成声音"
}
```

成功时：
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

失败时：
```json
{
    "code": 1,
    "msg": "不存在该任务"
}
```

#### 请求示例
```python
import requests
res=requests.get("http://127.0.0.1:9011/task_status?task_id=06c238d250f0b51248563c405f1d7294")
print(res.json())
```

---

## 翻译渠道数字对应 translate_type   0-14

- 0=Google翻译
- 1=微软翻译
- 2=302.AI
- 3=百度翻译
- 4=DeepL
- 5=DeepLx
- 6=离线翻译OTT
- 7=腾讯翻译
- 8=OpenAI ChatGPT
- 9=本地大模型及兼容AI
- 10=字节火山引擎
- 11=AzureAI GPT
- 12=Gemini
- 13=自定义翻译API
- 14=FreeGoogle翻译

## 配音渠道（tts_type） 0-11 对应名称
- 0=Edge-TTS
- 1=CosyVoice
- 2=ChatTTS
- 3=302.AI
- 4=FishTTS
- 5=Azure-TTS"
- 6=GPT-SoVITS
- 7=clone-voice
- 8=OpenAI TTS
- 9=Elevenlabs.io
- 10=Google TTS
- 11=自定义TTS API


## edge-tts 语言代码和角色名映射

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
  zh": [
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
    "zh-CN-liaoning-XiaobeiNeural",
    "zh-TW-HsiaoChenNeural",
    "zh-TW-YunJheNeural",
    "zh-TW-HsiaoYuNeural",
    "zh-CN-shaanxi-XiaoniNeural"
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

## Azure-tts 及 302.ai选择azure模型时语言代码和角色名映射
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