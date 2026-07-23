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


def glmasr_asr(
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
    import torch,zhconv
    from transformers import AutoProcessor, GlmAsrForConditionalGeneration
    
    checkpoint_name = local_dir
    processor = AutoProcessor.from_pretrained(local_dir)


    # 使用 device_map="auto" 自动分配，或指定 device
    device_arg = f"cuda:{device_index}" if is_cuda else "auto"
    model = GlmAsrForConditionalGeneration.from_pretrained(local_dir, device_map=device_arg)
    msg = f'Use device {model.device}'
    _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))

    logger.debug(f'huggingface_asr 渠道使用模型: {local_dir}')
    try:
        if cut_audio_list and isinstance(cut_audio_list, str):
            cut_audio_list: List[SrtItem] = [SrtItem(**item) for item in
                                             json.loads(Path(cut_audio_list).read_text(encoding='utf-8'))]
        raws = cut_audio_list
        conversation=[]
        for it in cut_audio_list:
            conversation.append(
                [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "audio",
                                "url": it['filename'],
                            },
                            {"type": "text", "text": "Please transcribe this audio into text"},
                        ],
                    },
                ]
            )
    
        inputs = processor.apply_chat_template(
            conversation, tokenize=True, add_generation_prompt=True, return_dict=True
        ).to(model.device, dtype=model.dtype)
        inputs_transcription = processor.apply_transcription_request(
            [it['filename'] for it in cut_audio_list],
        ).to(model.device, dtype=model.dtype)
        _write_log(logs_file, json.dumps({"type": "logs", "text": 'Generate text...'}))
        outputs = model.generate(**inputs, do_sample=False, max_new_tokens=500)
        decoded_outputs = processor.batch_decode(
            outputs[:, inputs.input_ids.shape[1] :], skip_special_tokens=True
        )

        total = len(raws)

        for i, (it, text) in enumerate(zip(raws, decoded_outputs)):
            _write_log(logs_file, json.dumps({"type": "logs", "text": f"subtitles {i + 1}/{total}..."}))
            if text:
                # 清理特殊标记
                cleaned_text = re.sub(r'<unk>|</unk>', '', text).strip()
                if jianfan:
                    cleaned_text = zhconv.convert(cleaned_text, 'zh-hans')
                raws[i]['text'] = cleaned_text
                _write_log(logs_file, json.dumps({"type": "subtitles", "text": f'[{i}] {cleaned_text}\n'}))
        return raws, None
    except Exception as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'

