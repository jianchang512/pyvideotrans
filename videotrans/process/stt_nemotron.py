# 语音识别，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
import re, json, traceback, logging
from pathlib import Path
from typing import List, Tuple, Union
from videotrans.task.taskcfg import SrtItem
from videotrans.configure.config import logger
from videotrans.process._stt_utils import _write_log



def nemotron_asr(
        cut_audio_list=None,
        logs_file=None,
        local_dir=None,
        **kw
) -> Tuple[Union[List[SrtItem], bool], Union[str, None]]:
    from transformers import AutoModelForRNNT, AutoProcessor
    from transformers.audio_utils import load_audio


    try:
        if cut_audio_list and isinstance(cut_audio_list, str):
            cut_audio_list: List[SrtItem] = [SrtItem(**item) for item in
                                             json.loads(Path(cut_audio_list).read_text(encoding='utf-8'))]
        raws = cut_audio_list
        processor = AutoProcessor.from_pretrained(local_dir)
        model = AutoModelForRNNT.from_pretrained(local_dir, device_map="auto")
        msg = f"running on {model.device}"
        _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
        logger.debug(f'huggingface_asr渠道使用模型: {local_dir},{msg}')

        total = len(raws)

        for i,it in enumerate(raws):
            _write_log(logs_file, json.dumps({"type": "logs", "text": f"Subtitles {i + 1}/{total}..."}))
            audio = load_audio(it['filename'],
                sampling_rate=processor.feature_extractor.sampling_rate,
            )


            inputs = processor(audio, sampling_rate=processor.feature_extractor.sampling_rate) # equiv to ..., language="auto"
            inputs.to(model.device, dtype=model.dtype)
            output = model.generate(**inputs, return_dict_in_generate=True)
            text_list=processor.decode(output.sequences, skip_special_tokens=True)

            text = text_list[0].strip()
            if text:
                raws[i]['text'] = text
                _write_log(logs_file, json.dumps({"type": "subtitles", "text": f'[{i}] {text}\n'}))
        return raws, None
    except Exception as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'
