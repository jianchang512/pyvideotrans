import json
import os
import shutil
import time
from pathlib import Path

from videotrans.configure.config import tr, ROOT_DIR, settings, logger
from videotrans.configure.contants import BUILTINT_URL_MS, BUILTINT_URL_HF
from videotrans.util.help_misc import is_connect_hf


class DiarizMixin:

    def diariz(self):
        _st=time.time()
        # 只要 do_diarize 是 False,无论是否选中都不分离说话人
        if self._exit() or not self.should_dubbing or not self.do_diarize or not self.cfg.enable_diariz or self.max_speakers == 1 or Path(
                self.cfg.cache_folder + "/speaker.json").exists():
            return
        speaker_type = settings.get('speaker_type', 'built')
        hf_token = settings.get('hf_token')
        if speaker_type == 'built' and self.cfg.detect_language.split('-')[0] not in ['zh', 'en']:
            logger.error(f'当前选择 built 说话人分离模型，但不支持当前语言:{self.cfg.detect_language}')
            return
        if speaker_type in ['pyannote', 'reverb'] and not hf_token:
            logger.error(f'当前选择 pyannote 说话人分离模型，但未设置 huggingface.co 的token: {self.cfg.detect_language}')
            return
        from videotrans.util.help_down import down_file_from_hf, check_and_down_ms
        ishf=is_connect_hf()
        try:
            self.precent += 3
            title = tr('Speaker classification') + f':{speaker_type}'
            subtitles_file=f'{self.cfg.cache_folder}/diariz-{time.time()}.json'
            Path(subtitles_file).write_text(json.dumps([[it['start_time'], it['end_time']] for it in self.source_srt_list]),encoding='utf-8')
            kw = {
                "input_file": self.cfg.source_wav,
                "subtitles_file": subtitles_file,
                "speak_file":self.cfg.cache_folder + "/speaker.json",
                "num_speakers": self.max_speakers,
                "is_cuda": self.cfg.is_cuda
            }
            if speaker_type == 'built':
                down_file_from_hf(f'{ROOT_DIR}/models/onnx', BUILTINT_URL_MS if not ishf else BUILTINT_URL_HF, callback=self._process_callback)
                from videotrans.process.prepare_audio import built_speakers as _run_speakers
                del kw['is_cuda']
                kw['num_speakers'] = -1 if self.max_speakers < 1 else self.max_speakers
                kw['language'] = self.cfg.detect_language
            elif speaker_type == 'ali_CAM':
                check_and_down_ms(model_id='iic/speech_campplus_speaker-diarization_common',
                    local_dir=f"{ROOT_DIR}/models/speech_campplus_speaker-diarization_common",
                    callback=self._process_callback)
                from videotrans.process.prepare_audio import cam_speakers as _run_speakers
            elif speaker_type in ['pyannote','reverb']:
                from videotrans.process.prepare_audio import pyannote_speakers as _run_speakers
            else:
                logger.error(f'当前所选说话人分离模型不支持:{speaker_type=}')
                return
            if speaker_type in ['pyannote', 'reverb']:
                from videotrans.util.help_down import check_and_down_hf
                check_and_down_hf(
                    speaker_type, 
                    "pyannote/speaker-diarization-3.1", 
                    f'{ROOT_DIR}/models/models--pyannote--speaker-diarization-3.1', 
                    self._process_callback, 
                    None,
                    hf_token)
                check_and_down_hf(
                    speaker_type, 
                    "pyannote/segmentation-3.0", 
                    f'{ROOT_DIR}/models/models--pyannote--segmentation-3.0', 
                    self._process_callback, 
                    None,
                    hf_token)
                check_and_down_hf(
                    speaker_type, 
                    "pyannote/wespeaker-voxceleb-resnet34-LM", 
                    f'{ROOT_DIR}/models/models--pyannote--wespeaker-voxceleb-resnet34-LM', 
                    self._process_callback, 
                    None,
                    hf_token)

            _rs = self._new_process(callback=_run_speakers, title=title,
                                         is_cuda=self.cfg.is_cuda and speaker_type != 'built', kwargs=kw)

            if _rs:
                logger.debug('分离说话人成功完成')
                shutil.copy2(self.cfg.cache_folder + "/speaker.json", self.cfg.target_dir + "/speaker.json")
            else:
                logger.error('分离失败说话人失败')
            self.signal(text=tr('separating speakers end'))
        except Exception as e:
            logger.exception(f'说话人分离失败，跳过 {e}', exc_info=True)

        logger.debug(f'[说话人分离阶段结束耗时]:{time.time()-_st}s')
