# 语音识别，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
import json, traceback
from pathlib import Path
from typing import List, Tuple, Union

from videotrans.configure.config import logger, ROOT_DIR



#支持热词
def qwen3asr_fun(
        cut_audio_list=None,
        logs_file=None,
        is_cuda=False,
        audio_file=None,
        model_name="1.7B",
        device_index=0,  # gpu索引
        hotword=None
):
    import torch
    from qwen_asr import Qwen3ASRModel
    from videotrans.task.taskcfg import SrtItem
    from videotrans.process._stt_utils import _write_log

    if is_cuda:
        device_map = f'cuda:{device_index}'
        dtype = torch.float16
    else:
        device_map = 'cpu'
        dtype = torch.float32

    logger.debug(f'QwenASR本地渠道 {model_name} 模型，{device_map=}')
    try:
        """
        之所以未使用 Qwen/Qwen3-ForcedAligner-0.6B 返回字级时间戳，长语音例如1个小时、2个小时可能OOM，为避免需提前裁切
        1. 如果不使用VAD而是固定时间裁切，可能断在句子中间，影响效果
        2. 若VAD裁切，既然都用VAD了，干脆直接裁切为合适长度语句了，无需再对齐
        3. 返回的词级时间戳无标点符号，需要进一步根据静音区间等断句，可能产生过长过短的字幕
        """
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
