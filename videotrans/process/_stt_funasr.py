# 语音识别，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
import json, traceback
from pathlib import Path
from typing import List, Tuple, Union
from videotrans.task.taskcfg import SrtItem
from videotrans.configure.config import logger, ROOT_DIR
from videotrans.process._stt_utils import _write_log, _remove_unwanted_characters


def funasr_mlt(
        cut_audio_list=None,
        detect_language=None,
        model_name=None,
        logs_file=None,
        is_cuda=False,
        audio_file=None,
        jianfan=False,
        max_speakers=-1,
        cache_folder=None,
        device_index=0,  # gpu索引
        hotword=None
) -> Tuple[Union[List[SrtItem], bool], Union[str, None]]:
    from funasr import AutoModel
    from modelscope.pipelines import pipeline
    from modelscope.utils.constant import Tasks

    msg = f'Load {model_name}'
    _write_log(logs_file, json.dumps({"type": "logs", "text": f'{msg}'}))

    device = f"cuda:{device_index}" if is_cuda else 'cpu'
    logger.debug(f'阿里FunASR渠道使用 {model_name} 模型，{device=}')
    try:
        if cut_audio_list and isinstance(cut_audio_list, str):
            cut_audio_list: List[SrtItem] = [SrtItem(**item) for item in
                                             json.loads(Path(cut_audio_list).read_text(encoding='utf-8'))]

        srts = cut_audio_list
        if model_name == 'iic/SenseVoiceSmall':
            model = pipeline(
                task=Tasks.auto_speech_recognition,
                model='iic/SenseVoiceSmall',
                # model_revision="master",
                disable_update=True,
                disable_progress_bar=True,
                disable_log=True,
                device=device,
            )
            res = model([it['filename'] for it in cut_audio_list], batch_size=4, disable_pbar=True,hotword=hotword.replace(',',' '))
        else:
            model = AutoModel(
                model=model_name,
                punc_model="iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
                device=device,
                local_dir=ROOT_DIR + "/models",
                disable_update=True,
                disable_progress_bar=True,
                disable_log=True,
                trust_remote_code=True,
                remote_code=f"{ROOT_DIR}/videotrans/codes/model.py",
                hub='ms',
            )

            # vad
            msg = "Recognition starting"
            _write_log(logs_file, json.dumps({"type": "logs", "text": f'{msg}'}))
            num = 0

            def _show_process(ex, dx):
                nonlocal num
                num += 1
                _write_log(logs_file, json.dumps({"type": "logs", "text": f'STT {num}'}))

            res = model.generate(
                input=[it['filename'] for it in srts],
                language=detect_language[:2],  # "zh", "en", "yue", "ja", "ko", "nospeech"
                use_itn=True,
                # batch_size=4,
                progress_callback=_show_process,
                disable_pbar=True,
                hotwords=hotword.split(',') if hotword else []
            )
        for i, it in enumerate(res):
            text = _remove_unwanted_characters(it['text'])
            srts[i]['text'] = text
            _write_log(logs_file, json.dumps({"type": "subtitles", "text": f'[{i}] {text}\n'}))
        return srts, None
    except Exception as e:
        msg = traceback.format_exc()
        return False, f'{e}:{msg}'
