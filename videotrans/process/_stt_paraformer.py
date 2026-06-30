# 语音识别，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
import json, traceback
from pathlib import Path
from typing import List, Tuple, Union
from videotrans.task.taskcfg import SrtItem
from videotrans.util import tools
from videotrans.configure.config import logger
from videotrans.process._stt_utils import _write_log


# 支持热词
def paraformer(
        cut_audio_list=None,
        detect_language=None,
        model_name=None,
        logs_file=None,
        is_cuda=False,
        audio_file=None,
        max_speakers=-1,
        cache_folder=None,
        device_index=0,  # gpu索引
        hotword=None
) -> Tuple[Union[List[SrtItem], bool], Union[str, None]]:
    from modelscope.pipelines import pipeline
    from modelscope.utils.constant import Tasks

    msg = f'Load {model_name}'
    _write_log(logs_file, json.dumps({"type": "logs", "text": f'{msg}'}))
    raw_subtitles = []
    device = f'cuda:{device_index}' if is_cuda else 'cpu'
    logger.debug(f'阿里FunASR渠道使用 {model_name} 模型，{device=}')
    try:
        model = pipeline(
            task=Tasks.auto_speech_recognition,
            model='iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch',
            # model_revision="v2.0.4",
            vad_model='iic/speech_fsmn_vad_zh-cn-16k-common-pytorch',
            # vad_model_revision="v2.0.4",
            punc_model='iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch',
            # punc_model_revision="v2.0.3",
            spk_model="damo/speech_campplus_sv_zh-cn_16k-common",
            # spk_model_revision="v2.0.2",
            disable_update=True,
            disable_progress_bar=True,
            disable_log=True,
            device=device,

            # trust_remote_code=True,
        )

        msg = "Model loading is complete, enter recognition"
        _write_log(logs_file, json.dumps({"type": "logs", "text": f'{msg}'}))

        res = model(audio_file,hotword=hotword.replace(',',' '))
        speaker_list = []
        i = 0
        if not res or 'sentence_info' not in res[0]:
            return False, f'No sentence info: {res}'
        for it in res[0]['sentence_info']:
            if not it.get('text', '').strip():
                continue
            i += 1
            if max_speakers > -1:
                speaker_list.append(f"spk{it.get('spk', 0)}")
            tmp = SrtItem(**{
                "line": len(raw_subtitles) + 1,
                "text": it['text'].strip(),
                "start_time": it['start'],
                "end_time": it['end'],
                "startraw": f'{tools.ms_to_time_string(ms=it["start"])}',
                "endraw": f'{tools.ms_to_time_string(ms=it["end"])}'
            })
            _write_log(logs_file, json.dumps({"type": "subtitles", "text": f'[{i}] {it["text"]}\n'}))
            tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
            raw_subtitles.append(tmp)
        if speaker_list:
            Path(f'{cache_folder}/speaker.json').write_text(json.dumps(speaker_list), encoding='utf-8')
        return raw_subtitles, None
    except BaseException as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'
