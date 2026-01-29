import logging
import time
from dataclasses import dataclass, field
from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT,StopRetry
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

from tenacity import retry, wait_exponential, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log,  RetryError
import base64
import hashlib
import hmac
import html
import json
import uuid
from datetime import datetime
from urllib.parse import quote
import requests


ENDPOINT_URL = "https://dev.microsofttranslator.com/apps/endpoint?api-version=1.0"
VOICES_LIST_URL = "https://eastus.api.speech.microsoft.com/cognitiveservices/voices/list"
USER_AGENT = "okhttp/4.5.0"
CLIENT_VERSION = "4.0.530a 5fe1dc6c"
USER_ID = "0f04d16a175c411e"
HOME_GEOGRAPHIC_REGION = "zh-Hans-CN"
CLIENT_TRACE_ID = "aab069b9-70a7-4844-a734-96cd78d94be9"
VOICE_DECODE_KEY = "oik6PdDdMnOXemTbwvMn9de/h9lFnfBaCWbGMMZqqoSaQaqUOqjVGm5NqsmjcBI1x+sS9ugjB55HEJWRiFXYFw=="


DEFAULT_OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3"
DEFAULT_STYLE = "general"

endpoint = None
expired_at = None

RETRY_NUMS = 2
RETRY_DELAY = 5


@dataclass
class FreeAzureTTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()


    def get_endpoint(self):
        signature = self.sign(ENDPOINT_URL)
        headers = {
            "Accept-Language": "zh-Hans",
            "X-ClientVersion": CLIENT_VERSION,
            "X-UserId": USER_ID,
            "X-HomeGeographicRegion": HOME_GEOGRAPHIC_REGION,
            "X-ClientTraceId": CLIENT_TRACE_ID,
            "X-MT-Signature": signature,
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": "0",
            "Accept-Encoding": "gzip",
        }

        response = requests.post(ENDPOINT_URL, headers=headers,proxies=None)
        response.raise_for_status()
        return response.json()


    def sign(self,url_str):
        u = url_str.split("://")[1]
        encoded_url = quote(u, safe='')
        uuid_str = str(uuid.uuid4()).replace("-", "")
        formatted_date = datetime.utcnow().strftime(
            "%a, %d %b %Y %H:%M:%S").lower() + "gmt"
        bytes_to_sign = f"MSTranslatorAndroidApp{encoded_url}{formatted_date}{uuid_str}".lower().encode('utf-8')

        decode = base64.b64decode(VOICE_DECODE_KEY)
        hmac_sha256 = hmac.new(decode, bytes_to_sign, hashlib.sha256)
        secret_key = hmac_sha256.digest()
        sign_base64 = base64.b64encode(secret_key).decode()

        return f"MSTranslatorAndroidApp::{sign_base64}::{formatted_date}::{uuid_str}"


    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(RETRY_NUMS)),
               wait=wait_fixed(RETRY_DELAY), before=before_log(config.logger, logging.INFO),
               after=after_log(config.logger, logging.INFO))
    def get_voice(self,data_item):
        global endpoint, expired_at, client_id

        current_time = int(time.time())
        if not expired_at or current_time > expired_at - 60:
            endpoint = self.get_endpoint()
            jwt = endpoint['t'].split('.')[1]
            decoded_jwt = json.loads(base64.b64decode(jwt + '==').decode('utf-8'))
            expired_at = decoded_jwt['exp']
            seconds_left = expired_at - current_time
            client_id = str(uuid.uuid4())
        else:
            seconds_left = expired_at - current_time

        voice_name = tools.get_azure_rolelist(self.language.split('-')[0],data_item['role'])
        rate = self.rate
        pitch = self.pitch
        output_format = DEFAULT_OUTPUT_FORMAT
        style = DEFAULT_STYLE

        endpoint = self.get_endpoint()

        url = f"https://{endpoint['r']}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Authorization": endpoint["t"],
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": output_format,
        }

        ssml = self.get_ssml(data_item.get('text'), voice_name, rate, pitch, style,self.volume)
        print(f'{url=}')

        response = requests.post(url, headers=headers, data=ssml.encode(),proxies=None)
        response.raise_for_status()
        filename = data_item['filename'] + f"-generate.wav"
        with open(filename,'wb') as f:
            f.write(response.content)
        if tools.vail_file(filename):
            self.convert_to_wav(filename, data_item['filename'])
        return True


    def get_ssml(self,text, voice_name, rate, pitch, style,volume):
        return f"""
    <speak xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" version="1.0" xml:lang="zh-CN">
    <voice name="{voice_name}">
        <mstts:express-as style="{style}" styledegree="1.0" role="default">
            <prosody rate="{rate}" pitch="{pitch}" volume="{volume}">
                {text}
            </prosody>
        </mstts:express-as>
    </voice>
    </speak>
        """


    def _item_task(self, data_item):
        if self._exit() or  not data_item.get('text','').strip():
            return
        
        try:
            self.get_voice(data_item)
        except RetryError as e:
            err=str(e.last_attempt.exception())
            if "Unsupported voice" in err:
                raise StopRetry(config.tr("The sound cannot be tried."))
                
            raise
        
        

    def _exec(self) -> None:
        self._local_mul_thread()
        


