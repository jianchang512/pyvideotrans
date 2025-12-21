# stt项目识别接口
import json
import re,os,requests
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union


from pydub import AudioSegment

from videotrans.configure import config
from videotrans.configure.config import tr,logs
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools


@dataclass
class FunasrRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()

    def remove_unwanted_characters(self, text: str) -> str:
        # 保留中文、日文、韩文、英文、数字和常见符号，去除其他字符
        allowed_characters = re.compile(r'<\|\w+\|>')
        return re.sub(allowed_characters, '', text)

    def _tosend(self, msg):
        self._signal(text=msg)

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return


        if self.model_name !='paraformer-zh' or  self.detect_language[:2].lower() not in ['zh','en']:
            return self._exec1()
            
        raw_subtitles = []       
        model_dir=f'{config.ROOT_DIR}/models/models/iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch'
        if not Path(model_dir).exists():
            self._tosend(f'Download {self.model_name} from modelscope.cn')
        else:
            self._tosend(f'Load {self.model_name} model')
        from funasr import AutoModel
        model=None
        try:
            model = AutoModel(
                model='iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch',
                vad_model="fsmn-vad", 
                punc_model="ct-punc",
                local_dir=config.ROOT_DIR + "/models",
                hub='ms',
                spk_model="cam++" if self.max_speakers>-1 else None, 
                disable_update=True,
                disable_progress_bar=True,
                disable_log=True,
                device=self.device
            )
        except (OSError,AssertionError) as e:
            if not Path(model_dir+'/config.yaml').exists():
                raise RuntimeError(config.tr('downloading model.safetensors and all .json files',f'{config.ROOT_DIR}/models/models/iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch')+f'\n[https://modelscope.cn/models/iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch/files]\n{e}')
            raise
        
        msg = tr("Model loading is complete, enter recognition")
        self._tosend(msg)
        num=0
        def _show_process(ex,dx):
            nonlocal num
            num+=1
            self._tosend(f'STT {num}')
            
        res = model.generate(
            input=self.audio_file, 
            return_raw_text=True, 
            is_final=True,
            batch_size=64,
            sentence_timestamp=True, 
            progress_callback=_show_process,
            disable_pbar=True)

        speaker_list=[]
        for it in res[0]['sentence_info']:
            if not it.get('text','').strip():
                continue
            if self.max_speakers>-1:
                speaker_list.append(f"spk{it.get('spk', 0)}")
            tmp = {
                "line": len(raw_subtitles) + 1,
                "text":it['text'].strip(),
                "start_time": it['start'],
                "end_time": it['end'],
                "startraw": f'{tools.ms_to_time_string(ms=it["start"])}',
                "endraw": f'{tools.ms_to_time_string(ms=it["end"])}'
            }
            self._signal(text=it['text'] + "\n", type='subtitle')
            tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
            raw_subtitles.append(tmp)
        if speaker_list:
            Path(f'{self.cache_folder}/speaker.json').write_text(json.dumps(speaker_list), encoding='utf-8')
        try:
            import torch
            import gc
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            del model
            gc.collect()
        except Exception:
            pass
        return raw_subtitles
    
    def _show_process(self,end_idx,nu):
        print(f'{end_idx=},{nu=}')
        self._tosend(f'STT {end_idx}/{nu}')

    def _exec1(self) -> Union[List[Dict], None]:
        if self._exit():
            return
            
        if self.model_name =='paraformer-zh':
            self.model_name='FunAudioLLM/Fun-ASR-MLT-Nano-2512' if self.detect_language[:2] not in ['ja','yu'] else 'FunAudioLLM/Fun-ASR-Nano-2512'
        elif self.model_name=='SenseVoiceSmall':
            self.model_name='iic/SenseVoiceSmall'
        elif self.model_name =='Fun-ASR-Nano-2512':
            if self.detect_language[:2] not in ['zh','en','ja','yu']:
                self.model_name=f'FunAudioLLM/Fun-ASR-MLT-Nano-2512'
            else:
                self.model_name=f'FunAudioLLM/Fun-ASR-Nano-2512'
        else:
            self.model_name=f'FunAudioLLM/Fun-ASR-MLT-Nano-2512'


        if not Path(f'{config.ROOT_DIR}/models/models/{self.model_name}').exists():
            self._tosend(f'Download {self.model_name} from modelscope.cn')
        else:
            self._tosend(f'Load {self.model_name}')
        
        from funasr import AutoModel
        from funasr.utils.postprocess_utils import rich_transcription_postprocess
        from concurrent.futures import ThreadPoolExecutor
        print(f'{self.model_name=}')
        model=None
        try:
            model = AutoModel(
                model=self.model_name,
                punc_model="ct-punc",
                device=self.device,
                local_dir=config.ROOT_DIR + "/models",
                disable_update=True,
                disable_progress_bar=True,
                disable_log=True,
                trust_remote_code=True,
                remote_code=f"{config.ROOT_DIR}/videotrans/codes/model.py",
                hub='ms',
            )
        except Exception as e:
            raise 
        
        # vad
        msg = tr("Recognition may take a while, please be patient")
        self._tosend(msg)        
        srts=self.cut_audio()
        res = model.generate(
                input=[it['file'] for it in srts],
                language=self.detect_language[:2],  # "zh", "en", "yue", "ja", "ko", "nospeech"
                use_itn=True,
                batch_size=1,
                progress_callback=self._show_process,
                disable_pbar=True
        )
        for i,it in enumerate(res):
            print(f'{it=}')
            srts[i]['text']=self.remove_unwanted_characters(it['text'])
        try:
            import torch
            import gc
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            del model
            #del vm
            gc.collect()
        except Exception:
            pass


        return srts
