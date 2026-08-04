# 语音合成，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
import time
from pathlib import Path
import traceback, json
from typing import Tuple, Union
from videotrans.configure.config import logger,ROOT_DIR,REDUBB_QUEUE_FILE,REDUBB_STATUS_FILE
from ._utils import _write_log,convert_to_wav


def confucius_fun(
        queue_tts_file=None,# 配音数据存在 json文件下，根据文件路径获取
        language='zh',#语言
        logs_file=None,
        is_cuda=False,
        device_index=0, # gpu索引
        is_redubb=False#是否处于单视频校对配音流程
)->Tuple[bool,Union[str,None]]:
    from videotrans.util.help_misc import vail_file
    import torchaudio
    from videotrans.confuciustts.cli.inference import ConfuciusTTS

    try:
        model = ConfuciusTTS(
            device=f'cuda:{device_index}' if is_cuda else 'cpu',
        )
        logger.debug(f'Confucius-TTS 本地内置渠道，{is_cuda=}')
        if is_redubb:
            queue_tts_file=REDUBB_QUEUE_FILE
        # 循环，用于轮询重新配音数据，非重新配音时，第一轮直接返回
        while 1:
            if is_redubb and Path(REDUBB_STATUS_FILE).exists():
                return True,None
            queue_tts=json.loads(Path(queue_tts_file).read_text(encoding='utf-8'))

            _len=len(queue_tts)
            ok,err=0,0
            last_error=''

            for i,it in enumerate(queue_tts):
                if is_redubb and Path(REDUBB_STATUS_FILE).exists():
                    return True,None
                output_filename=it.get('filename','')+"-24k.wav"
                if vail_file(it.get('filename','')):
                    ok+=1
                    continue
                text=it.get('text')
                if not text:
                    err+=1
                    last_error="No text for dubbing"
                    continue
                role=it.get('role')
                _write_log(logs_file, json.dumps({"type": "logs", "text": f'Confucius-TTS {i+1}/{_len} {role}'}))

                if role == 'clone':
                    wavfile = it.get('ref_wav', '')
                else:
                    # 使用 f5-tts文件夹内音频
                    wavfile = f'{ROOT_DIR}/f5-tts/{role}'

                if not wavfile or not Path(wavfile).is_file():
                    # 仍然不存在，无参考音频不可用
                    msg = f"No ref_audio: {role=},{wavfile=}"
                    _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
                    err+=1
                    last_error=msg
                    continue

                audio = model.generate(it['text'],language ,wavfile, verbose=False)
                torchaudio.save(output_filename, audio.cpu(), model.sample_rate)
                if not vail_file(output_filename):
                    err += 1
                    continue
                ok+=1
                if is_redubb:
                    convert_to_wav(output_filename,it['filename'])

            # 是重新配音，继续轮询
            if is_redubb:
                time.sleep(1)
                continue
            break

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
