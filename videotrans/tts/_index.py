from dataclasses import dataclass
from typing import List, Dict, Union

from gradio_client import handle_file

from videotrans.configure.config import params,app_cfg
from videotrans.tts._gradio import GradioBase
from videotrans.util.help_misc import vail_file


@dataclass
class IndexTTS(GradioBase):
    def __post_init__(self):
        self.ainame = "indextts"
        super().__post_init__()


    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
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
            kwargs['emo_control_method'] = app_cfg.indextts_default_choice
            kwargs['emo_ref_path'] = handle_file(ref_wav)
        
        if _v==2:
            kwargs['lang_choice']=self.language.split('-')[0].upper()
        try:       
            return self._send(kwargs, data_item)
        except Exception as e:
            if '与音色参考音频相同' in str(e):
                raise ValueError(f'请打开 Index-TTS 中的 webui.py,搜索 i18n("与音色参考音频相同") ，将它改为 "Same as the voice reference" ,保存后重启 Index-TTS webui.py')
            raise
        


