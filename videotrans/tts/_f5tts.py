from dataclasses import dataclass,field
from typing import List, Dict, Union,Any
import sys,random,json
from videotrans.tts._base import BaseTTS
from videotrans.configure.config import ROOT_DIR, app_cfg, logger,tr
from videotrans.configure.excepts import DubbingSrtError
from videotrans.util import tools,gpus
from pathlib import Path
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



@dataclass
class F5TTSBuilt(BaseTTS):
    
    cfg:Dict[str, Any] = field(default_factory=dict, repr=False)
    localdir:str=None

    def __post_init__(self):
        super().__post_init__()
        self.roledict = tools.get_f5tts_role()
        self.device='cuda' if self.is_cuda else gpus.mps_or_cpu()
        language = self.language.split('-')[0]
        cfg=json.loads(Path(f'{ROOT_DIR}/videotrans/voicejson/f5ttscfg.json').read_text(encoding='utf-8'))
        if language not in cfg or not Path(f'{ROOT_DIR}/videotrans/voicejson/f5ttscfg/{language}.yaml').is_file():
            raise DubbingSrtError(f"[F5-TTS]{tr('may not support')}{tr(language)}")
        
        self.cfg=cfg[language]
        self.localdir=f'{ROOT_DIR}/models/models--'+self.cfg['repid'].replace('/','--')

    
    def _download(self):
        tools.check_and_down_hf(
                "",
                self.cfg['repid'],
                self.localdir,
                callback=self._process_callback,
                allow_list=[self.cfg['model_name'],self.cfg['vocab_name']]
        )
        
        if not Path(f'{ROOT_DIR}/models/models--charactr--vocos-mel-24khz/pytorch_model.bin').is_file():
            tools.check_and_down_hf("",
                'charactr/vocos-mel-24khz',
                f'{ROOT_DIR}/models/models--charactr--vocos-mel-24khz',
                callback=self._process_callback,
                allow_list=['pytorch_model.bin','config.yaml'])
        return True
    
    def _exec(self):
        _model_obj = {}
        ok, err = 0, 0
        _except = None
        
        seed=random.randint(0, 65536)
        speed = self.get_speed()
        f5tts = _F5TTS(
            yaml_path=f"{ROOT_DIR}/videotrans/voicejson/{self.cfg['config']}",
            ckpt_file=f'{self.localdir}/{self.cfg["model_name"]}',
            vocab_file=f'{self.localdir}/{self.cfg["vocab_name"]}',
            vocoder_local_path=f'{ROOT_DIR}/models/models--charactr--vocos-mel-24khz',
            device=self.device
        )
        
        for i,item in enumerate(self.queue_tts):
            if app_cfg.exit_soft: return
            try:
                self.signal(text=f"Dubbing {i+1}/{len(self.queue_tts)}")
                reference_audio_file,reference_text=self.get_ref_wav(item)
                if not Path(reference_audio_file).is_file():
                    raise ValueError(f"No reference audio_file in {ROOT_DIR}/f5-tts")
                output_filename=f'{item["filename"]}-24k.wav'
                wav, sr, spec = f5tts.infer(
                    ref_file=reference_audio_file,
                    ref_text=reference_text,
                    gen_text=item['text'],
                    file_wave=output_filename,
                    seed=seed,
                    remove_silence=False,                    
                    speed=speed
                )
                if not tools.vail_file(output_filename):
                    err += 1
                    continue
                ok += 1
                self.convert_to_wav(output_filename, item['filename'])
                self.signal(text=f"Dubbed {i+1}")
            except Exception as e:
                _except = e
                logger.exception(f'F5-TTS dubbing error:{e}', exc_info=True)
                err += 1

        try:
            del f5tts
        except Exception:
            pass
        if ok == 0:
            raise _except if _except else DubbingSrtError('[F5-TTS] dubbing error')

        msg = "dubbing ended"
        if err > 0 and ok > 0:
            msg = f'[{err}] errors, {ok} succeed'


        self.signal(text=msg)
        logger.debug(f'F5-TTS 配音结束：{msg}')


