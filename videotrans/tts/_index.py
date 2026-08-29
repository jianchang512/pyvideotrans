from dataclasses import dataclass
from typing import List, Dict, Union

from gradio_client import handle_file

from videotrans.configure.config import params,app_cfg
from videotrans.tts._gradio import GradioBase
from videotrans.util.help_misc import vail_file

# 兼容 index-webui 中英界面
METHOD_TEXT_EN='Same as the voice reference'
METHOD_TEXT_CN='与音色参考音频相同'
REAL_USE=METHOD_TEXT_EN

@dataclass
class IndexTTS(GradioBase):
    def __post_init__(self):
        self.ainame = "indextts"
        super().__post_init__()


    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        global REAL_USE
        if vail_file(data_item['filename']):return
        ref_wav,ref_text = self.get_ref_wav(data_item)
        kwargs = {
            "prompt": handle_file(ref_wav),
            "text": data_item['text'].strip(),
            "api_name": '/gen_single'
        }
        # 0=v1 1=v2 2=v2.5
        _v=int(params.get('index_tts_version', 1))
        if _v >0:
            kwargs['emo_control_method'] = REAL_USE
            kwargs['emo_ref_path'] = handle_file(ref_wav)
        
        if _v==2:
            kwargs['lang_choice']=self.language.split('-')[0].upper()
        try:
            return self._send(kwargs, data_item)
        except ValueError as e:
            _e=str(e)
            if METHOD_TEXT_CN in _e and METHOD_TEXT_EN in _e and REAL_USE==METHOD_TEXT_EN:                
                REAL_USE=METHOD_TEXT_CN
                return self._run(data_item,idx)
            raise            
        
        


