import json
import shutil
import time
from pathlib import Path

from videotrans.configure.config import tr, ROOT_DIR, settings, logger


class DiarizMixin:

    def diariz(self):
        _st=time.time()
        if self._exit() or not self.cfg.enable_diariz or self.max_speakers == 1 or Path(
                self.cfg.cache_folder + "/speaker.json").exists():
            return
        speaker_type = settings.get('speaker_type', 'built')
        hf_token = settings.get('hf_token')
        if speaker_type == 'built' and self.cfg.detect_language[:2] not in ['zh', 'en']:
            logger.error(f'当前选择 built 说话人分离模型，但不支持当前语言:{self.cfg.detect_language}')
            return
        if speaker_type in ['pyannote', 'reverb'] and not hf_token:
            logger.error(f'当前选择 pyannote 说话人分离模型，但未设置 huggingface.co 的token: {self.cfg.detect_language}')
            return
        hf_endpoit = "https://huggingface.co"
        if speaker_type in ['pyannote', 'reverb']:
            try:
                import requests
                requests.head('https://huggingface.co', timeout=5)

            except Exception:
                logger.exception(f'当前选择 {speaker_type} 说话人分离模型，但无法连接到 https://huggingface.co,可能会失败', exc_info=True)
                hf_endpoit = "https://hf-mirror.com"
        from videotrans.util.help_down import down_file_from_ms, check_and_down_ms
        try:
            self.precent += 3
            title = tr(f'Begin separating the speakers') + f':{speaker_type}'
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
                down_file_from_ms(f'{ROOT_DIR}/models/onnx', [
                    "https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/onnx/seg_model.onnx",
                    "https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/onnx/nemo_en_titanet_small.onnx",
                    "https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/onnx/3dspeaker_speech_eres2net_large_sv_zh-cn_3dspeaker_16k.onnx"
                ], callback=self._process_callback)
                from videotrans.process.prepare_audio import built_speakers as _run_speakers
                del kw['is_cuda']
                kw['num_speakers'] = -1 if self.max_speakers < 1 else self.max_speakers
                kw['language'] = self.cfg.detect_language
            elif speaker_type == 'ali_CAM':
                check_and_down_ms(model_id='iic/speech_campplus_speaker-diarization_common',
                                        callback=self._process_callback)
                from videotrans.process.prepare_audio import cam_speakers as _run_speakers
            elif speaker_type == 'pyannote':
                from videotrans.process.prepare_audio import pyannote_speakers as _run_speakers
            elif speaker_type == 'reverb':
                from videotrans.process.prepare_audio import reverb_speakers as _run_speakers
            else:
                logger.error(f'当前所选说话人分离模型不支持:{speaker_type=}')
                return
            if speaker_type in ['pyannote', 'reverb']:
                self.signal(text='Downloading speakers models')
                from huggingface_hub import snapshot_download
                snapshot_download(
                    repo_id="pyannote/speaker-diarization-3.1" if speaker_type == 'pyannote' else "Revai/reverb-diarization-v1",
                    token=hf_token,
                    endpoint=hf_endpoit
                )

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
