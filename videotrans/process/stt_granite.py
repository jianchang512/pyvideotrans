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



def granite_asr(
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
    import torchaudio
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor


    processor = AutoProcessor.from_pretrained(local_dir)
    tokenizer = processor.tokenizer
    device = f'cuda:{device_index}' if is_cuda else 'cpu'
    torch_dtype = torch.bfloat16 if is_cuda and torch.cuda.is_bf16_supported() else torch.float32
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        local_dir, device_map=device, torch_dtype=torch_dtype
    )

    msg = f"Loading model on {device}"
    _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
    vt_logger.debug(f'huggingface_asr渠道使用模型: {local_dir}')
    

    
    try:

        if cut_audio_list and isinstance(cut_audio_list, str):
            cut_audio_list: List[SrtItem] = [SrtItem(**item) for item in
                                             json.loads(Path(cut_audio_list).read_text(encoding='utf-8'))]
        raws = cut_audio_list

        msg = f'Loaded on device={device}'
        _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
        


        total = len(raws)

        for i, it in enumerate(raws):
            wav, sr = torchaudio.load(it['filename'], normalize=True)

            # Create text prompt
            user_prompt = "<|audio|>transcribe the speech with proper punctuation and capitalization."
            chat = [
              {"role": "user", "content": user_prompt},
            ]
            prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)

            # Run the processor + model
            model_inputs = processor(prompt, wav, device=device, return_tensors="pt").to(device)
            model_outputs = model.generate(
              **model_inputs, max_new_tokens=256, do_sample=False, num_beams=1
            )

            # Transformers includes the input IDs in the response
            num_input_tokens = model_inputs["input_ids"].shape[-1]
            new_tokens = model_outputs[0, num_input_tokens:].unsqueeze(0)
            output_text = tokenizer.batch_decode(
              new_tokens, add_special_tokens=False, skip_special_tokens=True
            )            

            it['text']=output_text[0]
        
            _write_log(logs_file, json.dumps({"type": "logs", "text": f"Subtitles {i + 1}/{total}..."}))

                
        return raws, None
                        
    except Exception as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'



