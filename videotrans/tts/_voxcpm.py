from dataclasses import dataclass
from typing import List, Dict, Union

from gradio_client import handle_file

from videotrans.configure.config import params
from videotrans.tts._gradio import GradioBase


@dataclass
class VoxCPMTTS(GradioBase):
    def __post_init__(self):
        self.ainame = "voxcpmtts"
        super().__post_init__()

    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        kwargs = {
            "do_normalize": True,
            "denoise": True,
            "api_name": '/generate'
        }
        _version = params.get('voxcpmtts_version', 'v2')
        text=data_item['text'].strip()
        ref_wav,ref_text=self.get_ref_wav(data_item)
        if _version == 'v2':
            kwargs['text'] = text
            kwargs['control_instruction'] = ''
            kwargs['use_prompt_text'] = True if ref_text else False
            kwargs['ref_wav'] = handle_file(ref_wav)
            kwargs['dit_steps'] = 10
            kwargs["cfg_value"] = 2
            kwargs["prompt_text_value"] = ref_text
        elif _version == 'hf':
            kwargs['text_input'] = text
            kwargs['control_instruction'] = ''
            kwargs['use_prompt_text'] = True if ref_text else False
            kwargs['reference_wav_path_input'] = handle_file(ref_wav)
            # kwargs['inference_timesteps']=10
            kwargs["cfg_value_input"] = 2
            kwargs["prompt_text_input"] = ref_text

        else:
            kwargs['text_input'] = text
            kwargs['prompt_wav_path_input'] = handle_file(ref_wav)
            kwargs['inference_timesteps_input'] = 10
            kwargs["cfg_value_input"] = 2
            kwargs["prompt_text_input"] = ref_text
        return self._send(kwargs,data_item)
