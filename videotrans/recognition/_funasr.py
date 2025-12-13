# stt项目识别接口
import json
import re,os
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
        allowed_characters = re.compile(r'[^\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af'
                                        r'a-zA-Z0-9\s.,!@#$%^&*()_+\-=\[\]{};\'"\\|<>/?，。！｛｝【】；‘’“”《》、（）￥]+')
        return re.sub(allowed_characters, '', text)

    def _tosend(self, msg):
        self._signal(text=msg)

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return


        if self.model_name == 'SenseVoiceSmall' or self.detect_language[:2].lower() in ['ja','en','ko','yu']:
            return self._exec1()
        raw_subtitles = []
        if not Path(f'{config.ROOT_DIR}/models/models/iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch/model.pt').exists():
            self._tosend('Download paraformer-zh from modelscope.cn')
        else:
            self._tosend('Load paraformer-zh')
        from funasr import AutoModel
        
        model = AutoModel(
            model='iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch', model_revision="v2.0.5",
            vad_model="fsmn-vad", vad_model_revision="v2.0.4",
            punc_model="ct-punc", punc_model_revision="v2.0.4",
            local_dir=config.ROOT_DIR + "/models",
            hub='ms',
            spk_model="cam++" if self.max_speakers>-1 else None, spk_model_revision="v2.0.2" if self.max_speakers>-1 else None,
            disable_update=True,
            disable_progress_bar=True,
            disable_log=True,
            device=self.device
        )
        msg = tr("Model loading is complete, enter recognition")
        self._tosend(msg)
        res = model.generate(input=self.audio_file, return_raw_text=True, is_final=True,
                             sentence_timestamp=True, batch_size_s=100, disable_pbar=True)

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

        return raw_subtitles

    def _exec1(self) -> Union[List[Dict], None]:
        if self._exit():
            return

        if not Path(f'{config.ROOT_DIR}/models/models/iic/SenseVoiceSmall/model.pt').exists():
            self._tosend('Download SenseVoiceSmall from modelscope.cn')
        else:
            self._tosend('Load SenseVoiceSmall')
        from funasr import AutoModel
        from funasr.utils.postprocess_utils import rich_transcription_postprocess
        from concurrent.futures import ThreadPoolExecutor
        
        model = AutoModel(
            model="iic/SenseVoiceSmall",
            punc_model="ct-punc",
            device=self.device,
            local_dir=config.ROOT_DIR + "/models",
            disable_update=True,
            disable_progress_bar=True,
            disable_log=True,
            trust_remote_code=False,
            hub='ms'
        )
        # vad
        
        vm = AutoModel(
            model="fsmn-vad",
            local_dir=config.ROOT_DIR + "/models",
            max_single_segment_time=int(float(config.settings.get('max_speech_duration_s',5))*1000),
            max_end_silence_time=int(config.settings.get('min_silence_duration_ms',500)),
            hub='ms',
            disable_update=True,
            disable_progress_bar=True,
            disable_log=True,
            device=self.device)
        
        msg = tr("Recognition may take a while, please be patient")
        self._tosend(msg)
        segments = vm.generate(input=self.audio_file)
        audiodata = AudioSegment.from_file(self.audio_file)
        
        #srts = self.cut_audio()
        srts=[]
        for i,seg in enumerate(segments[0]['value']):
            chunk = audiodata[seg[0]:seg[1]]
            filename = f"{config.TEMP_DIR}/{seg[0]}-{seg[1]}.wav"
            chunk.export(filename)
            srt = {                
                "line": len(srts) + 1,
                "text": '',
                "file":filename,
                "start_time": seg[0],
                "end_time": seg[1],
                "startraw": f'{tools.ms_to_time_string(ms=seg[0])}',
                "endraw": f'{tools.ms_to_time_string(ms=seg[1])}'
            }
            srt['time'] = f"{srt['startraw']} --> {srt['endraw']}"
            srts.append(srt)

        
        def _stt(i,it):
            res = model.generate(
                input=it['file'],
                language=self.detect_language[:2],  # "zh", "en", "yue", "ja", "ko", "nospeech"
                use_itn=True,
                disable_pbar=True
            )
            text = self.remove_unwanted_characters(rich_transcription_postprocess(res[0]["text"]))
            srts[i]['text']=text
  

            self._signal(
                text=text + "\n",
                type='subtitle'
            )
            

        all_task = []
        with ThreadPoolExecutor(max_workers=min(4,len(srts),os.cpu_count())) as pool:
            for i,item in enumerate(srts):
                all_task.append(pool.submit(_stt, i,item))
            completed_tasks = 0
            total_tasks=len(all_task)
            for task in all_task:
                try:
                    task.result()  # 等待任务完成
                    completed_tasks += 1
                    self._signal( text=f"stt [{completed_tasks}/{total_tasks}]" )
                except Exception as e:
                    logs(f"Task {completed_tasks + 1} failed with error: {e}", level="except")
                    

        return srts
