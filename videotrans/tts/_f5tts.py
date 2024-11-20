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
        if not self.api_url.endswith('/api'):
            self.api_url+='/api'
        self.proxies={"http": "", "https": ""}
    

    
    def _exec(self):
        self._local_mul_thread()

    def convert_numbers_in_text(self,text):
        """
        将文本中的数字0-9转换为中文或英文，原地修改文本。

        Args:
            text: 输入文本字符串。
        """

        def replace_with_chinese(match):
            num = int(match.group(0))
            chinese_nums = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']
            return chinese_nums[num]

        def replace_with_english(match):
            num = int(match.group(0))
            english_nums = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
            return english_nums[num]

        # 使用正则表达式查找所有数字
        if self.language.startswith('zh'):
            return re.sub(r'[0-9]', replace_with_chinese, text) #修改为中文
        return re.sub(r'\b[0-9]\b', replace_with_english, text) #修改为英文


    def _item_task(self, data_item: Union[Dict, List, None]):
        if self._exit():
            return
        if not data_item:
            return
        speed=1.0
        try:
            speed=1+float(self.rate.replace('%',''))/100
        except:
            pass
        try:
            text = self.convert_numbers_in_text(data_item['text'].strip())
            role = data_item['role']
            if not text:
                return
            data = {"model":config.params['f5tts_model'],'speed':speed}
            data['gen_text']=text
            
            if role=='clone':
                if not Path(data_item['ref_wav']).exists():
                    self.error = f'不存在参考音频，无法使用clone功能' if config.defaulelang=='zh' else 'No reference audio exists and cannot use clone function'
                    return
                audio_chunk=AudioSegment.from_wav(data_item['ref_wav'])
                if len(audio_chunk)<4000:
                    audio_chunk=audio_chunk*2
                    audio_chunk.export(data_item['ref_wav'],format='wav')

                with open(data_item['ref_wav'],'rb') as f:
                    chunk=f.read()
                files={"audio":chunk}
                data['ref_text']=data_item.get('ref_text').strip()
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
            if response.status_code != 200:
                self.error = f'{response.text}, status_code={response.status_code} {response.reason} '
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
        except Exception as e:
            self.error = str(e)
            config.logger.exception(e, exc_info=True)
        finally:
            if self.error:
                self._signal(text=self.error)
            else:
                self._signal(text=f'{config.transobj["kaishipeiyin"]} {self.has_done}/{self.len}')
        return
