from dataclasses import dataclass
from typing import List, Dict, Union

from gradio_client import handle_file

from videotrans.configure.config import params,app_cfg
from videotrans.configure.excepts import StopTask
from videotrans.tts._gradio import GradioBase
from videotrans.tts._index_emotion import index_emotion_for_role
from videotrans.util.help_misc import vail_file

# 兼容 index-webui 中英界面
METHOD_TEXT_EN='Same as the voice reference'
METHOD_TEXT_CN='与音色参考音频相同'
VECTOR_TEXT_EN='Use emotion vectors'
VECTOR_TEXT_CN='使用情感向量控制'
REAL_USE=METHOD_TEXT_EN


@dataclass(repr=False)
class IndexTTS(GradioBase):
    def __post_init__(self):
        self.ainame = "index"
        super().__post_init__()


    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        global REAL_USE
        # 0=v1 1=v2 2=v2.5
        try:
            _v=int(params.get('index_version', 1))
            emotion = index_emotion_for_role(params, data_item['role'])
        except ValueError as e:
            raise StopTask(str(e)) from e
        if vail_file(data_item['filename']):return
        ref_wav,ref_text = self.get_ref_wav(data_item)
        kwargs = {
            "prompt": handle_file(ref_wav),
            "text": data_item['text'].strip(),
            "api_name": '/gen_single'
        }
        if _v >0:
            emo_vector = emotion[0] if emotion else None
            kwargs['emo_control_method'] = (
                VECTOR_TEXT_CN if emo_vector and REAL_USE == METHOD_TEXT_CN else
                VECTOR_TEXT_EN if emo_vector else REAL_USE
            )
            kwargs['emo_ref_path'] = handle_file(ref_wav)
            if emotion:
                kwargs['emo_weight'] = emotion[1]
                kwargs.update({f'vec{i}': value for i, value in enumerate(emo_vector, 1)})
        
        if _v==2:
            kwargs['lang_choice']=self.language.split('-')[0].upper()
        try:
            return self._send(kwargs, data_item)
        except ValueError as e:
            _e=str(e)
            method_mismatch = (
                METHOD_TEXT_CN in _e and METHOD_TEXT_EN in _e
                or VECTOR_TEXT_CN in _e and VECTOR_TEXT_EN in _e
            )
            if method_mismatch and REAL_USE==METHOD_TEXT_EN:
                REAL_USE=METHOD_TEXT_CN
                return self._run(data_item,idx)
            raise            
        
        


