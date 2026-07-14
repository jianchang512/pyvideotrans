import time,re,json,shutil
from pathlib import Path

from videotrans.configure.config import tr, app_cfg, settings, logger
from videotrans.configure.excepts import VideoTransError
from videotrans.task.simple_runnable_qt import run_in_threadpool
from videotrans.util.help_ffmpeg import get_video_info, runffmpeg
from videotrans.util.help_misc import vail_file
from videotrans.util.help_srt import get_srt_from_list,get_subtitle_from_srt

class PrepareMixin:

    def prepare(self) -> None:
        _st=time.time()
        if self._exit(): return
        self.signal(text=tr("Hold on a monment..."))
        Path(self.cfg.cache_folder).mkdir(parents=True, exist_ok=True)
        Path(self.cfg.target_dir).mkdir(parents=True, exist_ok=True)

        self._unlink_size0([self.cfg.source_sub, self.cfg.target_sub, self.cfg.targetdir_mp4])
        self.video_info = get_video_info(self.cfg.name)
        self.video_time = self.video_info['time']
        audio_stream_len = self.video_info.get('streams_audio', 0)

        if self.video_info.get('video_streams', 0) < 1 and not self.is_audio_trans and self.cfg.app_mode != 'tiqu':
            raise VideoTransError(
                tr('The video file {} does not contain valid video data and cannot be processed.', self.cfg.name))

        if audio_stream_len < 1 and not vail_file(self.cfg.source_sub):
            raise VideoTransError(
                tr('There is no valid audio in the file {} and it cannot be processed. Please play it manually to confirm that there is sound.',
                   self.cfg.name))

        if self.video_info['video_codec_name'] == 'h264' and self.video_info['color'] == 'yuv420p':
            self.is_copy_video = True

        if self.cfg.subtitles.strip():
            with open(self.cfg.source_sub, 'w', encoding="utf-8", errors="ignore") as f:
                txt = re.sub(r':\d+\.\d+', lambda m: m.group().replace('.', ','),
                             self.cfg.subtitles.strip(), flags=re.I | re.S)
                f.write(txt)
            self.should_recogn = False

        raw_vocal = f"{self.cfg.target_dir}/vocal.wav"
        if vail_file(raw_vocal):
            shutil.copy2(raw_vocal, self.cfg.vocal)

        raw_instrument = f"{self.cfg.target_dir}/instrument.wav"
        if vail_file(raw_instrument):
            shutil.copy2(raw_instrument, self.cfg.instrument)

        if not self.is_audio_trans and self.cfg.app_mode != 'tiqu':
            app_cfg.queue_novice[self.uuid] = 'ing'
            if not self.is_copy_video:
                self.signal(text=tr("Video needs transcoded and take a long time.."))
            run_in_threadpool(self._split_novoice_byraw)
        else:
            app_cfg.queue_novice[self.uuid] = 'end'

        if audio_stream_len > 0 and self.cfg.is_separate and (
                not vail_file(self.cfg.vocal) or not vail_file(self.cfg.instrument)):
            self.signal(text=tr('Separating background music'))
            try:
                self._split_audio_byraw(True)
            except Exception as e:
                logger.exception(f'分离人声背景声失败，跳过 {e}', exc_info=True)
            finally:
                if not vail_file(self.cfg.vocal) or not vail_file(self.cfg.instrument):
                    self.cfg.is_separate = self.should_separate = False

        if audio_stream_len > 0 and not vail_file(self.cfg.source_wav) and vail_file(self.cfg.vocal):
            cmd = [
                "-y",
                "-i",
                self.cfg.vocal,
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                self.cfg.source_wav
            ]
            try:
                logger.debug(f'存在单独的人声文件 vocal.wav, 使用此作为语音识别原始音频')
                runffmpeg(cmd)
            except Exception as e:
                logger.exception(f'将 人声文件 转为 16000 source_wav 时失败 {e}', exc_info=True)

        if audio_stream_len > 0 and not vail_file(self.cfg.source_wav):
            self._split_audio_byraw()
        if self.cfg.vocal and Path(self.cfg.vocal).exists():
            self.clone_ref = self.cfg.vocal
        # 从字幕中提取说话人 start
        # 如果存在原始字幕，并且字幕第一条开头存在说话人标识，提取出说话人
        if vail_file(self.cfg.source_sub):
            try:
                source_srt_list = get_subtitle_from_srt(self.cfg.source_sub, is_file=True)
                if source_srt_list:
                    spk_list=[]
                    for i,it in enumerate(source_srt_list):
                        groups=re.search(r'^\[\s*?(sp[a-zA-Z]+\s*?\d+)\s*?\]',it['text'].strip(),flags=re.I)
                        if not groups:
                            if i==0:
                                break
                            if i>0 and spk_list:
                                spk_list.append(spk_list[0])
                        else:
                            spk_list.append(groups.group(1))
                            # 从字幕中删掉说话人标识
                            it['text']=it['text'].replace(groups.group(0),'')
                    if spk_list:                            
                        Path(self.cfg.target_dir + "/speaker.json").write_text(json.dumps(spk_list), encoding='utf-8')
                        txt = get_srt_from_list(source_srt_list)
                        with open(self.cfg.source_sub, "w", encoding="utf-8", errors="ignore") as f:
                            f.write(txt)
            except Exception as e:
                logger.exception(f'从原始字幕中提取出说话人并删除标识后保存失败:{e}',exc_info=True)
        # 从字幕中提取说话人 end
            
        self.signal(text=tr('endfenliyinpin'))
        logger.debug(f'[预处理阶段结束耗时]:{time.time()-_st}s')

    def _split_novoice_byraw(self):
        import os
        from videotrans.configure.config import settings
        cmd = [
            "-y",
            "-fflags",
            "+genpts",
            "-i",
            self.cfg.name,
            "-an",
            "-c:v",
            "copy" if self.is_copy_video else f"libx264"
        ]
        _name = os.path.basename(self.cfg.novoice_mp4)
        enc_qua = [] if self.is_copy_video else ['-crf', '18']
        if self.is_copy_video or settings.get('force_lib'):
            return runffmpeg(cmd + enc_qua + [_name], noextname=self.uuid, cmd_dir=self.cfg.cache_folder)

        try:
            hw_decode_args, _, vcodec, enc_args = self._get_hard_cfg(codec="264")
            cmd = [
                "-y",
                "-fflags",
                "+genpts",
            ]
            cmd += hw_decode_args

            cmd += [
                "-i",
                self.cfg.name,
                "-an",
                "-c:v",
                vcodec,
                _name
            ]
            self._subprocess(cmd)
            app_cfg.queue_novice[self.uuid] = 'end'
        except Exception as e:
            logger.exception(f'硬件分离无声视频失败,尝试软分离 {e}', exc_info=True)
            return runffmpeg([
                "-y",
                "-fflags",
                "+genpts",
                "-i",
                self.cfg.name,
                "-an",
                "-c:v",
                "libx264",
                _name
            ], noextname=self.uuid, cmd_dir=self.cfg.cache_folder, force_cpu=True)

    def _split_audio_byraw(self, is_separate=False):
        cmd = [
            "-y",
            "-i",
            self.cfg.name,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            self.cfg.source_wav
        ]
        rs = runffmpeg(cmd)
        if not is_separate:
            return rs

        tmpfile = self.cfg.cache_folder + "/441000_ac2_raw.wav"
        runffmpeg([
            "-y",
            "-i",
            self.cfg.name,
            "-vn",
            "-ac",
            "2",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            tmpfile
        ])

        if vail_file(self.cfg.vocal) and vail_file(self.cfg.instrument):
            return
        from videotrans.configure.config import ROOT_DIR
        from videotrans.util.help_down import down_file_from_ms
        title = tr('Separating vocals and background music, which may take a longer time')
        uvr_models = settings.get('uvr_models')
        if uvr_models.startswith('spleeter'):
            down_file_from_ms(f'{ROOT_DIR}/models/onnx', [
                f"https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/onnx/vocals.fp16.onnx",
                f"https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/onnx/accompaniment.fp16.onnx"
            ], callback=self._process_callback)

        else:
            down_file_from_ms(f'{ROOT_DIR}/models/onnx', [
                f"https://www.modelscope.cn/models/himyworld/videotrans/resolve/master/onnx/{uvr_models}.onnx"
            ], callback=self._process_callback)
        from videotrans.process.prepare_audio import vocal_bgm
        kw = {"input_file": tmpfile, "vocal_file": self.cfg.vocal, "instr_file": self.cfg.instrument,
              "uvr_models": uvr_models}
        try:
            rs = self._new_process(callback=vocal_bgm, title=title, is_cuda=False, kwargs=kw)
            if rs and vail_file(self.cfg.vocal) and vail_file(self.cfg.instrument):
                cmd = [
                    "-y",
                    "-i",
                    self.cfg.vocal,
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    '-af',
                    "volume=1.5",
                    self.cfg.source_wav
                ]
                runffmpeg(cmd)
                shutil.copy2(self.cfg.vocal, f'{self.cfg.target_dir}/vocal.wav')
                shutil.copy2(self.cfg.instrument, f'{self.cfg.target_dir}/instrument.wav')
        except Exception as e:
            logger.exception(f'人声背景声分离失败，静默跳过 {e}', exc_info=True)
