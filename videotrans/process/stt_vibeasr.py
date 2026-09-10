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
    #from transformers import pipeline
    from videotrans.util._srt_parse import ms_to_time_string
    from transformers import AutoProcessor, VibeVoiceAsrForConditionalGeneration,BitsAndBytesConfig


    raws=[]
    try:

        # 8位量化，避免爆显存
        quant= BitsAndBytesConfig( load_in_8bit=True ) if torch.cuda.is_available() else None
        #pipe = pipeline("any-to-any", model=local_dir, device_map=kw.get('device_name', 'auto'),quantization_config=quant)
        
        processor = AutoProcessor.from_pretrained(local_dir)
        model = VibeVoiceAsrForConditionalGeneration.from_pretrained(local_dir, device_map=kw.get('device_name', 'auto'),quantization_config=quant)

        
        
        srts = [item for item in json.loads(Path(cut_audio_list).read_text(encoding='utf-8'))]

        msg = f'Load {model_name} running on {model.device}'
        _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
        logger.debug(f'QwenASR:{local_dir}，{msg}，{detect_language=}')

        for i, it in enumerate(srts):
            chat_template = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "audio",
                            "path": it['filename'],
                        },
                    ],
                }
            ]
            if hotword:
                chat_template[0]['content'].insert(0,{"type":"text","text":hotword})
            offset=it['start_time']
            inputs = processor.apply_chat_template(
                chat_template, 
                #tokenize=True,    
                #return_dict=True,
            ).to(model.device, model.dtype)
            output_ids = model.generate(**inputs)
            generated_ids = output_ids[:, inputs["input_ids"].shape[1] :]

            #dict_output = pipe.processor.extract_speaker_dict(outputs[0]["generated_text"])
            dict_output = processor.decode(generated_ids, return_format="parsed")[0]
            
            for item in dict_output:
                print(f'{item=}')
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
