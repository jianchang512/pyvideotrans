# 语音识别，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
import json, traceback
import re
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
        detect_language=None,
        force_align=False,  # 是否需要对齐时间戳:只有明确指定属于这些语言中的某个 ["zh","en","ja",'ko','yue','fr','es','it','de','pt','ru'] 才支持
        hotword=None,
        **kw
):
    import copyreg
    copyreg.pickle(type({}.keys()), lambda k: (list, (list(k),)))
    from transformers4576 import BitsAndBytesConfig
    from qwen_asr import Qwen3ASRModel
    from videotrans.task.taskcfg import SrtItem
    from videotrans.process._stt_utils import _write_log, _resegment
    import torch

    try:
        batch_size=2
        # 8位量化，避免爆显存
        quant= BitsAndBytesConfig( load_in_8bit=True ) if torch.cuda.is_available() else None
        srts: List[SrtItem] = [SrtItem(**item) for item in json.loads(Path(cut_audio_list).read_text(encoding='utf-8'))]
        if not force_align:
            model = Qwen3ASRModel.from_pretrained(
                local_dir,
                dtype='auto',
                device_map=kw.get('device_name', 'auto'),
                max_inference_batch_size=batch_size,
                max_new_tokens=4096,
                quantization_config=quant,
            )
        else:


            model = Qwen3ASRModel.from_pretrained(
                local_dir,
                dtype='auto',
                device_map=kw.get('device_name', 'auto'),
                max_inference_batch_size=batch_size,
                max_new_tokens=80920,#80k
                forced_aligner=local_dir_align,
                quantization_config=quant,
                forced_aligner_kwargs=dict(
                    dtype='auto',
                    device_map=kw.get('device_name', 'auto')
                )
            )

        msg = f'Load {model_name} running on {model.device}'
        _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
        logger.debug(f'QwenASR:{local_dir}，{msg}，{detect_language=}, 是否返回字级时间戳:{force_align}')

        if not force_align:
            # 不返还时间戳数据
            srts_chunk = [srts[i:i + batch_size] for i in range(0, len(srts), batch_size)]
            for i, it_list in enumerate(srts_chunk):
                results = model.transcribe(
                    audio=[it['filename'] for it in it_list],
                    language=[None for it in it_list],
                    return_time_stamps=False,
                    context=[hotword for it in it_list]
                )
                for j, it in enumerate(it_list):
                    it['text'] = results[j].text
                srts_chunk[i] = it_list
                _write_log(logs_file, json.dumps({"type": "subtitle", "text": "\n".join([it['text'] for it in it_list])}))

            return srts, None

        # 需要返回时间戳
        texts = [{
            "start": 0,
            "end": 0,
            "text": "",
            "words": []
        }]
        language = None
        srts_chunk = [srts[i:i + batch_size] for i in range(0, len(srts), batch_size)]
        for i, it_list in enumerate(srts_chunk):
            results = model.transcribe(
                audio=[it['filename'] for it in it_list],
                language=[None for it in it_list],
                return_time_stamps=True,
                context=[hotword for it in it_list]
            )
            if not language:
                language = results[0].language
            for j,it in enumerate(it_list):
                timestamps = results[j].time_stamps.items
                offset = it['start_time'] / 1000.0
                if i == 0 and j==0:
                    texts[0]['start'] = timestamps[0].start_time + offset
                for item in timestamps:
                    texts[0]['words'].append({"word": item.text, "start": item.start_time + offset, "end": item.end_time + offset})
                _write_log(logs_file, json.dumps({"type": "subtitle", "text":"\n".join(re.split(r'[,.?!，。？！]',results[j].text)) +"\n" }))
                if i == len(srts_chunk) - 1 and j==len(it_list)-1:
                    texts[0]['end'] = timestamps[-1].end_time + offset

        srts = _resegment(texts, "zh" if language in ["Chinese", "Cantonese", "Japanese", "Korean"] else 'en',
                          max_speech_ms, min_speech_ms, logs_file)
        return srts, None
    except BaseException as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'
