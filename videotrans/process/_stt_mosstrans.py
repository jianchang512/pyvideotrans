# 语音识别，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
import re, json, traceback
from pathlib import Path
from typing import List, Tuple, Union
from videotrans.task.taskcfg import SrtItem
from videotrans.util import gpus
from videotrans.configure.config import logger
from videotrans.process._stt_utils import _write_log


def mosstrans_asr(
        prompt=None,
        cut_audio_list=None,
        detect_language=None,
        model_name=None,
        logs_file=None,
        is_cuda=False,
        audio_file=None,
        local_dir=None,
        jianfan=False,
        device_index=0  # gpu索引
) -> Tuple[Union[List[SrtItem], bool], Union[str, None]]:
    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor

    from moss_transcribe_diarize.inference_utils import (
        build_transcription_messages,
        generate_transcription
    )

    model_id = local_dir#"OpenMOSS-Team/MOSS-Transcribe-Diarize"


    #device = resolve_device("auto")
    dev_str=f"cuda:{device_index}" if is_cuda else "cpu"
    device = torch.device(dev_str)
    dtype =  torch.float32 if not is_cuda or not torch.cuda.is_bf16_supported() else torch.bfloat16
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        trust_remote_code=True,
        dtype='auto',
        device_map=dev_str
    ).eval()
    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)

    msg = f'Use device {device.type}'
    _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))

    logger.debug(f'huggingface_asr 渠道使用模型: {local_dir}')
    try:
        if cut_audio_list and isinstance(cut_audio_list, str):
            cut_audio_list: List[SrtItem] = [SrtItem(**item) for item in
                                             json.loads(Path(cut_audio_list).read_text(encoding='utf-8'))]
        raws = cut_audio_list

        for i,it in enumerate(raws):
            messages = build_transcription_messages(it['filename'],prompt="请将音频转写为文本，仅返回文本。")
            result = generate_transcription(
                model,
                processor,
                messages,
                max_new_tokens=4096,
                do_sample=False,
                device=device,
                dtype=dtype,
            )
            it['text']=result["text"]
            _write_log(logs_file, json.dumps({"type": "subtitles", "text": f'[{i}] {it["text"]}\n'}))
    
        return raws, None
    except Exception as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'

