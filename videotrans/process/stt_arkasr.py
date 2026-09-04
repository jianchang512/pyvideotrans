# 语音识别，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
import json, traceback
from pathlib import Path
from typing import List, Tuple, Union
from videotrans.task.taskcfg import SrtItem
from videotrans.configure.config import logger as vt_logger
from videotrans.process._stt_utils import _write_log


def ark_asr(
        cut_audio_list=None,
        logs_file=None,
        local_dir=None,
        **kw
) -> Tuple[Union[List[SrtItem], bool], Union[str, None]]:
    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor, AutoTokenizer


    try:
        processor = AutoProcessor.from_pretrained(local_dir, trust_remote_code=True)
        tokenizer = AutoTokenizer.from_pretrained(local_dir, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            local_dir,
            trust_remote_code=True,
            dtype='auto',
            device_map=kw.get('device_name','auto'),
            attn_implementation="sdpa",
        )
        _write_log(logs_file, json.dumps({"type": "logs", "text": f"Running on {model.device}"}))
        vt_logger.debug(f'{local_dir}, running on {model.device}')
        model.eval()

        def build_bad_words_ids():
            eos_ids = tokenizer.eos_token_id
            keep_ids = {eos_ids} if isinstance(eos_ids, int) else set(eos_ids or [])
            bad_ids = set(tokenizer.all_special_ids) - keep_ids
            bad_ids.update(
                token_id
                for token, token_id in tokenizer.get_added_vocab().items()
                if token.startswith("<") and token.endswith(">") and token_id not in keep_ids
            )
            return [[token_id] for token_id in sorted(bad_ids)]

        if cut_audio_list and isinstance(cut_audio_list, str):
            cut_audio_list: List[SrtItem] = [SrtItem(**item) for item in
                                             json.loads(Path(cut_audio_list).read_text(encoding='utf-8'))]
        raws = cut_audio_list
        total = len(raws)
        for i, it in enumerate(raws):
            conversation = [
                {
                    "role": "user",
                    "content": [
                        {"type": "audio", "path": it['filename']},
                        {"type": "text", "text": "Please transcribe this audio."},
                    ],
                }
            ]

            inputs = processor.apply_chat_template(
                conversation,
                add_generation_prompt=True,
                return_tensors="pt",
                sampling_rate=16000,
                audio_padding="longest",
                text_kwargs={"padding": "longest"},
                audio_max_length=30 * 16000,
            )
            inputs = inputs.to(model.device)

            bad_words_ids = build_bad_words_ids()
            with torch.inference_mode():
                outputs = model.generate(
                    **inputs,
                    do_sample=False,
                    max_new_tokens=256,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                    bad_words_ids=bad_words_ids,
                )
            decoded_outputs = tokenizer.batch_decode(
                outputs[:, inputs.input_ids.shape[1]:],
                skip_special_tokens=True,
            )
            it['text'] = decoded_outputs[0]

            _write_log(logs_file, json.dumps({"type": "logs", "text": f"Subtitles {i + 1}/{total}..."}))

        return raws, None

    except Exception as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'
