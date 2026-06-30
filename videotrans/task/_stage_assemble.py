import glob
import os
import platform
import shutil
import subprocess
import sys
import time
import threading
from pathlib import Path

from videotrans import translator
from videotrans.configure.config import tr, app_cfg, settings, logger
from videotrans.configure.excepts import VideoTransError, FFmpegError
from videotrans.util.help_ffmpeg import get_video_codec, get_audio_time, runffmpeg, get_video_duration
from videotrans.util.help_misc import vail_file, read_last_n_lines, is_novoice_mp4


class AssembleMixin:

    def assembling(self) -> None:
        _st=time.time()
        if self._exit() or self.is_audio_trans or self.cfg.app_mode == 'tiqu' or not self.should_hebing:
            return
        self.precent = self.precent + 3 if self.precent < 95 else self.precent
        self.signal(text=tr('kaishihebing'))
        self._join_video_audio_srt()
        logger.debug(f'[音频+字幕+画面合成阶段结束耗时]:{time.time()-_st}s')

    def task_done(self) -> None:
        if self._exit(): return
        self.precent = max(99, self.precent)

        if self.cfg.app_mode == 'tiqu':
            try:
                Path(f"{self.cfg.target_dir}/{self.cfg.source_language_code}.srt").unlink(
                    missing_ok=True)
                Path(f"{self.cfg.target_dir}/{self.cfg.target_language_code}.srt").unlink(
                    missing_ok=True)
            except OSError:
                logger.warning('仅提取模式时，清理中间文件失败，跳过')
            return self.set_end(True)

        if self.is_audio_trans and vail_file(self.cfg.target_wav):
            try:
                shutil.copy2(self.cfg.target_wav,
                             f"{self.cfg.target_dir}/{self.cfg.target_language_code}-{self.cfg.noextname}.wav")
            except shutil.SameFileError:
                pass

        try:
            if self.cfg.only_out_mp4:
                shutil.move(self.cfg.targetdir_mp4, Path(self.cfg.target_dir).parent / Path(self.cfg.targetdir_mp4).name)
                shutil.rmtree(self.cfg.target_dir, ignore_errors=True)
        except OSError as e:
            logger.exception(f'仅输出mp4时清理临时文件移动视频位置出错，跳过 {e}', exc_info=True)

        self.set_end(True)
        logger.debug(f'[{self.cfg.name}视频翻译任务结束，总耗时]:{time.time()-self.cost_duration}s')

    def _video_extend(self, duration_ms=1000):
        sec = duration_ms / 1000.0
        final_video_path = Path(f'{self.cfg.cache_folder}/final_video_with_freeze_lastend.mp4').as_posix()

        cmd = ['-y', '-i', os.path.basename(self.cfg.novoice_mp4),
               '-vf', f'tpad=stop_mode=clone:stop_duration={sec:.3f}',
               '-c:v', 'libx264',
               '-crf', f'{settings.get("crf", 23)}',
               '-preset', settings.get('preset', 'veryfast'),
               '-an', 'final_video_with_freeze_lastend.mp4'
        ]
        try:
            runffmpeg(cmd, force_cpu=True, cmd_dir=self.cfg.cache_folder)
            if Path(final_video_path).exists():
                shutil.copy2(final_video_path, self.cfg.novoice_mp4)
                logger.debug(f"视频定格应延长{duration_ms}ms，实际向上取整秒延长{sec}s,操作成功。")
        except Exception as e:
            logger.exception(f"视频定格延长操作失败,跳过 {e}", exc_info=True)

    def _join_video_audio_srt(self) -> None:
        if self._exit() or not self.should_hebing:
            return

        is_novoice_mp4(self.cfg.novoice_mp4, self.uuid)
        if not Path(self.cfg.novoice_mp4).exists():
            raise VideoTransError(f'{self.cfg.novoice_mp4} 不存在')

        if self.should_dubbing and not vail_file(self.cfg.target_wav):
            raise VideoTransError(f"{tr('Dubbing')}{tr('anerror')}:{self.cfg.target_wav}")

        self.precent = min(max(90, self.precent), 98)

        target_m4a = self.cfg.cache_folder + "/will_embed.m4a"
        output_source_output = True
        duration_ms = int(get_video_duration(self.cfg.novoice_mp4))
        if not self.should_dubbing:
            self._get_origin_audio(target_m4a,duration_ms)
        else:
            output_source_output = False
            cmd = [
                "-y",
                "-i",
                self.cfg.name,
                "-vn",
                "-b:a", "128k",
                "-c:a",
                "aac",
                self.cfg.source_wav_output
            ]

            def _output():
                nonlocal output_source_output
                try:
                    runffmpeg(cmd)
                except Exception as e:
                    logger.exception(f'单独输出原始视频中音频文件到目标文件夹失败，跳过{e}', exc_info=True)
                finally:
                    output_source_output = True
            threading.Thread(target=_output, daemon=True).start()

            self._back_music()
            self._separate()

            audio_ms = get_audio_time(self.cfg.target_wav)
            _cmd=[
                "-y",
                "-i",
                os.path.basename(self.cfg.target_wav)
            ]
            v_a_offset=duration_ms-audio_ms
            if v_a_offset>100:
                logger.debug(f'视频时长{duration_ms}ms-音频时长{audio_ms}ms={v_a_offset}ms,需延长音频')
                _cmd.extend(['-af', f'apad=pad_dur={v_a_offset/1000.0}'])
            _cmd.extend([
                "-ac", "2", "-b:a", "128k", "-c:a", "aac",
                os.path.basename(target_m4a)
            ])
            runffmpeg(_cmd, cmd_dir=self.cfg.cache_folder)

        shutil.copy2(target_m4a, self.cfg.target_wav_output)
        self.precent = min(max(95, self.precent), 98)
        _video_output_ext = settings.get('out_video_ext', '.mp4')
        subtitles_file, subtitle_langcode = None, None
        if self.cfg.subtitle_type > 0:
            subtitles_file, subtitle_langcode = self._process_subtitles()

        if _video_output_ext!='.mp4':
            subtitle_langcode=translator.get_mkv_code(subtitle_langcode)

        audio_ms = get_audio_time(target_m4a)
        a_v_offset=audio_ms-duration_ms

        is_copy_mode = str(self.video_codec_num) == '264'
        is_lossless=self.is_copy_video and is_copy_mode and not self.cfg.video_autorate and self.cfg.subtitle_type not in [1, 3]
        if is_lossless:
            logger.debug(f'当前原始视频是标准264,输出也是264，未视频慢速，未嵌入硬字幕，放弃视频末尾处理，实现无损输出。音频时长-视频时长={a_v_offset}ms'+('，\n音频时长大于视频时长{a_v_offset}ms，理论上视频末尾应定格等待音频播放完毕，但不同播放器可能有不同处理方式，如音频截断，视频末尾黑屏等' if a_v_offset>0 else ''))

        elif a_v_offset > 500:
            try:
                self._video_extend(a_v_offset)
            except Exception as e:
                logger.exception(f'定格视频最后一帧时失败，跳过 {e}', exc_info=True)

        tmp_target_mp4 = self.cfg.cache_folder + f"/laste_target{_video_output_ext}"
        self.signal(text=tr("Video + Subtitles + Dubbing in merge"))

        try:
            protxt = self.cfg.cache_folder + f"/compose{time.time()}.txt"
            protxt_basename = os.path.basename(protxt)
            threading.Thread(target=self._hebing_pro, args=(protxt,), daemon=True).start()

            novoice_mp4_basename = os.path.basename(self.cfg.novoice_mp4)
            target_m4a_basename = os.path.basename(target_m4a)
            tmp_target_mp4_basename = os.path.basename(tmp_target_mp4)

            if not app_cfg.video_codec:
                app_cfg.video_codec = get_video_codec()

            cmd0 = [
                "-y",
                "-progress",
                protxt_basename
            ]

            cmd1 = [
                "-i",
                novoice_mp4_basename,
                "-i",
                target_m4a_basename
            ]
            enc_qua = ['-crf', f'{settings.get("crf", 23)}', '-preset', settings.get('preset', 'medium')]

            fps_mode=None
            if settings.get('fps_mode')=='cfr':
                fps_mode=["-r",f"{self.video_info['video_fps']}","-fps_mode","cfr"]
            elif self.cfg.video_autorate:
                fps_mode=["-fps_mode","vfr"]
            if self.cfg.subtitle_type not in [1, 3]:
                if self.cfg.subtitle_type in [2, 4]:
                    cmd1.extend(["-i", subtitles_file])
                cmd1.extend([
                    '-map',
                    '0:v',
                    '-map',
                    '1:a'
                ])
                if self.cfg.subtitle_type in [2, 4]:
                    cmd1.extend(['-map', '2:s'])

                cmd1.extend([
                    "-c:v",
                    "copy"  if is_copy_mode else f"libx{self.video_codec_num}",
                    "-c:a",
                    "copy",
                ])
                if self.cfg.subtitle_type in [2, 4]:
                    cmd1.extend([
                        "-c:s",
                        "mov_text" if _video_output_ext == '.mp4' else 'srt',
                        "-metadata:s:s:0",
                        f"language={subtitle_langcode}"
                    ])

                cmd2 = [
                    "-movflags",
                    "+faststart",
                ]
                if fps_mode:
                    cmd2.extend(fps_mode)

                cmd2.extend(['-shortest',tmp_target_mp4_basename])
                if is_copy_mode:
                    logger.debug(f'[最终视频合成]copy模式，无需重新编码:\n{cmd0 + cmd1 + cmd2}')
                    runffmpeg(cmd0 + cmd1 + cmd2, cmd_dir=self.cfg.cache_folder, force_cpu=True)
                elif app_cfg.video_codec.startswith('libx') or settings.get('force_lib'):
                    logger.debug(f'[最终视频合成]不支持硬件编码或指定了强制软编解码:\n{cmd0 + cmd1 + cmd2}')
                    runffmpeg(cmd0 + cmd1 + enc_qua + cmd2, cmd_dir=self.cfg.cache_folder, force_cpu=True)
                else:
                    hw_decode_args, _, vcodec, enc_args = self._get_hard_cfg()
                    cmd1[cmd1.index('-c:v') + 1] = vcodec
                    try:
                        self._subprocess(cmd0 + hw_decode_args + cmd1 + enc_args + cmd2)
                    except Exception as e:
                        cmd1[cmd1.index('-c:v') + 1] = f'libx{self.video_codec_num}'
                        logger.exception(f'硬件处理视频合成失败，回退软编 {e}', exc_info=True)
                        runffmpeg(cmd0 + cmd1 + enc_qua + cmd2, cmd_dir=self.cfg.cache_folder, force_cpu=True)

            else:
                cmd1.append('-filter_complex')
                subtitle_filter = [f"[0:v]subtitles=filename='{subtitles_file}'[v_out]"]
                cmd2 = [
                    "-map",
                    "[v_out]",
                    "-map",
                    "1:a",
                    "-c:v",
                    f'libx{self.video_codec_num}',
                    '-c:a',
                    'copy',
                ]
                cmd3 = ["-movflags", "+faststart"]

                if fps_mode:
                    cmd3.extend(fps_mode)
                cmd3.extend(['-shortest', tmp_target_mp4_basename])
                if app_cfg.video_codec.startswith('libx') or settings.get('force_lib'):
                    logger.debug(f'[最终视频合成]不支持硬件编解码或指定了强制软编解码:\n{cmd0 + cmd1 + cmd2}')
                    runffmpeg(cmd0 + cmd1 + subtitle_filter + cmd2 + enc_qua + cmd3,
                                    cmd_dir=self.cfg.cache_folder, force_cpu=True)
                else:
                    try:
                        hw_decode_args, vf_string, vcodec, enc_args = self._get_hard_cfg(subtitles_file)
                        cmd2[cmd2.index('-c:v') + 1] = vcodec
                        self._subprocess(cmd0 + hw_decode_args + cmd1 + [vf_string] + cmd2 + enc_args + cmd3)
                    except Exception as e:
                        cmd2[cmd2.index('-c:v') + 1] = f'libx{self.video_codec_num}'
                        logger.exception(f'硬件处理视频合成失败，回退软编 {e}', exc_info=True)
                        runffmpeg(cmd0 + cmd1 + subtitle_filter + cmd2 + enc_qua + cmd3,
                                        cmd_dir=self.cfg.cache_folder, force_cpu=True)
        except Exception as e:
            raise VideoTransError(tr('Error in embedding the final step of the subtitle dubbing')+str(e)) from e

        if Path(tmp_target_mp4).exists():
            try:
                self.cfg.targetdir_mp4=self.cfg.targetdir_mp4[:-4]+_video_output_ext
                shutil.copy2(tmp_target_mp4, self.cfg.targetdir_mp4)
            except Exception:
                try:
                    shutil.copy2(tmp_target_mp4, f'{self.cfg.target_dir}/0{_video_output_ext}')
                except Exception as e:
                    logger.exception(f'再次复制到目标文件夹内 0{_video_output_ext}也失败 {e}', exc_info=True)
                    raise VideoTransError(tr('Translation successful but transfer failed.', tmp_target_mp4)) from e

        while output_source_output is not True:
            if app_cfg.exit_soft:return
            time.sleep(1)
        return

    def _get_origin_audio(self, output,duration_ms=0):
        if self.video_info.get('streams_audio', 0) == 0:
            return
        cmd = [
            "-y",
            "-i",
            self.cfg.name,
            "-vn"
        ]
        v_a_offset=int(self.video_info['time'])-duration_ms
        if duration_ms>0 and v_a_offset>100:
            cmd.extend(['-af', f'apad=pad_dur={v_a_offset/1000.0}'])

        cmd.extend(['-c:a', 'aac', '-b:a', '128k',output])
        return runffmpeg(cmd)

    def _hebing_pro(self, protxt) -> None:
        while 1:
            if app_cfg.exit_soft or self.hasend or self.uuid in app_cfg.stoped_uuid_set: return
            content = read_last_n_lines(protxt)
            if not content:
                time.sleep(0.5)
                continue

            if content[-1] == 'progress=end':
                return
            idx = len(content) - 1
            end_time = "00:00:00"
            while idx > 0:
                if content[idx].startswith('out_time='):
                    end_time = content[idx].split('=')[1].strip()
                    break
                idx -= 1
            self.signal(text=tr('kaishihebing') + f' {end_time}')
            time.sleep(0.5)

    def _get_hard_cfg(self, subtitles_file=None, codec=None):
        os_name = platform.system()
        if not app_cfg.video_codec:
            app_cfg.video_codec = get_video_codec()
        hw_type = app_cfg.video_codec
        logger.debug(f'原始{hw_type=}')

        if '_' in hw_type:
            _hw_type_list = hw_type.lower().split('_')
            if _hw_type_list[0] == 'vaapi':
                hw_type = 'vaapi'
            else:
                hw_type = _hw_type_list[1]

        logger.debug(f'整理后{hw_type=}')

        codec = f'{self.video_codec_num}' if not codec else codec
        vcodec = f"libx{codec}"
        _crf = f'{settings.get("crf", 23)}'

        global_args = []
        vf_string = f"[0:v]subtitles=filename='{subtitles_file}'[v_out]"

        _preset = settings.get('preset', 'medium')
        if 'fast' in _preset:
            _preset = 'fast'
        elif 'slow' in _preset:
            _preset = 'slow'

        if _preset not in ['fast', 'slow', 'medium']:
            _preset = 'medium'
        enc_args = ['-crf', _crf, '-preset', _preset]

        PRESET_MAP = {
            'nvenc': {'fast': 'p2', 'medium': 'p4', 'slow': 'p7'},
            'qsv': {'fast': 'fast', 'medium': 'medium', 'slow': 'slow'},
            'amf': {'fast': 'speed', 'medium': 'balanced', 'slow': 'quality'},
            'vaapi': {'fast': 'fast', 'medium': 'medium', 'slow': 'slow'},
            'videotoolbox': None
        }

        if hw_type in ['nvenc']:
            vcodec = "h264_nvenc" if codec == '264' else "hevc_nvenc"
            enc_args = ['-cq', _crf, '-preset', PRESET_MAP.get('nvenc').get(_preset, 'p4')]
            if settings.get('hw_decode'):
                global_args = ['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda']
                vf_string = f"[0:v]hwdownload,format=nv12,subtitles=filename='{subtitles_file}',hwupload_cuda[v_out]"
            else:
                vf_string = f"[0:v]subtitles=filename='{subtitles_file}'[v_out]"

            return global_args, vf_string, vcodec, enc_args
        if hw_type in ['videotoolbox']:
            vcodec = "h264_videotoolbox" if codec == '264' else "hevc_videotoolbox"
            quality = int(100 - (int(_crf) * 1.4))
            enc_args = ['-q:v', f'{int(max(1, min(quality, 100)))}']
            return global_args, vf_string, vcodec, enc_args

        if hw_type in ['qsv', 'amf', 'vaapi']:
            if os_name == 'Linux':
                devices = glob.glob('/dev/dri/renderD*')
                device = devices[0] if devices else '/dev/dri/renderD128'
                if settings.get('hw_decode'):
                    global_args = ['-hwaccel', 'vaapi', '-hwaccel_device', device, '-hwaccel_output_format', 'vaapi']
                    vf_string = f"[0:v]hwdownload,format=nv12,subtitles=filename='{subtitles_file}',format=nv12,hwupload[v_out]"
                else:
                    global_args = [
                        '-init_hw_device', f'vaapi=vaapi:{device}'
                    ]
                    vf_string = f"[0:v]subtitles=filename='{subtitles_file}',format=nv12,hwupload[v_out]"
                vcodec = "h264_vaapi" if codec == '264' else "hevc_vaapi"
                enc_args = ['-qp', _crf, '-preset', PRESET_MAP.get('vaapi').get(_preset, 'medium')]
                return global_args, vf_string, vcodec, enc_args

            if hw_type in ['qsv']:
                vcodec = "h264_qsv" if codec == '264' else "hevc_qsv"
                enc_args = ['-global_quality', _crf, '-preset', PRESET_MAP.get('qsv').get(_preset, 'medium')]
            else:
                vcodec = "h264_amf" if codec == '264' else "hevc_amf"
                enc_args = ['-rc', 'cqp', '-qp_p', _crf, '-qp_i', _crf, '-quality',
                            PRESET_MAP.get('amf').get(_preset, 'balanced')]
            return global_args, vf_string, vcodec, enc_args

        return global_args, vf_string, vcodec, enc_args

    def _subprocess(self, cmd):
        logger.debug(f'[尝试硬件编解码执行命令]\n{" ".join(cmd)}\n')
        try:
            if app_cfg.exit_soft: return
            cmd = ["ffmpeg", '-nostdin'] + cmd
            subprocess.run(
                cmd,
                encoding="utf-8",
                errors='ignore',
                check=True,
                text=True,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                cwd=self.cfg.cache_folder
            )
            return True
        except subprocess.CalledProcessError as e:
            raise FFmpegError(f"尝试使用硬件执行命令出错[CalledProcessError]:{e.stderr}\n{e.stdout},{e}") from e
