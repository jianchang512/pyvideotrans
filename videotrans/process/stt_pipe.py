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



def pipe_asr(
        prompt=None,
        cut_audio_list=None,
        detect_language=None,
        logs_file=None,
        local_dir=None,
        jianfan=False,
        **kw
) -> Tuple[Union[List[SrtItem], bool], Union[str, None]]:
    import zhconv
    from transformers import pipeline

    def inputs_generator():
        for item in raws:
            yield item['filename']

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
            device_map=kw.get('device_name','auto'),
            dtype='auto'  # torch.float16 if is_cuda else torch.float32,
        )
        msg = f"running on {p.model.device}"
        _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
        logger.debug(f'huggingface_asr渠道使用模型: {local_dir},{msg}')

        generate_kwargs = {}
        # 仅 openai官方模型加 generate_kwargs 参数，其他微调可能不兼容，暂不加
        if "--openai--whisper" in local_dir:
            lang = detect_language.split('-')[0] if detect_language != 'auto' else None
            generate_kwargs["task"] = "transcribe"
            if lang:
                generate_kwargs["language"] = lang
            if prompt:
                if hasattr(p.tokenizer, "get_prompt_ids"):
                    prompt_ids = p.tokenizer.get_prompt_ids(prompt, return_tensors="pt")
                else:
                    prompt_ids = p.tokenizer(prompt, add_special_tokens=False, return_tensors="pt").input_ids

                prompt_ids = prompt_ids.to(p.model.device)

                generate_kwargs["prompt_ids"] = prompt_ids

        results_iterator = p(
            inputs_generator(),
            generate_kwargs=generate_kwargs
        )

        total = len(raws)

        for i, (it, res) in enumerate(zip(raws, results_iterator)):
            _write_log(logs_file, json.dumps({"type": "logs", "text": f"Subtitles {i + 1}/{total}..."}))
            text = res.get('text', '')
            if text:
                cleaned_text = re.sub(r'<unk>|</unk>', '', text).strip()
                if jianfan:
                    cleaned_text = zhconv.convert(cleaned_text, 'zh-hans')
                raws[i]['text'] = cleaned_text

                _write_log(logs_file, json.dumps({"type": "subtitles", "text": f'[{i}] {cleaned_text}\n'}))

        return raws, None
    except Exception as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'
