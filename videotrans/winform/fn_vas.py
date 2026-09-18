# 视频 字幕 音频 合并
import glob
import platform
import subprocess
import sys

from videotrans.configure.excepts import FFmpegError
from videotrans.util._ffmpeg_hwcodec import get_video_codec
from videotrans.winform import get_win


def openwin():
    from videotrans.winform import get_cls
    from videotrans.task.taskcfg import SignMsg
    from videotrans.util._ffmpeg_audio import change_speed_rubberband
    from videotrans.util._ffmpeg_runner import runffmpeg
    from videotrans.util._ffprobe import get_audio_time, get_video_duration, get_video_info
    from videotrans.util._srt_ass import set_ass_font
    from videotrans.util._srt_parse import get_subtitle_from_srt
    from videotrans.util._srt_wrap import simple_wrap
    from videotrans.util.help_misc import show_error, read_last_n_lines
    from videotrans.configure import constants
    from PySide6.QtWidgets import QFileDialog
    import shutil, threading
    import os
    import time
    from pathlib import Path
    from PySide6.QtCore import QThread, Signal, QUrl, QTimer
    from PySide6.QtGui import QDesktopServices
    from videotrans.configure.config import tr, app_cfg, settings, params, logger, HOME_DIR
    from videotrans.configure import config

    RESULT_DIR = HOME_DIR + "/vas"
    STATE_DICT = {"stop": False}

    from videotrans.translator import LANGNAME_DICT, get_subtitle_code

    class CompThread(QThread):
        uito = Signal(object)

        def __init__(self, *, parent=None, video=None, audio=None, srt=None, saveraw=True, is_soft=False, language=None,
                     maxlen=30, audio_process=0, remain_hr=False):
            super().__init__(parent=parent)
            self.winobj = parent
            self.video = video
            self.audio = audio
            self.srt = srt
            self.saveraw = saveraw
            self.is_soft = is_soft
            self.language = language
            self.maxlen = maxlen
            self.remain_hr = remain_hr
            self.audio_process = audio_process
            self.file = f'{RESULT_DIR}/{Path(self.video).stem}-{int(time.time())}.mp4'
            self.video_info = get_video_info(self.video)
            self.video_time = get_video_duration(self.video)
            self.is_end = False

        def post(self, type='logs', text=''):
            self.uito.emit(SignMsg(**{"type": type, "text": text}))

        #
        def hebing_pro(self, protxt):
            timeout = 0
            while 1:
                if self.is_end:
                    return
                timeout += 1
                if timeout > 1200:
                    return
                content = read_last_n_lines(protxt)
                if not content:
                    time.sleep(1)
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
                self.post(type='jd', text=f'{end_time}')
                time.sleep(1)

        def _get_hard_cfg(self, subtitles_file):
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
            vcodec = f"libx264"
            _crf = f'{settings.get("crf", 23)}'

            global_args = []
            vf_string = f"[0:v]subtitles=filename='{subtitles_file}'[v_out]"

            _preset = settings.get('preset', 'fast')
            if 'fast' in _preset:
                _preset = 'fast'
            elif 'slow' in _preset:
                _preset = 'slow'

            if _preset not in ['fast', 'slow', 'medium']:
                _preset = 'fast'
            enc_args = ['-crf', _crf, '-preset', _preset]

            PRESET_MAP = {
                'nvenc': {'fast': 'p2', 'medium': 'p4', 'slow': 'p7'},
                'qsv': {'fast': 'fast', 'medium': 'medium', 'slow': 'slow'},
                'amf': {'fast': 'speed', 'medium': 'balanced', 'slow': 'quality'},
                'vaapi': {'fast': 'fast', 'medium': 'medium', 'slow': 'slow'},
                'videotoolbox': None
            }

            if hw_type in ['nvenc']:
                vcodec = "h264_nvenc"
                enc_args = ['-cq', _crf, '-preset', PRESET_MAP.get('nvenc').get(_preset, 'p4')]
                if settings.get('hw_decode'):
                    global_args = ['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda']
                    vf_string = f"[0:v]hwdownload,format=nv12,subtitles=filename='{subtitles_file}',hwupload_cuda[v_out]"
                else:
                    vf_string = f"[0:v]subtitles=filename='{subtitles_file}'[v_out]"

                return global_args, vf_string, vcodec, enc_args
            if hw_type in ['videotoolbox']:
                vcodec = "h264_videotoolbox"
                quality = int(100 - (int(_crf) * 1.4))
                enc_args = ['-q:v', f'{int(max(1, min(quality, 100)))}']
                return global_args, vf_string, vcodec, enc_args

            if hw_type in ['qsv', 'amf', 'vaapi']:
                if os_name == 'Linux':
                    devices = glob.glob('/dev/dri/renderD*')
                    device = devices[0] if devices else '/dev/dri/renderD128'
                    if settings.get('hw_decode'):
                        global_args = ['-hwaccel', 'vaapi', '-hwaccel_device', device, '-hwaccel_output_format',
                                       'vaapi']
                        vf_string = f"[0:v]hwdownload,format=nv12,subtitles=filename='{subtitles_file}',format=nv12,hwupload[v_out]"
                    else:
                        global_args = [
                            '-init_hw_device', f'vaapi=vaapi:{device}'
                        ]
                        vf_string = f"[0:v]subtitles=filename='{subtitles_file}',format=nv12,hwupload[v_out]"
                    vcodec = "h264_vaapi"
                    enc_args = ['-qp', _crf, '-preset', PRESET_MAP.get('vaapi').get(_preset, 'fast')]
                    return global_args, vf_string, vcodec, enc_args

                if hw_type in ['qsv']:
                    vcodec = "h264_qsv"
                    enc_args = ['-global_quality', _crf, '-preset', PRESET_MAP.get('qsv').get(_preset, 'medium')]
                else:
                    vcodec = "h264_amf"
                    enc_args = ['-rc', 'cqp', '-qp_p', _crf, '-qp_i', _crf, '-quality',
                                PRESET_MAP.get('amf').get(_preset, 'balanced')]
                return global_args, vf_string, vcodec, enc_args

            return global_args, vf_string, vcodec, enc_args

        def run(self):
            from pydub import AudioSegment
            try:
                protxt = config.TEMP_DIR + f'/vas-jd{time.time()}.txt'
                threading.Thread(target=self.hebing_pro, args=(protxt,), daemon=True).start()
                # 有新的需要插入的音频，才涉及到 保留原声音 、 截断、加速、定格、声音混合等，才需要处理音频、分离无声视频
                if self.audio:
                    ext = self.audio.split('.')[-1].lower()
                    # 先转为 wav，方便 soundfile 处理
                    if ext != 'wav':
                        self.post(text='covert ext to wav...')
                        _audio = f'{config.TEMP_DIR}/vas-audio-{time.time()}.wav'
                        runffmpeg([
                            "-y",
                            "-progress", protxt,
                            "-i",
                            Path(self.audio).as_posix(),
                            "-c:a",
                            "pcm_s16le",
                            "-ar",
                            "48000",
                            "-ac",
                            "2",
                            _audio
                        ], state_dict=STATE_DICT)
                        if app_cfg.exit_soft: return
                        self.audio = _audio
                    audio_time = int(get_audio_time(self.audio))

                    tmp_audio = config.TEMP_DIR + f"/vas-tmp_audio-{time.time()}.wav"
                    # 如果音频时长小于视频，则音频直接添加末尾静音
                    if audio_time < self.video_time:
                        audio_data = AudioSegment.from_file(self.audio, format='wav') + AudioSegment.silent(
                            duration=self.video_time - audio_time)
                        audio_data.export(self.audio, format="wav")
                    elif audio_time > self.video_time and self.audio_process == 0:
                        # 截断音频
                        self.post(text='cut audio...')
                        runffmpeg(
                            ['-y', "-progress", protxt, '-i', self.audio, '-ss', '00:00:00.000', '-t',
                             str(self.video_time / 1000),
                             tmp_audio], state_dict=STATE_DICT)
                        if app_cfg.exit_soft: return
                        self.audio = tmp_audio
                    elif audio_time > self.video_time and self.audio_process == 1:
                        # 加速音频
                        self.post(text='speedup audio...')
                        change_speed_rubberband(self.audio, tmp_audio, self.video_time)
                        self.audio = tmp_audio

                    # 需要保留原视频中声音，则需要混合 self.audio 和视频声音
                    if self.saveraw and self.video_info['streams_audio']:
                        tmp_mp4a = config.TEMP_DIR + f"/vas-fromvideotowav-{time.time()}.wav"
                        end_m4a = config.TEMP_DIR + f"/vas-fromvideotowav2uploadwav-{time.time()}.m4a"
                        # 先取出来视频中的音频为 wav
                        self.post(text='get origin audio from video...')
                        runffmpeg([
                            '-y', "-progress", protxt,
                            '-i',
                            Path(self.video).as_posix(),
                            "-vn",
                            tmp_mp4a], state_dict=STATE_DICT
                        )
                        if app_cfg.exit_soft: return
                        # audio_process=0截断 1=音频加速 2=视频定格
                        # 音频时长小于视频时长时无需考虑，简单为音频加静音即可
                        # 需考虑音频时长大于视频时长,并且 2 需定格视频时，要延长视频中声音==self.audio
                        if audio_time > self.video_time and self.audio_process == 2:
                            audio_data = AudioSegment.from_file(tmp_mp4a) + AudioSegment.silent(
                                duration=audio_time - self.video_time)
                            audio_data.export(tmp_mp4a, format="wav")

                        # 到此处，新插入的音频 self.audio和视频剥离的音频，时长已经一致了
                        # 开始混合 2个音频
                        self.post(text='amix origin and new audio...')
                        runffmpeg([
                            '-y', "-progress", protxt,
                            '-i',
                            tmp_mp4a,
                            '-i',
                            self.audio,
                            '-filter_complex',
                            "[0:a][1:a]amix=inputs=2:duration=longest[aout]",
                            '-map',
                            '[aout]',
                            '-ac',
                            '2',
                            end_m4a], state_dict=STATE_DICT)
                        if app_cfg.exit_soft: return
                        # 混合后新音频
                        self.audio = end_m4a
                        # 混合后音频时长，当大于视频时长，并且 audio_process == 2 需定格视频
                        audio_time = int(get_audio_time(self.audio))

                    # audio_process=0截断 1=音频加速 2=视频定格
                    # 如果存在 self.audio ，则无论是否保留原视频中声音，此时都已处理好，直接替换 视频中声音
                    # 分离出无声视频进行定格操作
                    novoice_mp4 = config.TEMP_DIR + f"/vas-novoice-{time.time()}.mp4"
                    cmd = [
                        '-y', "-progress", protxt,
                        '-i',
                        self.video,
                        "-an",
                        '-c:v',
                        'copy',
                        novoice_mp4
                    ]
                    self.post(text='get video without voice...')
                    runffmpeg(cmd, state_dict=STATE_DICT)
                    if app_cfg.exit_soft: return
                    if self.audio_process == 2 and audio_time > self.video_time:
                        # 如果定格视频并且音频时长大于视频时长
                        sec = max((audio_time - self.video_time) / 1000, 1)
                        cmd = [
                            '-y', "-progress", protxt,
                            '-i',
                            novoice_mp4,
                            '-vf',
                            f'tpad=stop_mode=clone:stop_duration={sec}',
                            '-c:v',
                            f'libx264',
                            f'{novoice_mp4}-clone.mp4'
                        ]
                        try:
                            self.post(text=f'clone video {sec}s...')
                            runffmpeg(cmd, state_dict=STATE_DICT)
                            if app_cfg.exit_soft: return
                            novoice_mp4 = f'{novoice_mp4}-clone.mp4'
                        except Exception as e:
                            logger.exception(f'VAS合并期间，延长视频末端失败，将保持原样:{e}')

                    # 视频音频合并
                    audiovideoend_mp4 = config.TEMP_DIR + f"/vad-end-{time.time()}.mp4"
                    self.post(text='embed audio to video...')
                    runffmpeg([
                        '-y', "-progress", protxt,
                        '-i',
                        novoice_mp4,
                        '-i',
                        self.audio,
                        '-c:v',
                        'copy',
                        "-c:a",
                        "aac",
                        audiovideoend_mp4
                    ], state_dict=STATE_DICT)
                    if app_cfg.exit_soft: return

                    # 不存在字幕，则结束了
                    if not self.srt:
                        self.post(type='ok', text=self.file)
                        self.is_end = True
                        shutil.copy2(audiovideoend_mp4, self.file)
                        return
                    self.video = audiovideoend_mp4
                # 软字幕

                cmd = [
                    '-y',
                    "-progress",
                    protxt,

                ]

                # 硬字幕
                sublist = get_subtitle_from_srt(self.srt, is_file=True)
                srt_string = ''
                for i, it in enumerate(sublist):
                    if self.remain_hr:
                        txt_list = []
                        for txt_line in it['text'].strip().split("\n"):
                            txt_list.append(simple_wrap(txt_line.strip(), self.maxlen, self.language))
                        tmp = "\n".join(txt_list)
                    else:
                        tmp = simple_wrap(it['text'].strip(), self.maxlen, self.language)
                    srt_string += f"{it['line']}\n{it['time']}\n{tmp.strip()}\n\n"
                tmpsrt = config.TEMP_DIR + f"/vas-{time.time()}.srt"
                with Path(tmpsrt).open('w', encoding='utf-8') as f:
                    f.write(srt_string.strip())
                if self.is_soft and self.language:
                    # 软字幕
                    subtitle_language = get_subtitle_code(show_target=self.language)
                    cmd += [
                        '-i',
                        self.video,
                        '-i',
                        tmpsrt,
                        '-c:v',
                        'copy',
                        "-c:s",
                        "mov_text",
                        "-metadata:s:s:0",
                        f"language={subtitle_language}",
                        self.file
                    ]
                    runffmpeg(cmd, cmd_dir=config.TEMP_DIR, state_dict=STATE_DICT)
                else:
                    assfile = set_ass_font(tmpsrt)

                    self.post(text='embed subtitle to video...')
                    hw_decode_args, vf_string, vcodec, enc_args = self._get_hard_cfg(os.path.basename(assfile))
                    print(f'{vf_string=}')
                    cmd += hw_decode_args
                    cmd += [
                        '-i',
                        self.video,
                        '-filter_complex',
                        vf_string,
                        "-map",
                        "[v_out]",
                        "-map",
                        "0:a",
                        '-c:v',
                        vcodec]
                    cmd += enc_args + [self.file]
                    self._subprocess(cmd)
                self.post(type='ok', text=self.file)
            except Exception as e:
                self.post(type='error', text=str(e))
            finally:
                self.is_end = True

        def _subprocess(self, cmd):
            print(f'[尝试硬件编解码执行命令]\n{" ".join(cmd)}\n')

            if app_cfg.exit_soft: return
            cmd = ["ffmpeg", '-nostdin'] + cmd
            proc = subprocess.Popen(
                cmd,
                encoding="utf-8",
                errors='ignore',
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                cwd=config.TEMP_DIR
            )
            while proc.poll() is None:
                if app_cfg.exit_soft or STATE_DICT.get('stop'):
                    proc.kill()  # 杀死进程
                    proc.communicate()  # 清理
                    return  # raise RuntimeError("进程被强行终止")
                time.sleep(0.1)  # 免 CPU 飙升
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                raise FFmpegError(
                    f'{proc.returncode=}\n{cmd=}\n{stdout=}\n{stderr=}'
                )
            return True

    def feed(d):
        print(f'{d=}')
        if winobj.has_done:
            return

        if d['type'] == "error":
            winobj.has_done = True
            show_error(d['text'])
            winobj.ysphb_startbtn.setText(tr("start operate"))
            winobj.ysphb_startbtn.setDisabled(False)
            winobj.ysphb_stopbtn.setDisabled(True)
            winobj.ysphb_opendir.setDisabled(False)
        elif d['type'] == 'jd':
            winobj.ysphb_startbtn.setText(d['text'] or "Processing...")
        elif d['type'] == 'logs':
            winobj.ysphb_startbtn.setText(d['text'])
        elif d['type'] == 'ok':
            winobj.has_done = True
            winobj.ysphb_startbtn.setText(tr('zhixingwc'))
            winobj.ysphb_startbtn.setDisabled(False)
            winobj.ysphb_stopbtn.setDisabled(True)
            winobj.ysphb_out.setText(d['text'])
            winobj.ysphb_opendir.setDisabled(False)

    def get_file(type='video'):
        fname = None
        if type == 'video':
            format_str = " ".join(['*.' + f for f in constants.VIDEO_EXTS])
            fname, _ = QFileDialog.getOpenFileName(winobj, 'Select Video', params.get('last_opendir', ''),
                                                   f"Video files({format_str})")
        elif type == 'wav':
            format_str = " ".join(['*.' + f for f in constants.AUDIO_EXITS])
            fname, _ = QFileDialog.getOpenFileName(winobj, 'Select Audio', params.get('last_opendir', ''),
                                                   f"Audio files({format_str})")
        elif type == 'srt':
            fname, _ = QFileDialog.getOpenFileName(winobj, 'Select SRT', params.get('last_opendir', ''),
                                                   "Srt files(*.srt)")

        if not fname:
            return

        if type == 'video':
            winobj.ysphb_videoinput.setText(fname.replace('\\', '/'))
        if type == 'wav':
            winobj.ysphb_wavinput.setText(fname.replace('\\', '/'))
        if type == 'srt':
            winobj.ysphb_srtinput.setText(fname.replace('\\', '/'))
        params['last_opendir'] = os.path.dirname(fname)
        params.save()

    def start():
        winobj.has_done = False
        # 开始处理分离，判断是否选择了源文件
        video = winobj.ysphb_videoinput.text()
        audio = winobj.ysphb_wavinput.text()
        srt = winobj.ysphb_srtinput.text()
        is_soft = winobj.ysphb_issoft.isChecked()
        language = winobj.language.currentText()
        saveraw = winobj.ysphb_replace.isChecked()
        maxlen = 20
        try:
            maxlen = int(winobj.ysphb_maxlen.text())
        except (TypeError, ValueError):
            pass
        if not video:
            show_error(tr("Video must be selected"))
            return
        if not audio and not srt:
            show_error(
                tr("Choose at least one for audio and video"))
            return
        STATE_DICT['stop'] = False
        winobj.ysphb_startbtn.setDisabled(True)
        winobj.ysphb_stopbtn.setDisabled(False)
        winobj.ysphb_startbtn.setText(
            tr("In Progress..."))
        winobj.ysphb_opendir.setDisabled(True)
        task = CompThread(parent=winobj,
                          video=video,
                          audio=audio if audio else None,
                          srt=srt if srt else None,
                          saveraw=saveraw,
                          is_soft=is_soft,
                          language=language,
                          maxlen=maxlen,
                          audio_process=winobj.audio_process.currentIndex(),
                          remain_hr=winobj.remain_hr.isChecked()
                          )
        task.uito.connect(feed)
        task.start()

    def opendir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    winobj = get_cls(Path(__file__).stem)()

    def _set_state():
        STATE_DICT['stop'] = True

    def _bind():
        Path(RESULT_DIR).mkdir(parents=True, exist_ok=True)
        winobj.ysphb_selectvideo.clicked.connect(lambda: get_file('video'))
        winobj.ysphb_selectwav.clicked.connect(lambda: get_file('wav'))
        winobj.ysphb_selectsrt.clicked.connect(lambda: get_file('srt'))
        winobj.ysphb_startbtn.clicked.connect(start)
        winobj.ysphb_stopbtn.clicked.connect(_set_state)
        winobj.ysphb_opendir.clicked.connect(opendir)
        winobj.language.addItems(list(LANGNAME_DICT.values()))
        winobj.set_ass.clicked.connect(lambda: get_win('set_ass'))

    _bind()
    return winobj
