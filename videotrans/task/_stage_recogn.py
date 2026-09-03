import json
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os

from videotrans.configure.config import tr, ROOT_DIR, settings, logger
from videotrans.configure.contants import DENOISE_URL_MS, PUNC_RESTORE_MS, DENOISE_URL_HF, PUNC_RESTORE_HF
from videotrans.configure.excepts import SpeechToTextError
from videotrans.recognition import run as run_recogn,  FASTER_WHISPER
from videotrans.translator._registry import get_name_index
from videotrans.translator._runner import get_model_transobj
from videotrans.util.help_ffmpeg import conver_to_16k, runffmpeg, cut_from_audio
from videotrans.util.help_misc import vail_file, is_connect_hf
from videotrans.util.help_srt import get_subtitle_from_srt, delete_punc


class RecognMixin:

    def recogn(self) -> None:
        _st=time.time()
        if self._exit(): return
        if not self.should_recogn: return
        self.precent += 3
        self.signal(text=tr("kaishishibie"))
        if vail_file(self.cfg.source_sub):
            self.source_srt_list = get_subtitle_from_srt(self.cfg.source_sub, is_file=True)
            if Path(self.cfg.target_dir + "/speaker.json").exists():
                shutil.copy2(self.cfg.target_dir + "/speaker.json", self.cfg.cache_folder + "/speaker.json")
            self._recogn_succeed()
            return

        if not vail_file(self.cfg.source_wav):
            raise SpeechToTextError(tr("Failed to separate audio, please check the log or retry"))
        # 未分离人声背景时才降噪，已分离则不再降噪
        if self.cfg.remove_noise and not self.cfg.is_separate:
            from videotrans.util.help_down import down_file_from_hf
            _remove_noise_wav = f"{self.cfg.cache_folder}/remove_noise.wav"
            if vail_file(_remove_noise_wav):
                self.cfg.source_wav = _remove_noise_wav
                self.clone_ref = _remove_noise_wav
                logger.debug(f'复用已存在的降噪缓存文件')
            else:
                title = tr("Starting to process speech noise reduction, which may take a long time, please be patient")
                kw = {
                    "input_file": self.cfg.source_wav if not self.cfg.vocal or not Path(self.cfg.vocal).exists() else self.cfg.vocal,
                    "output_file": _remove_noise_wav,
                    "is_cuda": self.cfg.is_cuda
                }
                try:
                    down_file_from_hf(f'{ROOT_DIR}/models/onnx', urls=DENOISE_URL_MS if not is_connect_hf() else DENOISE_URL_HF,
                                            callback=self._process_callback)
                    from videotrans.process.prepare_audio import remove_noise
                    _rs = self._new_process(callback=remove_noise, title=title, is_cuda=self.cfg.is_cuda, kwargs=kw)
                    if _rs:
                        self.clone_ref = _remove_noise_wav
                        self.cfg.source_wav = _remove_noise_wav
                    self.signal(text='remove noise end')
                except Exception as e:
                    logger.exception(f'降噪失败，跳过 {e}', exc_info=True)

        self.signal(text=tr("Speech Recognition to Word Processing"))
        raw_subtitles = run_recogn(
            recogn_type=self.cfg.recogn_type,
            uuid=self.uuid,
            model_name=self.cfg.model_name,
            audio_file=self.cfg.source_wav,
            detect_language=self.cfg.detect_language,
            cache_folder=self.cfg.cache_folder,
            is_cuda=self.cfg.is_cuda,
            subtitle_type=self.cfg.subtitle_type,
            max_speakers=self.max_speakers,
        )
        if self._exit(): return
        if not raw_subtitles:
            raise SpeechToTextError(self.cfg.basename + tr('recogn result is empty'))

        if self.cfg.app_mode=='tiqu' and not self.should_trans and self.cfg.fix_punc==2:
            logger.debug('仅提取不翻译模式下，移除所有标点')
            for it in raw_subtitles:
                it['text'] = delete_punc(it['text'])

        self._save_srt_target(raw_subtitles, self.cfg.source_sub)
        self.source_srt_list = raw_subtitles
        # 恢复标点
        if self.cfg.fix_punc==1:
            try:
                down_file_from_hf(f'{ROOT_DIR}/models/puntc', PUNC_RESTORE_MS if not is_connect_hf() else PUNC_RESTORE_HF, callback=self._process_callback)
                from videotrans.process.prepare_audio import fix_punc
                text_dict = {f'{it["line"]}': re.sub(r'[,.?!，。？！]', ' ', it["text"]) for it in self.source_srt_list}
                text_dict_file=f'{self.cfg.cache_folder}/text_dict_file_{time.time()}.json'
                Path(text_dict_file).write_text(json.dumps(text_dict),encoding="utf-8")
                kw = {"text_dict_file": text_dict_file, "is_cuda": self.cfg.is_cuda}
                _rs = self._new_process(callback=fix_punc, title=tr("Restoring punct"), is_cuda=self.cfg.is_cuda,
                                        kwargs=kw)
                if _rs:
                    text_dict_obj=json.loads(Path(text_dict_file).read_text(encoding='utf-8'))
                    for it in self.source_srt_list:
                        it['text'] = text_dict_obj.get(f'{it["line"]}', it['text'])
                        if self.cfg.detect_language.split('-')[0] == 'en':
                            it['text'] = it['text'].replace('，', ',').replace('。', '. ').replace('？', '?').replace('！','!')
                    self._save_srt_target(self.source_srt_list, self.cfg.source_sub)
                else:
                    logger.error('标点恢复出错了，跳过')
            except Exception as e:
                logger.exception(f'标点恢复失败，跳过 {e}', exc_info=True)

        self.signal(text=Path(self.cfg.source_sub).read_text(encoding='utf-8'), type='replace_subtitle')


        # LLM纠错
        if self.cfg.rephrase:
            self.source_srt_list=self._llmpost(self.source_srt_list)
        
        self._recogn_succeed()
        self.signal(text=tr('endtiquzimu'))
        logger.debug(f'[语音识别阶段结束耗时]:{time.time()-_st}s')

    def _recogn_succeed(self) -> None:
        self.precent += 5
        if self.cfg.app_mode == 'tiqu' and not self.should_trans:
            shutil.copy2(self.cfg.source_sub,  f"{self.cfg.target_dir}/{self.cfg.noextname}.srt")
        self.signal(text=tr('endtiquzimu'))

    # 二次识别固定使用 faster-whisper 渠道
    def recogn2pass(self) -> None:
        _st=time.time()
        if not self.should_recogn2 or self._exit():
            return
        if not vail_file(self.cfg.target_wav):
            logger.debug(f'跳过二次识别，因无配音音频文件')
            return

        self.precent += 3
        self.signal(text=tr("Secondary speech recognition of dubbing files"))

        shibie_audio = f'{self.cfg.cache_folder}/recogn2pass-{time.time()}.wav'
        outsrt_file = f'{self.cfg.cache_folder}/recogn2pass-{time.time()}.srt'
        try:
            conver_to_16k(self.cfg.target_wav, shibie_audio)
        except Exception as e:
            logger.exception(f'二次识别配音音频生成字幕时，预处理音频失败，静默跳过 {e}', exc_info=True)
            return

        if not vail_file(shibie_audio):
            logger.error(f'二次识别配音音频生成字幕时，预处理音频失败，静默跳过')
            return

        try:

            detect_language = self.cfg.target_language_code.split('-')[0]
            recogn_type = FASTER_WHISPER
            model_name = settings.get('model_for_recogn2','large-v3-turbo')
            logger.debug(f'二次识别：faster-whisper + {detect_language=} + {model_name=}')
            raw_subtitles = run_recogn(
                recogn_type=recogn_type,
                uuid=self.uuid,
                model_name=model_name,
                audio_file=shibie_audio,
                detect_language=detect_language,
                cache_folder=self.cfg.cache_folder,
                is_cuda=self.cfg.is_cuda,
                recogn2pass=True
            )
            if self._exit(): return
            if not raw_subtitles:
                logger.error('二次识别出错：' + tr('recogn result is empty'))
                return

            if self.cfg.rephrase:
                raw_subtitles=self._llmpost(raw_subtitles,'2')

            if self.cfg.fix_punc==2:
                logger.debug('二次识别后，移除所有标点')
                for it in raw_subtitles:
                    it['text']=delete_punc(it['text'])
            self._save_srt_target(raw_subtitles, outsrt_file)

            if not vail_file(outsrt_file):
                logger.error(f'二次识别配音文件失败，原因未知')
                return
            shutil.copy2(outsrt_file, self.cfg.target_sub)
            self.signal(text='STT 2 pass end')
            logger.debug('二次识别成功完成')
        except Exception as e:
            logger.exception(f'二次识别配音音频生成字幕时失败，静默跳过 {e}', exc_info=True)
            return
        logger.debug(f'[二次识别阶段结束耗时]:{time.time()-_st}s')



    def _create_ref_from_vocal(self):
        vocal = self.cfg.source_wav
        if self.clone_ref and Path(self.clone_ref).exists():
            vocal=self.clone_ref
        else:
            try:
                tmpfile = self.cfg.cache_folder + "/clone_ref_44100.wav"
                runffmpeg([
                    "-y",
                    "-i",
                    self.cfg.name,
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "44100",
                    "-c:a",
                    "pcm_s16le",
                    tmpfile
                ])
                vocal=tmpfile
            except Exception as e:
                logger.exception(f'克隆语音前分离出 44.1k 的原始音频失败',exc_info=True)

        logger.debug(f'语音克隆模式下，所用参考音频为:{vocal}')
        def _cutaudio_from_vocal(it):
            try:
                logger.debug(f"裁切对应片段为参考音频：{it['startraw']}->{it['endraw']}\n当前{it=}")
                cut_from_audio(
                    audio_file=vocal,
                    ss=it['startraw'],
                    to=it['endraw'],
                    out_file=it['ref_wav']
                )
            except Exception as e:
                logger.exception(f'裁切参考音频失败:{it=},{e}', exc_info=True)

        all_task = []
        with ThreadPoolExecutor(max_workers=min(8, len(self.queue_tts), os.cpu_count())) as pool:
            for item in self.queue_tts:
                if item.get('ref_wav'):
                    all_task.append(pool.submit(_cutaudio_from_vocal, item))
            if len(all_task) > 0:
                _ = [i.result() for i in all_task]
