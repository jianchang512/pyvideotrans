import uuid

import requests

API_URL = "https://southeastasia.api.speech.microsoft.com/accfreetrial/texttospeech/acc/v3.0-beta1/vcg/speak";
DEFAULT_HEADERS = {
    "authority": "southeastasia.api.speech.microsoft.com",
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9",
    "customvoiceconnectionid": str(uuid.uuid4()),
    "origin": "https://speech.microsoft.com",
    "sec-ch-ua":
        '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
    "content-type": "application/json",
}
sml="""
 <speak xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" xmlns:emo="http://www.w3.org/2009/10/emotionml" version="1.0" xml:lang="en-US">
    <voice name="zh-CN-XiaochenNeural">
    <mstts:express-as style="">
        <prosody rate="+0%" pitch="0%">
        我是中国人
       </prosody>
        </mstts:express-as>
    </voice>
    </speak>
"""
jsondata={
        "ssml":sml,
        "ttsAudioFormat": "audio-24khz-160kbitrate-mono-mp3",
        "offsetInPlainText": 0,
        "properties": {
            "SpeakTriggerSource": "AccTuningPagePlayButton",
        },
    }
res=requests.post(API_URL,headers=DEFAULT_HEADERS,json=jsondata)
print(res.text)
with open('./1.mp3','wb') as f:
    f.write(res.content)
