# 语音识别，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
import re, json, traceback, logging
from pathlib import Path
from typing import List, Tuple, Union
from videotrans.task.taskcfg import SrtItem
from videotrans.configure.config import logger as vt_logger 
from videotrans.process._stt_utils import _write_log


class SuppressLogitsWarningFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        # 拦截 SuppressTokensLogitsProcessor 和 SuppressTokensAtBeginLogitsProcessor
        if "SuppressTokensLogitsProcessor" in msg and "will take precedence" in msg:
            return False
        if "SuppressTokensAtBeginLogitsProcessor" in msg and "will take precedence" in msg:
            return False
        return True


def pipe_asr(
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
    import torch, zhconv
    from transformers import pipeline

    def inputs_generator():
        for item in raws:
            yield item['filename']

    device_arg = f'cuda:{device_index}' if is_cuda else 'auto'

    msg = f"Loading pipeline from {local_dir}"
    _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
    vt_logger.debug(f'huggingface_asr渠道使用模型: {local_dir}')
    
    detect_language = 'tl' if detect_language == 'fil' else detect_language
    
    try:
        if cut_audio_list and isinstance(cut_audio_list, str):
            cut_audio_list: List[SrtItem] = [SrtItem(**item) for item in
                                             json.loads(Path(cut_audio_list).read_text(encoding='utf-8'))]
        raws = cut_audio_list
        p = pipeline(
            task="automatic-speech-recognition",
            model=local_dir,
            batch_size=4,
            device_map=device_arg,
            dtype=torch.float16 if is_cuda else torch.float32,
        )

        msg = f'Pipeline loaded on device={p.model.device}'
        _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
        
        generate_kwargs = {}

        model_type = p.model.config.model_type
        is_whisper = "whisper" in model_type.lower()

        if is_whisper:
            lang = detect_language.split('-')[0] if detect_language != 'auto' else None
            if "uyghur" in local_dir:
                lang = None
            generate_kwargs["task"] = "transcribe"
            if lang:
                generate_kwargs["language"] = lang

            if prompt:
                if hasattr(p.tokenizer, "get_prompt_ids"):
                    prompt_ids = p.tokenizer.get_prompt_ids(prompt, return_tensors="pt")
                else:
                    prompt_ids = p.tokenizer(prompt, add_special_tokens=False, return_tensors="pt").input_ids

                if is_cuda:
                    prompt_ids = prompt_ids.to(p.model.device)

                generate_kwargs["prompt_ids"] = prompt_ids


        gen_logger = logging.getLogger("transformers.generation.utils")
        warning_filter = SuppressLogitsWarningFilter()
        gen_logger.addFilter(warning_filter)

        try:
            results_iterator = p(
                inputs_generator(),
                generate_kwargs=generate_kwargs
            )

            total = len(raws)

            for i, (it, res) in enumerate(zip(raws, results_iterator)):
                _write_log(logs_file, json.dumps({"type": "logs", "text": f"subtitles {i + 1}/{total}..."}))
                text = res.get('text', '')
                if text:
                    cleaned_text = re.sub(r'<unk>|</unk>', '', text).strip()
                    if jianfan:
                        cleaned_text = zhconv.convert(cleaned_text, 'zh-hans')
                    raws[i]['text'] = cleaned_text

                    _write_log(logs_file, json.dumps({"type": "subtitles", "text": f'[{i}] {cleaned_text}\n'}))
                    
            return raws, None
            
        finally:
            gen_logger.removeFilter(warning_filter)
            
    except Exception as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'



