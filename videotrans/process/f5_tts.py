# 语音合成，新进程执行
# 返回元组
# 失败：第一个值为False，则为失败，第二个值存储失败原因
# 成功，第一个值存在需要的返回值，不需要时返回True，第二个值为None
from pathlib import Path
import traceback, json
from typing import Tuple, Union
from videotrans.configure.config import logger,ROOT_DIR
from ._utils import _write_log

# ----- 绕过 f5tts overrides 的严格类型检查 -----
try:
    import overrides
    def _dummy_overrides(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]
        return lambda m: m
    overrides.overrides = _dummy_overrides
except ImportError:
    pass

from f5_tts.api import F5TTS
from omegaconf import OmegaConf
from hydra.utils import get_class
from f5_tts.infer.utils_infer import (
    load_model,
    load_vocoder
)

# 重新 F5TTS 初始化方法，以实现多语言
class _F5TTS(F5TTS):
    def __init__(
        self,
        yaml_path: str,            # 配置文件的绝对路径（原 `model` 参数被替换）
        ckpt_file: str,            # 模型权重的绝对路径
        vocab_file: str,           # 词汇表的绝对路径
        ode_method: str = "euler",
        use_ema: bool = True,
        vocoder_local_path: str = None,
        device: str = None,
        hf_cache_dir: str = None,
    ):
        model_cfg = OmegaConf.load(yaml_path)
        model_cls = get_class(f"f5_tts.model.{model_cfg.model.backbone}")
        model_arc = model_cfg.model.arch

        self.mel_spec_type = model_cfg.model.mel_spec.mel_spec_type
        self.target_sample_rate = model_cfg.model.mel_spec.target_sample_rate

        self.ode_method = ode_method
        self.use_ema = use_ema

        self.device = device

        # 5. 加载声码器（Vocoder）
        self.vocoder = load_vocoder(
            self.mel_spec_type,
            vocoder_local_path is not None,
            vocoder_local_path,
            self.device,
            hf_cache_dir,
        )

        # 6. 加载主模型
        self.ema_model = load_model(
            model_cls,
            model_arc,
            ckpt_file,
            self.mel_spec_type,
            vocab_file,
            self.ode_method,
            self.use_ema,
            self.device,
        )




def f5tts_fun(
        queue_tts_file=None,# 配音数据存在 json文件下，根据文件路径获取
        language='zh',#语言
        logs_file=None,
        speed=1.0,
        is_cuda=False,
        device_index=0 # gpu索引
)->Tuple[bool,Union[str,None]]:
    from videotrans.util.help_role import get_f5tts_role
    from videotrans.util.help_misc import vail_file
    import random  
    queue_tts=json.loads(Path(queue_tts_file).read_text(encoding='utf-8'))
    seed=random.randint(0, 65536)
    cfg=json.loads(Path(f'{ROOT_DIR}/videotrans/voicejson/f5ttscfg.json').read_text(encoding='utf-8'))
    cfg=cfg.get(language)
    if not cfg:
        return False,f"[F5-TTS]{tr('may not support')}{tr(language)}"
    
    local_dir=f'{ROOT_DIR}/models/models--'+cfg['repid'].replace('/','--')
    f5tts = _F5TTS(
        yaml_path=f"{ROOT_DIR}/videotrans/voicejson/{cfg['config']}",
        ckpt_file=f'{local_dir}/{cfg["model_name"]}',
        vocab_file=f'{local_dir}/{cfg["vocab_name"]}',
        vocoder_local_path=f'{ROOT_DIR}/models/models--charactr--vocos-mel-24khz',
        device=f'cuda:{device_index}' if is_cuda else 'cpu'
    )

    logger.debug(f'F5-TTS 本地内置渠道使用 {cfg["model_name"]} 模型,{is_cuda=}')
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
            output_filename=it.get('filename','')+"-24k.wav"
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
    
            wav, sr, spec = f5tts.infer(
                    ref_file=wavfile,
                    ref_text=ref_text,
                    gen_text=it['text'],
                    file_wave=output_filename,
                    seed=seed,
                    remove_silence=False,                    
                    speed=speed
            )
            if not vail_file(output_filename):
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
