# 语音合成，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
from pathlib import Path
import traceback, json,os
from typing import Tuple, Union
from videotrans.configure.config import logger,ROOT_DIR
from ._utils import _write_log


def omnivoice_fun(
        queue_tts_file=None,# 配音数据存在 json文件下，根据文件路径获取
        logs_file=None,
        is_cuda=False,
        speed=1.0,
        device_index=0 # gpu索引
)->Tuple[bool,Union[str,None]]:
    from videotrans.util.help_role import get_f5tts_role
    from videotrans.util.help_misc import vail_file
    import torch
    from omnivoice import OmniVoice
    from videotrans.util import gpus
    import soundfile as sf
    queue_tts=json.loads(Path(queue_tts_file).read_text(encoding='utf-8'))
        
    model = OmniVoice.from_pretrained(
            f'{ROOT_DIR}/models/models--k2-fsa--OmniVoice',
            device_map=f'cuda:{device_index}' if is_cuda else  gpus.mps_or_cpu(),
            dtype=torch.float32 if not is_cuda else torch.float16
    )    
    
    logger.debug(f'OmniVoice-TTS本地内置渠道，{is_cuda=}')
    try:
    
        _len=len(queue_tts)
        ok,err=0,0
        last_error=''
        roledict=get_f5tts_role()
        for i,it in enumerate(queue_tts):
            text=it.get('text')
            if not text:
                err+=1
                last_error="No text for dubbing"
                continue
            role=it.get('role')
            filename=it.get('filename','')+"-24k.wav"
            _write_log(logs_file, json.dumps({"type": "logs", "text": f'{i+1}/{_len} {role}'}))
            if role == 'clone':
                wavfile = it.get('ref_wav', '')
                ref_text = it.get('ref_text', '')
            else:
                # 使用 f5-tts文件夹内音频
                wavfile = f'{ROOT_DIR}/f5-tts/{role}'
                ref_text = roledict.get(role,{}).get('ref_text') if roledict  else None
            
            if not wavfile or not Path(wavfile).is_file():
                # 仍然不存在，无参考音频不可用
                msg = f"No ref_audio: {role=},{wavfile=}"
                _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
                err+=1
                last_error=msg
                continue
            wav = model.generate(
                    text=it['text'],
                    ref_audio=wavfile,
                    ref_text=ref_text,
                    speed=speed
            )
            sf.write(filename, wav[0], 24000)
            if not vail_file(filename):
                err += 1
                continue

            ok+=1
        if ok<1:
            logger.error(f'配音全部失败：{last_error}')
            return False,"Dubbing failed"+last_error
        logger.debug(f'配音成功{ok}个，失败{err}个')
        _write_log(logs_file, json.dumps({"type": "logs", "text": f'{ok=},{err=} {last_error}'}))
        return True,None
    except BaseException as e:
        msg = traceback.format_exc()
        logger.error(msg)
        return False, f'{e},{msg}'
