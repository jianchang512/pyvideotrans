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
        cut_audio_list=None,
        logs_file=None,
        is_cuda=False,
        audio_file=None,
        local_dir=None,
        cache_folder=None,
        hotword=None,
        device_index=0  # gpu索引
) -> Tuple[Union[List[SrtItem], bool], Union[str, None]]:
    from videotrans.util._srt_parse import get_srt_from_list, get_subtitle_from_srt, ms_to_time_string
    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor

    from videotrans.moss_transcribe_diarize import parse_transcript
    from videotrans.moss_transcribe_diarize.inference_utils import (
        build_transcription_messages,
        generate_transcription,
        resolve_device,
    )

    dev_str=f"cuda:{device_index}" if is_cuda else "cpu"
    device = torch.device(dev_str)
    dtype =  torch.float32 if not is_cuda or not torch.cuda.is_bf16_supported() else torch.bfloat16
    model = AutoModelForCausalLM.from_pretrained(
        local_dir,
        trust_remote_code=True,
        dtype="auto",
    ).to(dtype=dtype).to(device).eval()
    processor = AutoProcessor.from_pretrained(local_dir, trust_remote_code=True)

    msg = f'Use device {device.type}'
    _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))

    logger.debug(f'Moss-Diarize 渠道使用模型: {local_dir}')
    try:
        prompt="请将音频转写为文本，每一段需以起始时间戳和说话人编号（[S01]、[S02]、[S03]…）开头，正文为对应的语音内容，并在段末标注结束时间戳，以清晰标明该段语音范围。"
        if hotword:
            prompt+=f'热词提示：{hotword}'
        if cut_audio_list:
            # 是文件名，获取列表
            cut_audio_list: List[SrtItem] = [SrtItem(**item) for item in
                                             json.loads(Path(cut_audio_list).read_text(encoding='utf-8'))]
            raws = cut_audio_list

            for i,it in enumerate(raws):
                _write_log(logs_file, json.dumps({"type": "logs", "text": f'Moss-Diarize {i}/{len(raws)} \n'}))
                messages = build_transcription_messages(it['filename'],prompt=prompt)
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
        else:
            # 不存在，则完整读取
            messages = build_transcription_messages(audio_file,prompt=prompt)
            result = generate_transcription(
                model,
                processor,
                messages,
                max_new_tokens=4096,
                do_sample=False,
                device=device,
                dtype=dtype,
            )
            raws=[]
            spks=[]
            for i,segment in enumerate(parse_transcript(result["text"])):
                tmp = {
                    "line": i + 1, 
                    "text": segment.text,
                    "start_time": int(float(segment.start)*1000),
                    "end_time": int(float(segment.end)*1000),
                }
                spks.append(segment.speaker.replace('S','spk'))

                tmp['startraw'] = ms_to_time_string(ms=tmp['start_time'])
                tmp['endraw'] = ms_to_time_string(ms=tmp['end_time'])
                tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
                raws.append(tmp)
                _write_log(logs_file, json.dumps({"type": "subtitles", "text": f'[{i}] {tmp["text"]}\n'}))
            if spks:
                Path(f'{cache_folder}/speaker.json').write_text(json.dumps(spks), encoding='utf-8')
        return raws, None
    except Exception as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'

