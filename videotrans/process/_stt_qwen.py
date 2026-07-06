# 语音识别，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
import json, traceback
from pathlib import Path
from typing import List, Tuple, Union
from videotrans.task.taskcfg import SrtItem
from videotrans.configure.config import logger, ROOT_DIR
from videotrans.process._stt_utils import _write_log


#支持热词
def qwen3asr_fun(
        cut_audio_list=None,
        logs_file=None,
        is_cuda=False,
        audio_file=None,
        model_name="1.7B",
        device_index=0,  # gpu索引
        hotword=None
) -> Tuple[Union[List[SrtItem], bool], Union[str, None]]:
    import torch
    from qwen_asr import Qwen3ASRModel

    if is_cuda:
        device_map = f'cuda:{device_index}'
        dtype = torch.float16
    else:
        device_map = 'cpu'
        dtype = torch.float32

    logger.debug(f'QwenASR本地渠道 {model_name} 模型，{device_map=}')
    try:
        _write_log(logs_file, json.dumps({"type": "logs", "text": f'Load Qwen3ASR on {device_map}'}))
        model = Qwen3ASRModel.from_pretrained(
            f"{ROOT_DIR}/models/models--Qwen--Qwen3-ASR-{model_name}",
            dtype=dtype,
            device_map=device_map,
            max_inference_batch_size=8,
            # Batch size limit for inference. -1 means unlimited. Smaller values can help avoid OOM.
            max_new_tokens=2048,  # Maximum number of tokens to generate. Set a larger value for long audio input.
        )
        srts: List[SrtItem] = [SrtItem(**item) for item in json.loads(Path(cut_audio_list).read_text(encoding='utf-8'))]

        srts_chunk = [srts[i:i + 8] for i in range(0, len(srts), 8)]
        for i, it_list in enumerate(srts_chunk):
            results = model.transcribe(
                audio=[it['filename'] for it in it_list],
                language=[None for it in it_list],  # can also be set to None for automatic language detection
                return_time_stamps=False,
                # context=hotword.split(',') if hotword else []
            )
            for j, it in enumerate(it_list):
                it['text'] = results[j].text
            srts_chunk[i] = it_list
            _write_log(logs_file, json.dumps({"type": "subtitle", "text": "\n".join([it['text'] for it in it_list])}))

        return srts, None
    except BaseException as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'
