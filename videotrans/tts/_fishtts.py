import os
import time
from dataclasses import dataclass
from typing import List, Dict, Union
import requests
from videotrans.configure.config import params, logger
from videotrans.configure.excepts import StopTask
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

@dataclass
class FishTTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        self.api_url = 'http://' +params.get('fishtts_url', '').strip().rstrip('/').lower().replace('http://', '')
        if len(self.api_url)<10:
            raise StopTask(f'API URL is error: {self.api_url}')
        self.roledict = tools.get_f5tts_role()

    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        ref_wav, ref_text = self.get_ref_wav(data_item)
        data = {
            "text": data_item['text'],
            "references": [{
                "audio": "",
                "text": ref_text
            }]
        }

        # 克隆声音
        data['references'][0]['audio'] = self._audio_to_base64(ref_wav)

        logger.debug(f'fishTTS-post:{data=}')
        response = requests.post(f"{self.api_url}", json=data, timeout=3600)
        response.raise_for_status()

        # 如果是WAV音频流，获取原始音频数据
        with open(data_item['filename'] + ".wav", 'wb') as f:
            f.write(response.content)
        time.sleep(1)
        if not os.path.exists(data_item['filename'] + ".wav"):
            return f'FishTTS dubbing error -2'
        self.convert_to_wav(data_item['filename'] + ".wav", data_item['filename'])
