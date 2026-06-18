# 语音合成，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
from pathlib import Path
import traceback, json
from typing import Tuple, Union
from videotrans.configure.config import logger,ROOT_DIR
import soundfile as sf

def _write_log(file, msg):
    try:
        Path(file).write_text(msg, encoding='utf-8')
    except Exception as e:
        logger.warning(f'写入新进程日志时出错{e}')


def qwen3tts_fun(
        queue_tts_file=None,# 配音数据存在 json文件下，根据文件路径获取
        language='Auto',#语言
        logs_file=None,
        defaulelang="en",
        is_cuda=False,
        prompt=None,
        model_name='1.7B',
        roledict=None,
        device_index=0 # gpu索引
)->Tuple[bool,Union[str,None]]:
    import torch
    try:
        from qwen_tts import Qwen3TTSModel
    except ImportError:
        logger.error('please run  uv sync --extra qwentts ')
        return False, 'please run  uv sync --extra qwentts '

    
    CUSTOM_VOICE= {"Vivian", "Serena", "Uncle_fu", "Dylan", "Eric", "Ryan", "Aiden", "Ono_anna", "Sohee"}

    
    queue_tts=json.loads(Path(queue_tts_file).read_text(encoding='utf-8'))
    
    atten=None
    if is_cuda:
        device_map = f'cuda:{device_index}'
        dtype=torch.float16
    else:
        device_map = 'cpu'
        dtype=torch.float32
    
    BASE_OBJ=None
    CUSTOM_OBJ=None
    

    all_roles={ r.get('role') for r in queue_tts}
    logger.debug(f'Qwen-TTS本地内置渠道使用 {model_name} 模型，{device_map=}')
    try:
        if all_roles & CUSTOM_VOICE:
            # 存在自定义音色
            CUSTOM_OBJ=Qwen3TTSModel.from_pretrained(
                f"{ROOT_DIR}/models/models--Qwen--Qwen3-TTS-12Hz-{model_name}-CustomVoice",
                device_map=device_map,
                dtype=dtype,
                attn_implementation=atten
            )
            logger.debug(f'存在内置自定义音色，加载 {model_name} 模型')
        if "clone" in all_roles or all_roles-CUSTOM_VOICE:
            # 存在克隆音色
            BASE_OBJ=Qwen3TTSModel.from_pretrained(
                f"{ROOT_DIR}/models/models--Qwen--Qwen3-TTS-12Hz-{model_name}-Base",
                device_map=device_map,
                dtype=dtype,
                attn_implementation=atten
            )
            logger.debug(f'需要克隆音色，加载 {model_name} 模型')

        _len=len(queue_tts)
        ok,err=0,0
        last_error=''
        for i,it in enumerate(queue_tts):
            text=it.get('text')
            if not text:
                err+=1
                last_error="No text for dubbing"
                continue
            role=it.get('role')
            filename=it.get('filename','')+"-qwen3tts.wav"
            _write_log(logs_file, json.dumps({"type": "logs", "text": f'{i+1}/{_len} {role}'}))
            
            if role in CUSTOM_VOICE and CUSTOM_OBJ:
                wavs, sr = CUSTOM_OBJ.generate_custom_voice(
                    text=text,
                    language=language, # Pass `Auto` (or omit) for auto language adaptive; if the target language is known, set it explicitly.
                    speaker=role,
                    instruct=prompt
                )
                sf.write(filename, wavs[0], sr)
                ok+=1
                continue
            if not BASE_OBJ:
                err+=1
                last_error='load model failed'
                continue
            if role == 'clone':
                wavfile = it.get('ref_wav', '')
                ref_text = it.get('ref_text', '')
            else:
                # 使用 f5-tts文件夹内音频
                wavfile = f'{ROOT_DIR}/f5-tts/{role}'
                ref_text = roledict.get(role) if roledict else None
            
            if not wavfile or not Path(wavfile).is_file():
                # 仍然不存在，无参考音频不可用
                msg = f"不存在参考音频，无法克隆:{role=},{wavfile=}"
                _write_log(logs_file, json.dumps({"type": "logs", "text": msg}))
                err+=1
                last_error=msg
                continue
            kw={
                "text":text,
                "language":language,
                "ref_audio":wavfile,
            }
            if not ref_text:
                kw['x_vector_only_mode']=True
            else:
                kw['ref_text']=ref_text
            wavs, sr = BASE_OBJ.generate_voice_clone(**kw)
            sf.write(filename, wavs[0], sr)
            ok+=1
        if ok<1:
            logger.error(f'配音全部失败：{last_error}')
            return False,"Dubbing failed"+last_error
        logger.error(f'配音成功{ok}个，失败{err}个')
        _write_log(logs_file, json.dumps({"type": "logs", "text": f'{ok=},{err=} {last_error}'}))
        return True,None
    except BaseException as e:
        msg = traceback.format_exc()
        logger.error(msg)
        return False, f'{e},{msg}'
