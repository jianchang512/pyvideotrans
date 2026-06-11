from dataclasses import dataclass
from typing import List, Dict, Union

from gradio_client import handle_file

from videotrans.configure.config import params,app_cfg
from videotrans.tts._gradio import GradioBase


@dataclass
class IndexTTS(GradioBase):
    def __post_init__(self):
        self.ainame = "indextts"
        super().__post_init__()


    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        ref_wav,ref_text = self.get_ref_wav(data_item)
        kwargs = {
            "prompt": handle_file(ref_wav),
            "text": data_item['text'].strip(),
            "api_name": '/gen_single'
        }
        # 0=v1 1=v2
        if int(params.get('index_tts_version', 1)) == 1:
            kwargs['emo_control_method'] = app_cfg.indextts_default_choice
            kwargs['emo_ref_path'] = handle_file(ref_wav)
        try:       
            return self._send(kwargs, data_item)
        except Exception as e:
            if app_cfg.indextts_default_choice=='Same as the voice reference' and 'is not in the list of choices' in str(e):
                app_cfg.indextts_default_choice='与音色参考音频相同'
                kwargs['emo_control_method'] = app_cfg.indextts_default_choice
                return self._send(kwargs,data_item)
            raise
        


