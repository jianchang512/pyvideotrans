# zh_recogn 识别
from dataclasses import dataclass
from typing import List, Dict, Union

import dashscope
from videotrans.configure.config import params
from videotrans.recognition._base import BaseRecogn

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class Qwen3ASRRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()


    def _exec(self) -> Union[List[Dict], None]:
        if self._exit(): return
        # 发送请求
        raws = self.cut_audio()
        api_key=params.get('qwenmt_key','')
        model=params.get('qwenmt_asr_model','qwen3-asr-flash')
        error=""
        ok_nums=0
        for i, it in enumerate(raws):
            response = dashscope.MultiModalConversation.call(
                # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key = "sk-xxx",
                api_key=api_key,
                model=model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"audio": it['file']},
                    ]
                }],
                result_format="message",
                asr_options={
                    "language": self.detect_language[:2].lower(), # 可选，若已知音频的语种，可通过该参数指定待识别语种，以提升识别准确率
                    "enable_lid": True,
                    "enable_itn": True
                }
            )
            if not hasattr(response, 'output') or not hasattr(response.output, 'choices'):
                error=f'{response.code}:{response.message}'
                continue
                
            ok_nums+=1
            txt=''
            for t in response.output.choices[0]['message']['content']:
                txt += t['text']
            raws[i]['text'] = txt
        if ok_nums==0:
            raise RuntimeError(error)
        return raws

 
 