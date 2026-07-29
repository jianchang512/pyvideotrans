import json
import time
from dataclasses import dataclass
from pathlib import Path

from videotrans.configure._paths import REDUBB_STATUS_FILE, REDUBB_QUEUE_FILE
from videotrans.configure.excepts import DubbingSrtError
from videotrans.configure.config import logger, ROOT_DIR, app_cfg
from videotrans.mosstts.args import Args
from videotrans.tts._base import BaseTTS
from videotrans.util.help_role import get_f5tts_role
from videotrans.mosstts.onnx_tts_runtime import    OnnxTtsRuntime
from videotrans.util.help_misc import vail_file


@dataclass
class MossTTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()
        self.roledict = get_f5tts_role()
        

    def _download(self):
        if Path(f'{ROOT_DIR}/models/MOSS-TTS-Nano-100M-ONNX/moss_tts_global_shared.data').exists() and Path(
                f'{ROOT_DIR}/models/MOSS-Audio-Tokenizer-Nano-ONNX/moss_audio_tokenizer_decode_shared.data').exists():
            return
        from videotrans.util.help_down import check_and_down_hf
        self.local_dir=f'{ROOT_DIR}/models/MOSS-TTS-Nano-100M-ONNX'
        check_and_down_hf("",
                                "OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX",
                                local_dir=self.local_dir,
                                callback=self._process_callback)
        self.local_dir=f"{ROOT_DIR}/models/MOSS-Audio-Tokenizer-Nano-ONNX"
        check_and_down_hf("",
                                "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX",
                                local_dir=self.local_dir,
                                callback=self._process_callback
                                )

    def _exec(self):
        ok, err = 0, 0
        _except = None
        args=Args()
        runtime = OnnxTtsRuntime(
            model_dir=args.model_dir,
            thread_count=args.cpu_threads,
            max_new_frames=args.max_new_frames,
            do_sample=bool(args.do_sample),
            sample_mode=args.sample_mode,
            execution_provider=args.execution_provider,
        )
        generation_defaults = runtime.manifest["generation_defaults"]
        generation_defaults["text_temperature"] = float(args.text_temperature)
        generation_defaults["text_top_p"] = float(args.text_top_p)
        generation_defaults["text_top_k"] = int(args.text_top_k)
        generation_defaults["audio_temperature"] = float(args.audio_temperature)
        generation_defaults["audio_top_p"] = float(args.audio_top_p)
        generation_defaults["audio_top_k"] = int(args.audio_top_k)
        generation_defaults["audio_repetition_penalty"] = float(args.audio_repetition_penalty)

        enable_wetext = bool(args.enable_wetext_processing) and not bool(args.disable_wetext_processing)
        enable_normalize_tts_text = bool(args.enable_normalize_tts_text) and not bool(args.disable_normalize_tts_text)




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
                    return
                if vail_file(item['filename']):
                    ok+=1
                    continue
                try:
                    ref_wav,_=self.get_ref_wav(item)
                    runtime.synthesize(
                        text=item['text'],
                        voice=args.voice,
                        prompt_audio_path=ref_wav,
                        output_audio_path=item['filename']+"-raw.wav",
                        sample_mode=args.sample_mode,
                        do_sample=bool(args.do_sample),
                        streaming=bool(args.realtime_streaming_decode),
                        max_new_frames=args.max_new_frames,
                        voice_clone_max_text_tokens=args.voice_clone_max_text_tokens,
                        enable_wetext=enable_wetext,
                        enable_normalize_tts_text=enable_normalize_tts_text,
                        seed=args.seed,
                    )
                    if not vail_file(item['filename']+'-raw.wav'):
                        err+=1
                        continue
                    self.convert_to_wav(item['filename'] + '-raw.wav', item['filename'])
                    ok+=1
                    self.signal(text=f"Dubbing {ok}/{self.len}")
                except Exception as e:
                    _except = e
                    logger.exception(f'vits dubbing error:{e}', exc_info=True)
                    err += 1

            if self.is_redubb:
                time.sleep(0.5)
                continue
            break

        if ok == 0:
            raise _except if _except else DubbingSrtError('Moss-TTS-Nano dubbing error')

        msg = "dubbing ended"
        if err > 0 and ok > 0:
            msg = f'[{err}] errors, {ok} succeed'


        self.signal(text=msg)
        logger.debug(f'MossTTS 配音结束：{msg}')
