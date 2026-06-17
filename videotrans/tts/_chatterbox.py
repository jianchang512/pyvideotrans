from dataclasses import dataclass
from pathlib import Path
from videotrans.configure.config import params, logger, app_cfg, ROOT_DIR
from videotrans.configure.excepts import DubbingSrtError
from videotrans.tts._base import BaseTTS
from videotrans.util import tools
from videotrans.util.gpus import mps_or_cpu

try:
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS as ChatterboxTTS
except ImportError:
    logger.critical('please run  uv sync --extra chatterbox ')

import soundfile as sf


@dataclass
class ChatterBoxTTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        self.roledict = tools.get_chatterbox_role()

    def _download(self):
        if not Path(f'{ROOT_DIR}/models/chatterbox/ve.pt').exists():
            tools.check_and_down_hf("", 'resembleAI/chatterbox', f'{ROOT_DIR}/models/chatterbox',
                                    callback=self._process_callback,
                                    allow_list=['ve.pt', 's3gen.pt', 'conds.pt', 't3_cfg.pt',
                                                't3_mtl23ls_v2.safetensors', 'Cangjie5_TC.json',
                                                'grapheme_mtl_merged_expanded_v1.json', 'mtl_tokenizer.json',
                                                'tokenizer.json'])
        return True

    def _exec(self):
        model = ChatterboxTTS.from_local(f'{ROOT_DIR}/models/chatterbox',
                                         device='cuda' if self.is_cuda else mps_or_cpu())

        ok, err = 0, 0
        _except = None
        cfg_weight = float(params.get("chatterbox_cfg_weight", '0.5'))
        exaggeration = float(params.get("chatterbox_exaggeration", '0.5'))
        lang = self.language.split('-')[0]
        for i,item in enumerate(self.queue_tts):
            if app_cfg.exit_soft: return
            ref_wav = None
            try:
                ref_wav, _ = self.get_ref_wav(item)
            except Exception:
                logger.warn('无参考音频，使用内置音色')
            try:
                self.signal(text=f'starting {i}/{self.len}')
                wav_tensor = model.generate(item['text'], exaggeration=exaggeration, cfg_weight=cfg_weight,
                                            language_id=lang, audio_prompt_path=ref_wav)
                wav_tensor = wav_tensor.detach().cpu()
                if wav_tensor.ndim == 2:
                    wav_np = wav_tensor.transpose(0, 1).numpy()
                else:
                    wav_np = wav_tensor.numpy()
                # 写入 WAV 格式到内存
                sf.write(item['filename'] + "-24k.wav", wav_np, model.sr, format='wav')
                if not tools.vail_file(item['filename'] + '-24k.wav'):
                    err += 1
                    continue
                ok += 1
                self.convert_to_wav(item['filename'] + '-24k.wav', item['filename'])
                self.signal(text=f"Dubbinged {i}/{self.len}")
            except Exception as e:
                _except = e
                logger.exception(f'chatterbox dubbing error:{e}', exc_info=True)
                err += 1

        try:
            del model
        except Exception:
            pass
        if ok == 0:
            raise _except if _except else DubbingSrtError('ChatterBox-TTS dubbing error')

        msg = "dubbing ended"
        if err > 0 and ok > 0:
            msg = f'[{err}] errors, {ok} succeed'

        self.signal(text=msg)
        logger.debug(f'ChatterBox 配音结束：{msg}')
