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
    import torch,zhconv
    from transformers import pipeline

    # 定义输入生成器，直接把路径或音频数据喂给 pipeline
    def inputs_generator():
        for item in raws:
            yield item['filename']

    # 2. 初始化 Pipeline
    # 使用 device_map="auto" 自动分配，或指定 device
    device_arg = device_index if is_cuda else gpus.mps_or_cpu()
    # 使用 device_map="auto" 时不需要传 device 参数，二者选一
    # 如果是单卡环境，直接传 device=0 效率通常比 device_map="auto" 稍微高一点点

    msg = f"Loading pipeline from {local_dir}"
    _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
    logger.debug(f'huggingface_asr渠道使用模型: {local_dir}')
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
            device=device_arg,
            dtype=torch.float16 if is_cuda else torch.float32,
        )

        msg = f'Pipeline loaded on device={p.model.device}'
        _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
        # 3. 动态构建 generate_kwargs
        generate_kwargs = {}

        # 获取模型类型，例如 'whisper', 'wav2vec2', 'huBERT', 'parakeet' 等
        model_type = p.model.config.model_type
        is_whisper = "whisper" in model_type.lower()

        if is_whisper:
            # === Whisper 专用参数 ===
            lang = detect_language.split('-')[0] if detect_language != 'auto' else None

            generate_kwargs["task"] = "transcribe"
            if lang:
                generate_kwargs["language"] = lang

            # 处理 Prompt
            if prompt:
                # 获取 tokenizer 并转换 prompt 为 token IDs
                # 兼容旧版本 transformers
                if hasattr(p.tokenizer, "get_prompt_ids"):
                    prompt_ids = p.tokenizer.get_prompt_ids(prompt, return_tensors="pt")
                else:
                    # 通用回退方案
                    prompt_ids = p.tokenizer(prompt, add_special_tokens=False, return_tensors="pt").input_ids

                # 确保 tensor 在正确的设备上
                if is_cuda:
                    prompt_ids = prompt_ids.to(p.model.device)

                # 注意：这里需要取 [0] 或者是 tensor 本身，取决于 pipeline 版本，
                # 通常传入 tensor 即可，但某些版本需要 list。
                # 安全起见，转为 tensor 传入通常是支持的，或者转为 list: prompt_ids.tolist()[0]
                generate_kwargs["prompt_ids"] = prompt_ids


        # 4. 执行批量推理
        # 这里的 p(...) 返回的是一个迭代器，它会在后台进行 batch 处理
        results_iterator = p(
            inputs_generator(),
            generate_kwargs=generate_kwargs
        )

        total = len(raws)

        # 5. 收集结果
        # 注意：这里我们同时遍历 raws 和 results_iterator
        # 因为 inputs_generator 是按顺序 yield 的，results_iterator 也会按顺序输出
        for i, (it, res) in enumerate(zip(raws, results_iterator)):
            _write_log(logs_file, json.dumps({"type": "logs", "text": f"subtitles {i + 1}/{total}..."}))
            text = res.get('text', '')
            if text:
                # 清理特殊标记
                cleaned_text = re.sub(r'<unk>|</unk>', '', text).strip()
                if jianfan:
                    cleaned_text = zhconv.convert(cleaned_text, 'zh-hans')
                raws[i]['text'] = cleaned_text

                # 如果 pipeline 返回了时间戳（取决于 chunk_length_s 和 return_timestamps 参数）
                _write_log(logs_file, json.dumps({"type": "subtitles", "text": f'[{i}] {cleaned_text}\n'}))
        return raws, None
    except Exception as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'
