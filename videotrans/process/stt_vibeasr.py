# 语音识别，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
import json, traceback
import re
from pathlib import Path
from typing import List
from videotrans.configure.config import logger


def videasr_fun(
        cut_audio_list=None,
        logs_file=None,
        local_dir=None,
        max_speech_ms=6000,
        min_speech_ms=3000,
        model_name=None,
        detect_language=None,
        hotword=None,
        **kw
):
    import copyreg
    copyreg.pickle(type({}.keys()), lambda k: (list, (list(k),)))
    from videotrans.task.taskcfg import SrtItem
    from videotrans.process._stt_utils import _write_log
    import torch
    from videotrans.util._srt_parse import ms_to_time_string
    from transformers import AutoProcessor, VibeVoiceAsrForConditionalGeneration,BitsAndBytesConfig


    raws=[]
    try:

        # 8位量化，避免爆显存
        #quant= BitsAndBytesConfig( load_in_8bit=True ) if torch.cuda.is_available() else None
        
        processor = AutoProcessor.from_pretrained(local_dir)
        model = VibeVoiceAsrForConditionalGeneration.from_pretrained(local_dir, device_map=kw.get('device_name', 'auto'))

        
        
        srts = [item for item in json.loads(Path(cut_audio_list).read_text(encoding='utf-8'))]

        msg = f'Load {model_name} running on {model.device}'
        _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
        logger.debug(f'QwenASR:{local_dir}，{msg}，{detect_language=}')
        srts_chunk = [srts[i:i + 2] for i in range(0, len(srts), 2)]
        print(f'#### {len(srts_chunk)=}')
        for j, it_list in enumerate(srts_chunk):
          print(f'{j=},{len(it_list)=}')
          inputs = processor.apply_transcription_request(
              audio=[it['filename'] for it in it_list], 
              prompt=[hotword for it in it_list]
          ).to(model.device, model.dtype)
          output_ids = model.generate(**inputs)
          generated_ids = output_ids[:, inputs["input_ids"].shape[1] :]
          dict_output_list = processor.decode(generated_ids, return_format="parsed")
          for i,dict_output in enumerate(dict_output_list):
            offset=it_list[i]['start_time']
            print(f'\t[{i=} {offset=}]{len(dict_output)=}')

              
            for item in dict_output:
              print(f'\t{item=}')
              _s=offset+int(float(item['Start'])*1000)
              _e=offset+int(float(item['End'])*1000)
              _sraw=ms_to_time_string(ms=_s)
              _eraw=ms_to_time_string(ms=_e)
              t={
                  "line":len(raws)+1,
                  "text":item['Content'],
                  "start_time": _s,
                  "end_time":_e,
                  "startraw":_sraw,
                  "endraw":_eraw,
                  "time":f'{_sraw} --> {_eraw}'
              }
              raws.append(t)
              _write_log(logs_file, json.dumps({"type": "subtitle", "text": f"{t['text']}\n"}))
                

        return raws, None
    except BaseException as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'
