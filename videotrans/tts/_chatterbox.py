import json
import time
from dataclasses import dataclass
from pathlib import Path

from videotrans.configure._paths import REDUBB_STATUS_FILE, REDUBB_QUEUE_FILE
from videotrans.configure.config import params, logger, app_cfg, ROOT_DIR
from videotrans.configure.excepts import DubbingSrtError
from videotrans.tts._base import BaseTTS
from videotrans.util.help_role import get_chatterbox_role
from videotrans.util.gpus import mps_or_cpu
import soundfile as sf
from videotrans.util.help_misc import vail_file, is_connect_hf


@dataclass
class ChatterBoxTTS(BaseTTS):
    def __post_init__(self):
        super().__post_init__()
        self.roledict = get_chatterbox_role()
        self.local_dir=f'{ROOT_DIR}/models/models--resembleAI--chatterbox'

    def _download(self):
        if Path(f'{self.local_dir}/ve.pt').exists():
            return True
        from videotrans.util.help_down import check_and_down_hf,check_and_down_ms
        check_and_down_hf("", 'resembleAI/chatterbox', self.local_dir,
                                callback=self._process_callback,
                                allow_list=["ve.pt","t3_mtl23ls_v3.safetensors","t3_mtl23ls_v2.safetensors","s3gen.pt", "grapheme_mtl_merged_expanded_v1.json", "conds.pt", "Cangjie5_TC.json"])
        return True

    def _exec(self):
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS

        model = ChatterboxMultilingualTTS.from_local(self.local_dir,
                                         device='cuda' if self.is_cuda else mps_or_cpu(),
                                         t3_model="v3")


        ok, err = 0, 0
        _except = None
        cfg_weight = float(params.get("chatterbox_cfg_weight", '0.5'))
        exaggeration = float(params.get("chatterbox_exaggeration", '0.5'))
        lang = self.language.split('-')[0]
        queue_tts=self.queue_tts
        # 循环，用于轮询重新配音数据，非重新配音时，第一轮直接返回
        while 1:
            if self.is_redubb and Path(REDUBB_STATUS_FILE).exists():
                return True
            if self.is_redubb:
                try:
                    queue_tts=json.loads(Path(REDUBB_QUEUE_FILE).read_text(encoding='utf-8'))
                except (OSError,json.JSONDecodeError) as e:
                    logger.exception(f'supertonic-3: {e}',exc_info=True)
                    raise


            for i,item in enumerate(queue_tts):
                if app_cfg.exit_soft or (self.is_redubb and Path(REDUBB_STATUS_FILE).exists()):
                    return True
                if vail_file(item['filename']):
                    continue
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
                    if not vail_file(item['filename'] + '-24k.wav'):
                        err += 1
                        continue
                    ok += 1
                    self.convert_to_wav(item['filename'] + '-24k.wav', item['filename'])
                    self.signal(text=f"Dubbinged {i}/{self.len}")
                except Exception as e:
                    _except = e
                    logger.exception(f'chatterbox dubbing error:{e}', exc_info=True)
                    err += 1
            if self.is_redubb:
                time.sleep(0.5)
                continue
            break

        if ok == 0:
            raise _except if _except else DubbingSrtError('ChatterBox-TTS dubbing error')

        msg = "dubbing ended"
        if err > 0 and ok > 0:
            msg = f'[{err}] errors, {ok} succeed'

        self.signal(text=msg)
        logger.debug(f'ChatterBox 配音结束：{msg}')
