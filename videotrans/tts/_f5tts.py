import copy
import json
import os,re
import time
from pathlib import Path
from typing import Union, Dict, List

import requests
from pydub import AudioSegment

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools


# 线程池并发  返回wav数据转为mp3
class F5TTS(BaseTTS):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.copydata = copy.deepcopy(self.queue_tts)
        api_url = config.params['f5tts_url'].strip().rstrip('/').lower()
        self.api_url = 'http://' + api_url.replace('http://', '')
        self.v1_local=True
        
        if self.api_url.find(':5010')>0:
            self._version='v0'
            if not self.api_url.endswith('/api'):
                self.api_url+='/api'
        else:
            self._version='v1'
            sepflag=self.api_url.find('/',9)
            if sepflag>-1:
                self.api_url=self.api_url[:sepflag]
            if not re.search(r'127.0.0.1|localhost',self.api_url):
                self.v1_local=False
        self.proxies={"http": "", "https": ""}
    

    
    def _exec(self):
        self._local_mul_thread()
    
    def _item_task_v1(self, data_item: Union[Dict, List, None]):
        from gradio_client import Client, handle_file
        speed=1.0
        try:
            speed=1+float(self.rate.replace('%',''))/100
        except:
            pass
        try:
            text = data_item['text'].strip()
            role = data_item['role']
            data = {'speed':speed,'ref_text':'','ref_wav':''}
            data['gen_text']=text
            if role=='clone':
                data['ref_wav']=data_item['ref_wav']
                if not config.params.get('f5tts_is_whisper'):
                    data['ref_text']=data_item.get('ref_text').strip()
            else:
                roledict = tools.get_f5tts_role()
                if role in roledict:
                    data['ref_text']=roledict[role]['ref_text'] if not config.params.get('f5tts_is_whisper') else ''
                    data['ref_wav']=config.ROOT_DIR+f"/f5-tts/{role}"
            
            if not Path(data['ref_wav']).exists():
                self.error = f'{role} 角色不存在'
                return
            client = Client(self.api_url,httpx_kwargs={"timeout":7200},
                    ssl_verify=False)
            result = client.predict(
                    ref_audio_input=handle_file(data['ref_wav']),
                    ref_text_input=data['ref_text'],
                    gen_text_input=text,
                    remove_silence=True,
                    
                    #cross_fade_duration_slider=0.15,
                    #nfe_slider=32,
                    speed_slider=speed,
                    api_name="/basic_tts"
            )
            print(result)
            config.logger.info(f'result={result}')
            if self.v1_local:
                tools.wav2mp3(result[0], data_item['filename'])
            else:
                resp=requests.get(self.api_url+f'/gradio_api/file='+Path(result[0]).as_posix())
                resp.raise_for_status()
                with open(data_item['filename'] + ".wav", 'wb') as f:
                    f.write(resp.content)
                time.sleep(1)
                if not os.path.exists(data_item['filename'] + ".wav"):
                    self.error = f'F5-TTS合成声音失败-2:{text=}'
                    return
                tools.wav2mp3(data_item['filename'] + ".wav", data_item['filename'])
            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error = ''
            self.has_done += 1
        except Exception as e:
            self.error = str(e)
            config.logger.exception(e, exc_info=True)
        finally:
            if self.error:
                self._signal(text=self.error)
            else:
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')            

    def _item_task(self, data_item: Union[Dict, List, None]):
        if self._exit():
            return
        if not data_item:
            return
        text = data_item['text'].strip()
        if not text:
            return
        if self._version == 'v1':
            return self._item_task_v1(data_item)
        speed=1.0
        try:
            speed=1+float(self.rate.replace('%',''))/100
        except:
            pass
        try:
            
            role = data_item['role']
            data = {"model":'f5-tts','speed':speed}
            data['gen_text']=text
            if role=='clone':
                if not Path(data_item['ref_wav']).exists():
                    self.error = f'不存在参考音频，无法使用clone功能' if config.defaulelang=='zh' else 'No reference audio exists and cannot use clone function'
                    return
                audio_chunk=AudioSegment.from_wav(data_item['ref_wav'])
                data['ref_text']=data_item.get('ref_text').strip()


                with open(data_item['ref_wav'],'rb') as f:
                    chunk=f.read()
                files={"audio":chunk}
                if not data['ref_text']:
                    Path(data_item['filename']).unlink(missing_ok=True)
                    return
            else:
                roledict = tools.get_f5tts_role()
                if role in roledict:
                    data['ref_text']=roledict[role]['ref_text']
                    with open(config.ROOT_DIR+f"/f5-tts/{role}",'rb') as f:
                        chunk=f.read()
                    files={"audio":chunk}
                else:
                    self.error = f'{role} 角色不存在'
                    return
            config.logger.info(f'f5TTS-post:{data=},{self.proxies=}')
            response = requests.post(f"{self.api_url}",files=files,data=data, proxies=self.proxies, timeout=3600)
            response.raise_for_status()
            if not response.content:
                self.error = f'{response.json()["error"]}, status_code={response.status_code} {response.reason} '
                Path(data_item['filename']).unlink(missing_ok=True)
                return

            # 如果是WAV音频流，获取原始音频数据
            with open(data_item['filename'] + ".wav", 'wb') as f:
                f.write(response.content)
            time.sleep(1)
            if not os.path.exists(data_item['filename'] + ".wav"):
                self.error = f'F5-TTS合成声音失败-2:{text=}'
                return
            tools.wav2mp3(data_item['filename'] + ".wav", data_item['filename'])
            Path(data_item['filename'] + ".wav").unlink(missing_ok=True)

            if self.inst and self.inst.precent < 80:
                self.inst.precent += 0.1
            self.error = ''
            self.has_done += 1
        except (requests.ConnectionError, requests.Timeout) as e:
            self.error="连接失败，请检查是否启动了api服务" if config.defaulelang=='zh' else  'Connection failed, please check if the api service is started'
        except Exception as e:
            self.error = str(e)
            config.logger.exception(e, exc_info=True)
        finally:
            if self.error:
                self._signal(text=self.error)
            else:
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
        return
