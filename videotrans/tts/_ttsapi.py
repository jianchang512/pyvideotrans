import logging
import sys,re
from dataclasses import dataclass
from typing import List, Dict
from typing import Union
import requests

from videotrans.configure.excepts import StopTask, NO_RETRY_EXCEPT
from videotrans.configure.config import tr, params, logger, settings,ROOT_DIR
from videotrans.tts._base import BaseTTS
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
from pathlib import Path
from videotrans.util.help_misc import vail_file

from videotrans.util.help_role import get_f5tts_role
from gradio_client import Client
from gradio_client import handle_file

import concurrent.futures
import threading
import urllib3
import httpx
thread_local = threading.local()


@dataclass
class TTSAPI(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.speed=self.get_speed()

        api_url = params.get('ttsapi_url','').strip().rstrip('/').lower()
        if len(api_url)<4:
            raise StopTask(f'API URL is error: {api_url}')
        if not api_url.startswith('http'):
            self.api_url = 'http://' + api_url
        else:
            self.api_url = api_url
        self.roledict = get_f5tts_role()

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        if not data_item.get('text') or vail_file(data_item['filename']):return
        if data_item.get('role')=='':
            data_item['role']=list(self.roledict.keys())[-1]
        if data_item.get('role') in self.roledict:
            ref_wav,ref_text = self.get_ref_wav(data_item)
        else:
            ref_wav,ref_text=None,None
        # 如果是 gradio api请求
        _gradio_api=f'{ROOT_DIR}/gradio_api.txt'
        if Path(_gradio_api).exists() and Path(_gradio_api).stat().st_size>0:
            _args=Path(_gradio_api).read_text(encoding='utf-8').strip().split("\n")            
            return self._send(_args,data_item,ref_wav,ref_text)
        
        
        data = {"text": data_item.get('text','').strip(),
                "language": self.language.split('-')[0] if self.language else "",
                "extra": params.get('ttsapi_extra',''),
                "voice": data_item['role'].strip(),
                "ostype": sys.platform,
                "rate": self.speed}
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        }
        logger.debug(f'自定义TTS API发送数据 {data=}')
        if ref_wav:
            with open(ref_wav, 'rb') as f:
                files = {'file': f}
                resraw = requests.post(f"{self.api_url}", data=data,  verify=False, headers=headers,files=files)
        else:
            resraw = requests.post(f"{self.api_url}", data=data, verify=False, headers=headers)
        if resraw.status_code in [401,403,404,405,415,422]:
            raise StopTask(resraw.text)
        resraw.raise_for_status()
        res=resraw.json()
        logger.debug(f'返回数据 {res["code"]=}')
        if "code" not in res or "msg" not in res or res['code'] != 0:
            return f'TTS-API:{res["msg"]}'

        if 'data' not in res or not res['data']:
            return  tr("No valid audio address returned")
        # 返回的是音频url地址
        tmp_filename = data_item['filename'] + ".mp3"
        if isinstance(res['data'], str) and res['data'].startswith('http'):
            url = res['data']
            res = requests.get(url)
            res.raise_for_status()
            with open(tmp_filename, 'wb') as f:
                f.write(res.content)
        elif isinstance(res['data'], str) and res['data'].startswith('data:audio'):
            # 返回 base64数据
            self._base64_to_audio(res['data'], tmp_filename)
        elif isinstance(res['data'], dict) and 'audio' in res['data']:
            with open(tmp_filename, 'wb') as f:
                f.write(bytes.fromhex(res['data']['audio']))
        else:
            return tr("No valid audio address or base64 audio data returned")
        self.convert_to_wav(tmp_filename, data_item['filename'])


    def get_thread_client(self)->Client:
        # 检查当前线程是否已经有存活的 client
        if not hasattr(thread_local, "client") or thread_local.client is None:
            logger.debug(f"正在为线程 {threading.current_thread().name} 初始化 Gradio Client: {self.api_url}")
            thread_local.client = Client(
                    self.api_url,
                    httpx_kwargs={"timeout": 3600}, # 连接超时设置短一点因为只是拉取配置
                    ssl_verify=False
                )
        return thread_local.client


    def _send(self, _args,data_item,ref_wav=None,ref_text=None)->Union[str,None]:
        if self._exit() or not data_item.get('text','').strip() or vail_file(data_item['filename']):
            return
        kwargs={}
        for it in _args:
            _kv=it.strip().split('=')
            _value=str(_kv[1]).strip().lower().strip(',') if len(_kv)>1 else ""
            if len(_kv)!=2 or _value=='none':
                continue
            if _value=='tts_text':
                kwargs[_kv[0]]=data_item['text'].strip()
            elif _value=='tts_audio':
                if ref_wav:
                    kwargs[_kv[0]]=handle_file(ref_wav)
            elif _value=='tts_audio_text':
                if ref_text:
                    kwargs[_kv[0]]=ref_text
            elif _value == 'true':
                kwargs[_kv[0]]=True
            elif _value=='false':
                kwargs[_kv[0]]=False
            elif re.match(r'^\d+$',_value):
                kwargs[_kv[0]]=int(_value)
            elif re.match(r'^\d*?\.\d+$',_value):
                kwargs[_kv[0]]=float(_value)
            else:
                kwargs[_kv[0]]=_kv[1]
                    
        logger.debug(f'[自定义TTS API|gradio api]:{self.api_url=},{kwargs=}')
        try:
            client = self.get_thread_client()
            result = client.predict(**kwargs)
            logger.debug(f'result={result}')
            wav_file = result[0] if isinstance(result, (list, tuple)) and result else result
            if isinstance(wav_file, dict) and "value" in wav_file:
                wav_file = wav_file['value']
            
            if not isinstance(wav_file, str) or not Path(wav_file).is_file():
                return str(result)+f"\n{self.api_url=}"
            self.convert_to_wav(wav_file, data_item['filename'])
        except (TypeError,ValueError,IndexError,AttributeError,urllib3.exceptions.NewConnectionError,httpx.ConnectError) as e:
            raise StopTask(e) from e
        except concurrent.futures.CancelledError as e:
            logger.exception(f'配音失败:{self.ainame}',exc_info=True)
            # 清理当前线程的客户端缓存，防止下次复用一个已损坏的连接
            if hasattr(thread_local, "client"):
                del thread_local.client
            return str(e)+f"\n{self.api_url=}"
        except Exception as e:
            return +f"{self.api_url} \n{str(e)}"
        return
