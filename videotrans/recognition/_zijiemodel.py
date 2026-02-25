# zh_recogn 识别
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union

import requests

from videotrans.configure import config
from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

_error={
"20000003":"静音音频",



"45000001":"请求参数缺失必需字段 / 字段值无效",
"45000002":"空音频",
"45000151":"音频格式不正确",

"550XXXX":"服务内部处理错误",
"55000031":"服务器繁忙"
}

@dataclass
class ZijieRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():  return

        submit_url = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
        task_id = str(uuid.uuid4())
        appid=params.get('zijierecognmodel_appid','')
        headers = {
            "X-Api-App-Key": appid,
            "X-Api-Access-Key": params.get('zijierecognmodel_token',''),
            "X-Api-Resource-Id": "volc.bigasr.auc_turbo",
            "X-Api-Request-Id": task_id,
            "X-Api-Sequence": "-1"
        }
        request = {
            "user": {
                "uid": appid
            },
            "audio": {"data": self._audio_to_base64(self.audio_file)},
            "request": {
                "model_name": "bigmodel",
                "model_version": "400",
                "enable_itn": True,
                "enable_punc": True,
                "enable_ddc": True,
                "show_utterances": True,
                # "vad_segment":True,
                # "end_window_size":300,
                "enable_speaker_info": True
            }
        }
        # print(request)

        response = requests.post(submit_url, json=request, headers=headers)
        logger.info(f'{response=}')
        logger.info(f'{response.headers=}')
        response.raise_for_status()
        code = response.headers.get('X-Api-Status-Code')
        if not code:
            raise RuntimeError(f"未知错误:{response=},{response.headers=}")
        if str(code) != "20000000":
            raise RuntimeError(_error.get(str(code),'未知错误'))

        res = response.json()
        seg_list = res.get('result', {}).get('utterances')
        if not seg_list:
            raise RuntimeError(f'返回数据中无识别结果:{response=}')

        srt_list = []
        speaker_list=[]
        srt_strings=""

        for it in seg_list:
            if not it.get('text','').strip():
                continue
            speaker_list.append(f'spk{it.get("additions", {}).get("speaker", 0)}')
            startraw = tools.ms_to_time_string(ms=it['start_time'])
            endraw = tools.ms_to_time_string(ms=it['end_time'])
            tmp={
                "line": len(srt_list) + 1,
                "start_time": it['start_time'],
                "end_time": it['end_time'],
                "startraw": startraw,
                "endraw": endraw,
                "text": it['text'].strip()
            }
            srt_list.append(tmp)
            srt_strings+=f"{tmp['line']}\n{startraw} --> {endraw}\n{tmp['text']}\n\n"

        self._signal(
            text=srt_strings,
            type='replace_subtitle'
        )
        if speaker_list:
            Path(f'{self.cache_folder}/speaker.json').write_text(json.dumps(speaker_list), encoding='utf-8')
        return srt_list


