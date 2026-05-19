import logging
from dataclasses import dataclass
from typing import List, Union

import dashscope
from dashscope.common.error import AuthenticationError
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_fixed, before_log, after_log

from videotrans.configure.excepts import SpeechToTextError, StopTask, NO_RETRY_EXCEPT
from videotrans.configure.config import params, settings, logger
from videotrans.recognition._base import BaseRecogn
from videotrans.task.taskcfg import SrtItem

@dataclass
class Qwen3ASRRecogn(BaseRecogn):
    def __post_init__(self):
        super().__post_init__()
        self.raws = self.cut_audio()

    @retry(retry=retry_if_not_exception_type(NO_RETRY_EXCEPT), stop=(stop_after_attempt(settings.get('retry_nums'))), wait=wait_fixed(2), before=before_log(logger, logging.INFO), after=after_log(logger, logging.INFO))
    def _exec(self) -> Union[List[SrtItem], None]:
        if self._exit(): return
        # 发送请求
        api_key=params.get('qwenmt_key','')
        model=params.get('qwenmt_asr_model','qwen3-asr-flash')
        error=""
        ok_nums=0
        for i, it in enumerate(self.raws):
            if it['text'].strip():
                ok_nums+=1
                continue
            try:
                response = dashscope.MultiModalConversation.call(
                    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key = "sk-xxx",
                    api_key=api_key,
                    model=model,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"audio": it['filename']},
                        ]
                    }],
                    result_format="message",
                    asr_options={
                        "language": self.detect_language[:2].lower(), # 可选，若已知音频的语种，可通过该参数指定待识别语种，以提升识别准确率
                        "enable_lid": True,
                        "enable_itn": True
                    }
                )
            except AuthenticationError as e:
                raise StopTask(str(e))

            if not hasattr(response, 'output') or not hasattr(response.output, 'choices') or not response.output.choices:
                error=f'{response.code}:{response.message}'
                continue
                
            ok_nums+=1
            txt=''
            for t in response.output.choices[0]['message']['content']:
                txt += t['text']
            self.raws[i]['text'] = txt
        if ok_nums==0:
            raise SpeechToTextError(error)
        return self.raws

 
 