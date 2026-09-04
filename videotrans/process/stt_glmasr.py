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


def glmasr_asr(
        cut_audio_list=None,
        logs_file=None,
        local_dir=None,
        **kw
) -> Tuple[Union[List[SrtItem], bool], Union[str, None]]:
    from videotrans.process._stt_utils import _write_log
    import copyreg
    copyreg.pickle(type({}.keys()), lambda k: (list, (list(k),)))
    from transformers import AutoProcessor, GlmAsrForConditionalGeneration, BitsAndBytesConfig
    import torch

    processor = AutoProcessor.from_pretrained(local_dir)

    quant_config = BitsAndBytesConfig( load_in_8bit=True )   if torch.cuda.is_available() else None
    model = GlmAsrForConditionalGeneration.from_pretrained(
        local_dir,
        quantization_config=quant_config,
        device_map=kw.get('device_name','auto'),
        dtype='auto'  # torch.bfloat16  if torch.cuda.is_bf16_supported() else torch.float16
    )
    msg = f'running on {model.device}'
    _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
    logger.debug(f'huggingface_asr 渠道使用模型: {local_dir}, {msg}')
    try:
        if cut_audio_list and isinstance(cut_audio_list, str):
            cut_audio_list: List[SrtItem] = [SrtItem(**item) for item in
                                             json.loads(Path(cut_audio_list).read_text(encoding='utf-8'))]
        raws = cut_audio_list
        conversation = []
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

        _write_log(logs_file, json.dumps({"type": "logs", "text": 'Zai-asr generate text...'}))
        outputs = model.generate(**inputs, do_sample=False, max_new_tokens=500)
        decoded_outputs = processor.batch_decode(
            outputs[:, inputs.input_ids.shape[1]:], skip_special_tokens=True
        )

        total = len(raws)

        for i, (it, text) in enumerate(zip(raws, decoded_outputs)):
            _write_log(logs_file, json.dumps({"type": "logs", "text": f"Subtitles {i + 1}/{total}..."}))
            if text:
                # 清理特殊标记
                cleaned_text = re.sub(r'<unk>|</unk>', '', text).strip()
                raws[i]['text'] = cleaned_text
                _write_log(logs_file, json.dumps({"type": "subtitles", "text": f'[{i}] {cleaned_text}\n'}))
        return raws, None
    except Exception as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'
