# 语音识别，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
import json, traceback
from pathlib import Path
from typing import List

from videotrans.configure.config import logger

def qwen3asr_fun(
        cut_audio_list=None,
        logs_file=None,
        local_dir=None,
        local_dir_align=None,
        max_speech_ms=6000,
        min_speech_ms=3000,
        model_name=None,
        force_align=False,#是否需要对齐时间戳
        **kw
):
    from qwen_asr import Qwen3ASRModel
    from videotrans.task.taskcfg import SrtItem
    from videotrans.process._stt_utils import _write_log,_resegment

    try:
        srts: List[SrtItem] = [SrtItem(**item) for item in json.loads(Path(cut_audio_list).read_text(encoding='utf-8'))]
        if not force_align:
            """
            自动检测语言：不可使用返回时间戳，只有明确指定 ["zh","en","ja",'ko','yue','fr','es','it','de','pt','ru'] 这些语言才支持。
            超过30分钟的视频需要极大显存，可能爆显存，此时设为自动检测语言，可避免
            """
            model = Qwen3ASRModel.from_pretrained(
                local_dir,  # f"{ROOT_DIR}/models/models--Qwen--Qwen3-ASR-{model_name}",
                dtype='auto',
                device_map=kw.get('device_name','auto'),
                max_inference_batch_size=8,
                # Batch size limit for inference. -1 means unlimited. Smaller values can help avoid OOM.
                max_new_tokens=4096,  # Maximum number of tokens to generate. Set a larger value for long audio input.
            )
        else:
            from transformers4576 import BitsAndBytesConfig

            quant_config = BitsAndBytesConfig(
                    load_in_8bit=True
                )
            model = Qwen3ASRModel.from_pretrained(
                local_dir,  # f"{ROOT_DIR}/models/models--Qwen--Qwen3-ASR-{model_name}",
                dtype='auto',
                device_map=kw.get('device_name','auto'),
                max_inference_batch_size=2,
                max_new_tokens=81920, # Maximum number of tokens to generate. Set a larger value for long audio input.
                forced_aligner=local_dir_align,
                quantization_config=quant_config,
                forced_aligner_kwargs=dict(
                    dtype='auto',
                    device_map="auto",
                )
            )

        msg= f'Load {model_name} running on {model.device}'
        _write_log(logs_file, json.dumps({"type": "logs", "text":msg}))
        logger.debug(f'QwenASR 本地渠道  {local_dir} 模型，{msg}')

        if not force_align:
            srts_chunk = [srts[i:i + 4] for i in range(0, len(srts), 4)]
            for i, it_list in enumerate(srts_chunk):
                results = model.transcribe(
                    audio=[it['filename'] for it in it_list],
                    language=[None for it in it_list],
                    return_time_stamps=False,
                    # context=hotword.split(',') if hotword else []
                )
                for j, it in enumerate(it_list):
                    it['text'] = results[j].text
                srts_chunk[i] = it_list
                _write_log(logs_file, json.dumps({"type": "subtitle", "text": "\n".join([it['text'] for it in it_list])}))

            return srts, None


        texts=[{
          "start":0,
          "end":0,
          "text":"",
          "words":[]
        }]
        language=None
        for i,it in enumerate(srts):
            results = model.transcribe(
                audio=[it['filename']],
                language=[None], # can also be set to None for automatic language detection
                return_time_stamps=True,
            )
            if not language:
                language=results[0].language
            timestamps=results[0].time_stamps.items
            offset=it['start_time']/1000.0
            if i==0:
                texts[0]['start']=timestamps[0].start_time+offset
            for item in timestamps:
              tmp={"word":item.text,"start":item.start_time+offset,"end":item.end_time+offset}
              texts[0]['words'].append(tmp)
            if i==len(srts)-1:
                texts[0]['end']=timestamps[-1].end_time+offset

        srts=_resegment(texts, "zh" if language in ["Chinese","Cantonese","Japanese","Korean"] else 'en' , max_speech_ms,min_speech_ms,logs_file)
        return srts,None
    except BaseException as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'
