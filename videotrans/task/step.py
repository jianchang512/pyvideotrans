import copy
import math
import os
import re
import shutil
import textwrap
import threading
import time
from pathlib import Path

from pydub import AudioSegment

from videotrans import translator
from videotrans.configure import config
from videotrans.recognition import run as run_recogn
from videotrans.translator import run as run_trans
from videotrans.tts import run as run_tts
from videotrans.util import tools
from ._rate import SpeedRate


class Runstep:
    def __init__(self, init=None, obj=None, config_params=None, parent=None):
        self.init = init
        self.obj = obj
        self.config_params = config_params
        self.precent = 1
        self.parent = parent
        self.video_codec = config.settings['video_codec']

    # 开始识别出字幕
    def recogn(self):
        if not self.parent.shoud_recogn or config.current_status !='ing':
            return
        self.precent += 3
        tools.set_process(config.transobj["kaishishibie"],type="logs", btnkey=self.init['btnkey'])
        # 分离未完成，需等待
        while not tools.vail_file(self.init['source_wav']):
            tools.set_process(config.transobj["running"],type="logs", btnkey=self.init['btnkey'])
            time.sleep(1)
        # 识别为字幕
        try:
            self.precent += 5
            self.parent.status_text = '语音识别文字处理中' if config.defaulelang == 'zh' else 'Speech Recognition to Word Processing'
            raw_subtitles = run_recogn(
                # faster-whisper openai-whisper googlespeech
                model_type=self.config_params['model_type'],
                # 整体 预先 均等
                type=self.config_params['whisper_type'],
                # 模型名
                model_name=self.config_params['whisper_model'],
                # 识别音频
                audio_file=self.init['shibie_audio'],
                detect_language=self.init['detect_language'],
                cache_folder=self.init['cache_folder'],
                is_cuda=self.config_params['cuda'],
                inst=self)
            Path(self.init['shibie_audio']).unlink(missing_ok=True)
        except Exception as e:
            msg = f'{str(e)}{str(e.args)}'
            if re.search(r'cub[a-zA-Z0-9_.-]+?\.dll', msg, re.I | re.M) is not None:
                msg = f'【缺少cuBLAS.dll】请点击菜单栏-帮助/支持-下载cublasxx.dll,或者切换为openai模型 {msg} ' if config.defaulelang == 'zh' else f'[missing cublasxx.dll] Open menubar Help&Support->Download cuBLASxx.dll or use openai model {msg}'
            elif re.search(r'out\s+?of.*?memory', msg, re.I):
                msg = f'显存不足，请使用较小模型，比如 tiny/base/small {msg}' if config.defaulelang == 'zh' else f'Insufficient video memory, use a smaller model such as tiny/base/small {msg}'
            elif re.search(r'cudnn', msg, re.I):
                msg = f'cuDNN错误，请尝试升级显卡驱动，重新安装CUDA12.x和cuDNN9 {msg}' if config.defaulelang == 'zh' else f'cuDNN error, please try upgrading the graphics card driver and reinstalling CUDA12.x and cuDNN9 {msg}'
            raise Exception(f'{msg}')
        else:
            if config.current_status == 'stop':
                return True
            if not raw_subtitles or len(raw_subtitles) < 1:
                raise Exception(
                    self.obj['raw_basename'] + config.transobj['recogn result is empty'].replace('{lang}',self.config_params['source_language']))
            self._save_srt_target(raw_subtitles, self.init['source_sub'])
            # 仅提取字幕
            if self.config_params['app_mode'] == 'tiqu':
                shutil.copy2(self.init['source_sub'], f"{self.obj['output']}/{self.obj['raw_noextname']}.srt")
        return True

    # 字幕是否存在并且有效
    def _srt_vail(self, file):
        if not tools.vail_file(file):
            return False
        try:
            tools.get_subtitle_from_srt(file)
        except Exception:
            Path(file).unlink(missing_ok=True)
            return False
        return True

    # 翻译字幕
    def trans(self):
        if not self.parent.shoud_trans or config.current_status !='ing':
            return
        self.precent += 3

        config.task_countdown = 0 if self.config_params['app_mode'] == 'biaozhun_jd' else int(config.settings['countdown_sec'])
        # 如果存在目标语言字幕，前台直接使用该字幕替换
        if self._srt_vail(self.init['target_sub']):
            # 判断已存在的字幕文件中是否存在有效字幕纪录
            # 通知前端替换字幕
            with open(self.init['target_sub'], 'r', encoding="utf-8", errors="ignore") as f:
                tools.set_process(f.read().strip(), type='replace_subtitle', btnkey=self.init['btnkey'])
                return True
        
        # 批量不允许修改字幕
        if not self.config_params['is_batch']:
            # 等待编辑原字幕后翻译,允许修改字幕
            tools.set_process(config.transobj["xiugaiyuanyuyan"], type='edit_subtitle_source', btnkey=self.init['btnkey'])
            while config.task_countdown > 0:
                config.task_countdown -= 1
                if config.task_countdown <= config.settings['countdown_sec']:
                    tools.set_process(f"{config.task_countdown} {config.transobj['jimiaohoufanyi']}", type='show_djs',
                                      btnkey=self.init['btnkey'])
                time.sleep(1)

            # 禁止修改字幕
            tools.set_process('translate_start', type='timeout_djs', btnkey=self.init['btnkey'])
            time.sleep(2)


        tools.set_process(config.transobj['starttrans'],type="logs", btnkey=self.init['btnkey'])
        # 开始翻译,从目标文件夹读取原始字幕
        rawsrt = tools.get_subtitle_from_srt(self.init['source_sub'], is_file=True)
        if not rawsrt or len(rawsrt) < 1:
            raise Exception(f'{self.obj["raw_basename"]}' + config.transobj['No subtitles file'])
        # 开始翻译，禁止修改字幕
        try:
            self.parent.status_text = '字幕文字翻译中' if config.defaulelang == 'zh' else 'Subtitle text translation in progress'
            target_srt = run_trans(
                translate_type=self.config_params['translate_type'],
                text_list=rawsrt,
                target_language_name=self.config_params['target_language'],
                set_p=True,
                inst=self,
                source_code=self.init['source_language_code'])
        except Exception as e:
            raise
        else:
            self._save_srt_target(target_srt, self.init['target_sub'])
            # 仅提取，该名字删原
            if self.config_params['app_mode'] == 'tiqu':
                shutil.copy2(self.init['target_sub'],f"{self.obj['output']}/{self.obj['raw_noextname']}-{self.init['target_language_code']}.srt")
        return True

    # 配音处理
    def dubbing(self):
        if not self.parent.shoud_dubbing or config.current_status !='ing':
            return

        self.precent += 3
        config.task_countdown = 0 if self.config_params['app_mode'] == 'biaozhun_jd' else int(config.settings['countdown_sec'])

        # 允许修改字幕
        if not self.config_params['is_batch']:
            tools.set_process(config.transobj["xiugaipeiyinzimu"], type="edit_subtitle_target", btnkey=self.init['btnkey'])
            while config.task_countdown > 0:
                # 其他情况，字幕处理完毕，未超时，等待1s，继续倒计时
                time.sleep(1)
                # 倒计时中
                config.task_countdown -= 1
                if config.task_countdown <= int(config.settings['countdown_sec']):
                    tools.set_process(f"{config.task_countdown}{config.transobj['zidonghebingmiaohou']}",
                                      type='show_djs',
                                      btnkey=self.init['btnkey'])
            # 禁止修改字幕
            tools.set_process('dubbing_start', type='timeout_djs', btnkey=self.init['btnkey'])
        tools.set_process(config.transobj['kaishipeiyin'], type="logs",btnkey=self.init['btnkey'])
        time.sleep(3)
        try:
            self._exec_tts(self._before_tts())
        except Exception as e:
            raise
        return True

    # 合并操作
    def hebing(self):
        if not self.parent.shoud_hebing or config.current_status !='ing':
            return
        if self.precent < 95:
            self.precent += 3
        try:
            self._compos_video()
        except Exception as e:
            raise
        self.precent = 100
        return True

    # 保存字幕文件 到目标文件夹
    def _save_srt_target(self, srtstr, file):
        # 是字幕列表形式，重新组装
        tools.save_srt(srtstr,file)
        tools.set_process(Path(file).read_text(encoding='utf-8'), type='replace_subtitle', btnkey=self.init['btnkey'])
        return True

    # 配音预处理，去掉无效字符，整理开始时间
    def _before_tts(self):
        queue_tts = []
        # 获取字幕
        try:
            subs = tools.get_subtitle_from_srt(self.init['target_sub'])
            if len(subs) < 1:
                raise Exception("字幕格式不正确，请打开查看")
        except Exception as e:
            raise
        rate = int(str(self.config_params['voice_rate']).replace('%', ''))
        if rate >= 0:
            rate = f"+{rate}%"
        else:
            rate = f"{rate}%"
        # 取出设置的每行角色
        line_roles = self.config_params["line_roles"] if "line_roles" in self.config_params else None
        # 取出每一条字幕，行号\n开始时间 --> 结束时间\n内容
        for i, it in enumerate(subs):
            # 判断是否存在单独设置的行角色，如果不存在则使用全局
            voice_role = self.config_params['voice_role']
            if line_roles and f'{it["line"]}' in line_roles:
                voice_role = line_roles[f'{it["line"]}']
            newrole = voice_role.replace('/', '-').replace('\\', '/')
            filename = f'{i}-{newrole}-{self.config_params["voice_rate"]}-{self.config_params["voice_autorate"]}-{it["text"]}-{self.config_params["volume"].replace("%", "")}-{self.config_params["pitch"]}'
            # 要保存到的文件
            # clone-voice同时也是音色复制源
            filename = self.init['cache_folder'] + "/" + tools.get_md5(filename) + ".mp3"
            # 如果是clone-voice类型， 需要截取对应片段
            if it['end_time'] <= it['start_time']:
                continue
            # 是克隆
            if self.config_params['tts_type'] in ['clone-voice', 'CosyVoice'] and voice_role == 'clone':
                if self.config_params['is_separate'] and not tools.vail_file(self.init['vocal']):
                    raise Exception(f"背景分离出错 {self.init['vocal']}")
                    # clone 方式文件为wav格式
                if tools.vail_file(self.init['source_wav']):
                    tools.cut_from_audio(
                        audio_file=self.init['vocal'] if self.config_params[
                            'is_separate'] else self.init['source_wav'],
                        ss=it['startraw'],
                        to=it['endraw'],
                        out_file=filename
                    )

            queue_tts.append({
                "text": it['text'],
                "role": voice_role,
                "start_time": it['start_time'],
                "end_time": it['end_time'],
                "rate": rate,
                "startraw": it['startraw'],
                "endraw": it['endraw'],
                "volume": self.config_params['volume'],
                "pitch": self.config_params['pitch'],
                "tts_type": self.config_params['tts_type'],
                "filename": filename})
        return queue_tts

    def _exec_tts(self, queue_tts):
        if not queue_tts or len(queue_tts) < 1:
            raise Exception(f'Queue tts length is 0')
        # 具体配音操作
        try:
            run_tts(queue_tts=copy.deepcopy(queue_tts),
                    language=self.init['target_language_code'],
                    set_p=True,
                    inst=self)
        except Exception as e:
            raise
        # 获取 novoice_mp4的长度
        if not tools.is_novoice_mp4(self.init['novoice_mp4'], self.init['noextname']):
            raise Exception("not novoice mp4")

        rate_inst=SpeedRate(
            queue_tts=queue_tts,
            btnkey=self.init['btnkey'],
            shoud_audiorate=self.config_params['voice_autorate'] and int(config.settings['audio_rate']) > 1,
            shoud_videorate=self.config_params['video_autorate'] and int(config.settings['video_rate']) > 1,
            novoice_mp4=self.init['novoice_mp4'],
            noextname=self.init['noextname'],
            target_audio=self.init['target_wav']
        )
        queue_tts=rate_inst.run()
        #
        #
        # video_time = tools.get_video_duration(self.init['novoice_mp4'])
        # audio_length, queue_tts = self._merge_audio_segments(
        #     video_time=video_time,
        #     queue_tts=copy.deepcopy(queue_tts))

        # 更新字幕
        srt = ""
        for (idx, it) in enumerate(queue_tts):
            if not config.settings['force_edit_srt']:
                it['startraw'] = tools.ms_to_time_string(ms=it['start_time_source'])
                it['endraw'] = tools.ms_to_time_string(ms=it['end_time_source'])
            srt += f"{idx + 1}\n{it['startraw']} --> {it['endraw']}\n{it['text']}\n\n"
        # 字幕保存到目标文件夹
        Path(self.init['target_sub']).write_text(srt.strip(), encoding="utf-8", errors="ignore")
        return True

    # 延长 novoice.mp4  duration_ms 毫秒
    def _novoicemp4_add_time(self, duration_ms):
        if duration_ms < 1000:
            return
        tools.set_process(f'{config.transobj["shipinmoweiyanchang"]} {duration_ms}ms', btnkey=self.init['btnkey'])
        if not tools.is_novoice_mp4(self.init['novoice_mp4'], self.init['noextname'],btnkey=self.init['btnkey']):
            raise Exception("not novoice mp4")

        video_time = tools.get_video_duration(self.init['novoice_mp4'])
        shutil.copy2(self.init['novoice_mp4'], self.init['novoice_mp4'] + ".raw.mp4")
        try:

            tools.cut_from_video(
                source=self.init['novoice_mp4'],
                ss=tools.ms_to_time_string(ms=video_time - 100).replace(',', '.'),
                pts='20',
                out=self.init['cache_folder'] + "/last-clip-novoicepts20.mp4"
            )
            video_time2 = tools.get_video_duration(self.init['cache_folder'] + "/last-clip-novoicepts20.mp4")
            tools.cut_from_video(
                source=self.init['cache_folder'] + "/last-clip-novoicepts20.mp4",
                ss=tools.ms_to_time_string(ms=video_time2 - 100).replace(',', '.'),
                out=self.init['cache_folder'] + "/last-clip-novoice.mp4"
            )
            tools.runffmpeg([
                '-y',
                '-stream_loop',
                f'{math.ceil(duration_ms / 100)}',
                '-i',
                self.init['cache_folder'] + "/last-clip-novoice.mp4",
                '-c:v',
                'copy',
                '-an',
                self.init['cache_folder'] + "/last-clip-novoice-all.mp4"
            ])
        except Exception as  e:
            print(e)

        tools.runffmpeg([
            '-y',
            '-i',
            f"{self.init['novoice_mp4']}.raw.mp4",
            '-i',
            self.init['cache_folder'] + "/last-clip-novoice-all.mp4",
            '-filter_complex',
            "[0:v][1:v]concat=n=2:v=1[outv]",
            '-map',
            "[outv]",
            '-an',
            self.init['novoice_mp4']])

        Path(f"{self.init['novoice_mp4']}.raw.mp4").unlink(missing_ok=True)
        return True

    # 添加背景音乐
    def _back_music(self):
        if config.current_status !='ing':
            return
        if self.parent.shoud_dubbing and tools.vail_file(self.init['target_wav']) and tools.vail_file(self.init['background_music']):
            try:
                self.parent.status_text = '添加背景音频' if config.defaulelang == 'zh' else 'Adding background audio'
                # 获取视频长度
                vtime = tools.get_video_info(self.init['novoice_mp4'], video_time=True)
                vtime /= 1000
                # 获取音频长度
                atime = tools.get_audio_time(self.init['background_music'])

                # 转为m4a
                if not self.init['background_music'].lower().endswith('.m4a'):
                    tmpm4a = self.init['cache_folder'] + f"/background_music-wav-m4a.m4a"
                    tools.wav2m4a(self.init['background_music'], tmpm4a)
                    self.init['background_music'] = tmpm4a
                beishu = math.ceil(vtime / atime)
                if config.settings['loop_backaudio'] and beishu > 1 and vtime - 1 > atime:
                    # 获取延长片段

                    tools.concat_multi_audio(filelist=[self.init['background_music'] for n in range(beishu + 1)],
                                             out=self.init['cache_folder'] + "/background_music-concat-extend.m4a")
                    self.init['background_music'] = self.init['cache_folder'] + "/background_music-concat-extend.m4a"
                # 背景音频降低音量
                tools.runffmpeg(
                    ['-y', '-i', self.init['background_music'], "-filter:a",
                     f"volume={config.settings['backaudio_volume']}",
                     '-c:a', 'aac',
                     self.init['cache_folder'] + f"/background_music-volume.m4a"])
                # 背景音频和配音合并
                cmd = ['-y', '-i', self.init['target_wav'], '-i',
                       self.init['cache_folder'] + f"/background_music-volume.m4a",
                       '-filter_complex', "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2", '-ac', '2',
                       self.init['cache_folder'] + f"/lastend.m4a"]
                tools.runffmpeg(cmd)
                self.init['target_wav'] = self.init['cache_folder'] + f"/lastend.m4a"
            except Exception as e:
                config.logger.error(f'添加背景音乐失败:{str(e)}')

    def _separate(self):
        if config.current_status !='ing':
            return
        if self.parent.shoud_separate and tools.vail_file(self.init['target_wav']):
            try:
                self.parent.status_text = '重新嵌入背景音' if config.defaulelang == 'zh' else 'Re-embedded background sounds'
                # 原始背景音乐 wav,和配音后的文件m4a合并
                # 获取视频长度
                vtime = tools.get_video_info(self.init['novoice_mp4'], video_time=True)
                vtime /= 1000
                # 获取音频长度
                atime = tools.get_audio_time(self.init['instrument'])
                beishu = math.ceil(vtime / atime)
                config.logger.info(f'合并背景音 {beishu=},{atime=},{vtime=}')
                if config.settings['loop_backaudio'] and atime + 1 < vtime:
                    # 背景音连接延长片段
                    tools.concat_multi_audio(filelist=[self.init['instrument'] for n in range(beishu + 1)],
                                             out=self.init['cache_folder'] + "/instrument-concat.m4a")
                    self.init['instrument'] = self.init['cache_folder'] + f"/instrument-concat.m4a"
                # 背景音合并配音
                tools.backandvocal(self.init['instrument'], self.init['target_wav'])
            except Exception as e:
                config.logger.error('合并原始背景失败' + config.transobj['Error merging background and dubbing'] + str(e))

    # 最终合成视频 source_mp4=原始mp4视频文件，noextname=无扩展名的视频文件名字
    def _compos_video(self):
        if not self.parent.shoud_hebing or config.current_status !='ing':
            return True
        # 判断novoice_mp4是否完成
        if not tools.is_novoice_mp4(self.init['novoice_mp4'], self.init['noextname']):
            raise Exception(config.transobj['fenlinoviceerror'])
        # 需要配音但没有配音文件
        if self.parent.shoud_dubbing and not tools.vail_file(self.init['target_wav']):
            raise Exception(f"{config.transobj['Dubbing']}{config.transobj['anerror']}:{self.init['target_wav']}")

        # 无声音视频 或 合并模式时原视频
        novoice_mp4_path = Path(self.init['novoice_mp4'])
        novoice_mp4 = Path(self.init['novoice_mp4']).as_posix()

        # 目标字幕语言
        subtitle_language = translator.get_subtitle_code(show_target=self.config_params['target_language'])

        # 视频目录，用于硬字幕时进入工作目录
        mp4_dirpath = novoice_mp4_path.parent.resolve()

        # 软字幕 完整路径
        soft_srt = Path(self.init['target_sub']).as_posix()

        # 硬字幕仅名字 需要和视频在一起
        hard_srt = "tmp.srt"
        hard_srt_path = Path(mp4_dirpath / hard_srt)

        # 存放目标字幕
        target_sub_list = []
        # 存放原始字幕
        source_sub_list = []
        self.precent = 90 if self.precent < 90 else self.precent
        # 需要字幕
        if self.config_params['subtitle_type'] > 0:
            maxlen_source = int(
                config.settings['cjk_len'] if self.init['source_language_code'][:2] in ["zh", "ja", "jp", "ko"] else
                config.settings['other_len'])
            maxlen = int(
                config.settings['cjk_len'] if self.init['target_language_code'][:2] in ["zh", "ja", "jp", "ko"] else
                config.settings['other_len'])

            if tools.vail_file(self.init['source_sub']):
                try:
                    source_sub_list = tools.get_subtitle_from_srt(self.init['source_sub'])
                except Exception as e:
                    raise Exception(f'{config.transobj["Subtitles error"]}-1 :{str(e)}')
            if tools.vail_file(self.init['target_sub']):
                try:
                    target_sub_list = tools.get_subtitle_from_srt(self.init['target_sub'])
                except Exception as e:
                    raise Exception(f'{config.transobj["Subtitles error"]}-1 :{str(e)}')

            if len(target_sub_list) < 1 and len(source_sub_list) < 1:
                raise Exception(f'需要嵌入字幕但不存在或未生成字幕')
            # 如果原始语言和目标语言相同，则强制单字幕
            print(f"@@@@@@@@@@@@@@@@@@@@@@@@@@@{self.init['source_language_code']=},,{self.init['target_language_code']=}")
            if self.init['source_language_code']==self.init['target_language_code']:
                print(f'##################### {self.config_params["subtitle_type"]=}')
                if self.config_params['subtitle_type']==3:
                    self.config_params['subtitle_type']=1
                elif self.config_params['subtitle_type']==4:
                    self.config_params['subtitle_type']=2
            # 需要双字幕
            if len(target_sub_list) > 0 and len(source_sub_list) > 0 and self.config_params['subtitle_type'] in [3, 4]:
                print(f'$$$$$$$$$$$$$$$$$==================')
                # 处理双硬字幕
                if self.config_params['subtitle_type'] == 3:
                    text = ""
                    source_length = len(source_sub_list)
                    for i, it in enumerate(target_sub_list):
                        tmp = textwrap.fill(it['text'].strip(), maxlen, replace_whitespace=False)
                        text += f"{it['line']}\n{it['time']}\n{tmp.strip()}"
                        if source_length > 0 and i < source_length:
                            text += "\n" + textwrap.fill(source_sub_list[i]['text'], maxlen_source, replace_whitespace=False).strip()
                        text += "\n\n"
                    hard_srt_path.write_text(text.strip(), encoding="utf-8", errors="ignore")
                    os.chdir(mp4_dirpath)
                    shutil.copy2(hard_srt_path.as_posix(), f"{self.obj['output']}/shuang.srt")
                    hard_srt = tools.set_ass_font(hard_srt_path.as_posix())

                # 双字幕 软字幕
                elif self.config_params['subtitle_type'] == 4:
                    text = ""
                    for i, it in enumerate(target_sub_list):
                        text += f"{it['line']}\n{it['time']}\n{it['text'].strip()}"
                        if i < len(source_sub_list):
                            text += f"\n{source_sub_list[i]['text'].strip()}"
                        text += "\n\n"
                    # 软字幕双
                    soft_srt = self.obj['output'] + "/shuang.srt"
                    shutil.copy2(self.init['target_sub'], soft_srt)
                    Path(soft_srt).write_text(text.strip(),encoding="utf-8", errors="ignore")
                    soft_srt = Path(soft_srt).as_posix()
            elif self.config_params['subtitle_type'] > 0:
                # 单硬字幕
                if self.config_params['subtitle_type'] in [1, 3]:
                    target_sub_list = target_sub_list if len(target_sub_list) > 0 else source_sub_list
                    maxlen = maxlen if len(target_sub_list) > 0 else maxlen_source
                    text = ""
                    for i, it in enumerate(target_sub_list):
                        it['text'] = textwrap.fill(it['text'], maxlen, replace_whitespace=False).strip()
                        text += f"{it['line']}\n{it['time']}\n{it['text'].strip()}\n\n"
                    hard_srt_path.write_text(text, encoding='utf-8', errors="ignore")
                    os.chdir(mp4_dirpath)
                    hard_srt = tools.set_ass_font(hard_srt_path.as_posix())
                # 单软
                elif self.config_params['subtitle_type'] in [2, 4]:
                    soft_srt = self.init['source_sub'] if not os.path.exists(soft_srt) else soft_srt
                    subtitle_language = translator.get_subtitle_code(
                        show_target=self.config_params['source_language']) if not os.path.exists(
                        soft_srt) else subtitle_language

        # 有配音 延长视频或音频对齐
        if self.parent.shoud_dubbing and self.config_params['append_video']:
            video_time = tools.get_video_duration(novoice_mp4)
            try:
                audio_length = int(tools.get_audio_time(self.init['target_wav']) * 1000)
            except Exception:
                audio_length = 0
            if audio_length > 0 and audio_length > video_time:
                try:
                    # 先对音频末尾移除静音
                    tools.remove_silence_from_end(self.init['target_wav'], is_start=False)
                    audio_length = int(tools.get_audio_time(self.init['target_wav']) * 1000)
                except Exception:
                    audio_length = 0
            if audio_length > 0 and audio_length > video_time:
                # 视频末尾延长
                try:
                    # 对视频末尾定格延长
                    self.parent.status_text = '视频末尾延长中' if config.defaulelang == 'zh' else 'Extension at the end of the video'
                    self._novoicemp4_add_time(audio_length - video_time)
                except Exception as e:
                    config.logger.error(f'视频末尾延长失败:{str(e)}')
            elif audio_length > 0 and video_time > audio_length:
                ext = self.init['target_wav'].split('.')[-1]
                m = AudioSegment.from_file(
                    self.init['target_wav'],
                    format="mp4" if ext == 'm4a' else ext) + AudioSegment.silent(
                    duration=video_time - audio_length)
                m.export(self.init['target_wav'], format="mp4" if ext == 'm4a' else ext)

        self._back_music()
        self._separate()
        # 开启进度线程
        protxt = config.TEMP_DIR + f"/compose{time.time()}.txt"
        video_time = tools.get_video_duration(novoice_mp4)
        self.precent = self.precent if self.precent < 98 else 95
        basenum = 100 - self.precent

        def hebing_pro():
            while 1:
                if self.precent >= 100:
                    return
                if not os.path.exists(protxt):
                    time.sleep(1)
                    continue
                with open(protxt, 'r', encoding='utf-8') as f:
                    content = f.read().strip().split("\n")
                    if content[-1] == 'progress=end':
                        return
                    idx = len(content) - 1
                    end_time = "00:00:00"
                    while idx > 0:
                        if content[idx].startswith('out_time='):
                            end_time = content[idx].split('=')[1].strip()
                            break
                        idx -= 1
                    try:
                        h, m, s = end_time.split(':')
                    except Exception:
                        time.sleep(1)
                        continue
                    else:
                        h, m, s = end_time.split(':')
                        precent = round((int(h) * 3600000 + int(m) * 60000 + int(s[:2]) * 1000) * basenum / video_time,
                                        2)
                        if self.precent + precent < 99.9:
                            self.precent += precent
                        tools.set_process('', btnkey=self.init['btnkey'])
                        time.sleep(1)

        threading.Thread(target=hebing_pro).start()
        if self.config_params['subtitle_type'] in [2, 4]:
            soft_srt_name = os.path.basename(soft_srt)
            os.chdir(os.path.dirname(soft_srt))
        try:
            self.parent.status_text = '视频+字幕+配音合并中' if config.defaulelang == 'zh' else 'Video + Subtitles + Dubbing in merge'
            # 有配音有字幕
            if self.config_params['voice_role'] != 'No' and self.config_params['subtitle_type'] > 0:
                if self.config_params['subtitle_type'] in [1, 3]:
                    tools.set_process(config.transobj['peiyin-yingzimu'], btnkey=self.init['btnkey'])
                    # 需要配音+硬字幕
                    tools.runffmpeg([
                        "-y",
                        "-progress",
                        protxt,
                        "-i",
                        novoice_mp4,
                        "-i",
                        Path(self.init['target_wav']).as_posix(),
                        "-c:v",
                        f"libx{self.video_codec}",
                        "-c:a",
                        "aac",
                        "-vf",
                        f"subtitles={hard_srt}",
                        '-crf',
                        f'{config.settings["crf"]}',
                        '-preset',
                        config.settings['preset'],
                        Path(self.init['targetdir_mp4']).as_posix()
                    ])
                else:
                    tools.set_process(config.transobj['peiyin-ruanzimu'], btnkey=self.init['btnkey'])
                    # 配音+软字幕
                    tools.runffmpeg([
                        "-y",
                        "-progress",
                        protxt,
                        "-i",
                        novoice_mp4,
                        "-i",
                        Path(self.init['target_wav']).as_posix(),
                        "-i",
                        soft_srt_name,
                        "-c:v",
                        "copy",
                        "-c:a",
                        "aac",
                        "-c:s",
                        "mov_text",
                        "-metadata:s:s:0",
                        f"language={subtitle_language}",
                        Path(self.init['targetdir_mp4']).as_posix()
                    ])
            elif self.config_params['voice_role'] != 'No':
                # 有配音无字幕
                tools.set_process(config.transobj['onlypeiyin'], btnkey=self.init['btnkey'])
                tools.runffmpeg([
                    "-y",
                    "-progress",
                    protxt,
                    "-i",
                    novoice_mp4,
                    "-i",
                    Path(self.init['target_wav']).as_posix(),
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    Path(self.init['targetdir_mp4']).as_posix()
                ])
            # 硬字幕无配音  原始 wav合并
            elif self.config_params['subtitle_type'] in [1, 3]:
                tools.set_process(config.transobj['onlyyingzimu'], btnkey=self.init['btnkey'])
                cmd = [
                    "-y",
                    "-progress",
                    protxt,
                    "-i",
                    novoice_mp4
                ]
                if tools.vail_file(self.init['source_wav']):
                    cmd.append('-i')
                    cmd.append(Path(self.init['source_wav']).as_posix())

                cmd.append('-c:v')
                cmd.append(f'libx{self.video_codec}')
                if tools.vail_file(self.init['source_wav']):
                    cmd.append('-c:a')
                    cmd.append('aac')
                cmd += [
                    "-vf",
                    f"subtitles={hard_srt}",
                    '-crf',
                    f'{config.settings["crf"]}',
                    '-preset',
                    config.settings['preset'],
                    Path(self.init['targetdir_mp4']).as_posix(),
                ]
                tools.runffmpeg(cmd)
            elif self.config_params['subtitle_type'] in [2, 4]:
                # 软字幕无配音
                tools.set_process(config.transobj['onlyruanzimu'], btnkey=self.init['btnkey'])
                # 原视频
                cmd = [
                    "-y",
                    "-progress",
                    protxt,
                    "-i",
                    novoice_mp4
                ]
                # 原配音流
                if tools.vail_file(self.init['source_wav']):
                    cmd.append("-i")
                    cmd.append(Path(self.init['source_wav']).as_posix())
                # 目标字幕流
                cmd += [
                    "-i",
                    soft_srt_name,
                    "-c:v",
                    "copy"
                ]
                if tools.vail_file(self.init['source_wav']):
                    cmd.append('-c:a')
                    cmd.append('aac')
                cmd += [
                    "-c:s",
                    "mov_text",
                    "-metadata:s:s:0",
                    f"language={subtitle_language}",
                    '-crf',
                    f'{config.settings["crf"]}',
                    '-preset',
                    config.settings['preset']
                ]
                cmd.append(Path(self.init['targetdir_mp4']).as_posix())
                tools.runffmpeg(cmd)
        except Exception as e:
            raise Exception(f'compose srt + video + audio:{str(e)}')
        self.precent = 99
        os.chdir(config.rootdir)
        try:
            if not self.config_params['only_video']:
                with open(self.init['target_dir'] + f'/{"readme" if config.defaulelang != "zh" else "文件说明"}.txt',
                          'w', encoding="utf-8", errors="ignore") as f:
                    f.write(f"""以下是可能生成的全部文件, 根据执行时配置的选项不同, 某些文件可能不会生成, 之所以生成这些文件和素材，是为了方便有需要的用户, 进一步使用其他软件进行处理, 而不必再进行语音导出、音视频分离、字幕识别等重复工作


*.mp4 = 最终完成的目标视频文件
{self.init['source_language_code']}.m4a|.wav = 原始视频中的音频文件(包含所有背景音和人声)
{self.init['target_language_code']}.m4a = 配音后的音频文件(若选择了保留背景音乐则已混入)
{self.init['source_language_code']}.srt = 原始视频中根据声音识别出的字幕文件
{self.init['target_language_code']}.srt = 翻译为目标语言后字幕文件
shuang.srt = 双语字幕
vocal.wav = 原始视频中分离出的人声音频文件
instrument.wav = 原始视频中分离出的背景音乐音频文件


如果觉得该项目对你有价值，并希望该项目能一直稳定持续维护，欢迎各位小额赞助，有了一定资金支持，我将能够持续投入更多时间和精力
捐助地址：https://github.com/jianchang512/pyvideotrans/issues/80

====

Here are the descriptions of all possible files that might exist. Depending on the configuration options when executing, some files may not be generated.

*.mp4 = The final completed target video file
{self.init['source_language_code']}.m4a|.wav = The audio file in the original video (containing all sounds)
{self.init['target_language_code']}.m4a = The dubbed audio file (if you choose to keep the background music, it is already mixed in)
{self.init['source_language_code']}.srt = Subtitles recognized in the original video
{self.init['target_language_code']}.srt = Subtitles translated into the target language
shuang.srt = Source language and target language subtitles srt 
vocal.wav = The vocal audio file separated from the original video
instrument.wav = The background music audio file separated from the original video


If you feel that this project is valuable to you and hope that it can be maintained consistently, we welcome small sponsorships. With some financial support, I will be able to continue to invest more time and energy
Donation address: https://ko-fi.com/jianchang512


====

Github: https://github.com/jianchang512/pyvideotrans
Docs: https://pyvideotrans.com

                """)

            novoice_mp4_path.unlink(missing_ok=True)
            hard_srt_path.unlink(missing_ok=True)
            Path(mp4_dirpath.as_posix() + "/tmp.srt.ass").unlink(missing_ok=True)
            if os.path.exists(self.obj['output'] + "/shuang.srt"):
                with open(self.obj['output'] + "/shuang.srt", 'r', encoding='utf-8') as f:
                    c = f.read().replace('\\N', "\n")
                with open(self.obj['output'] + "/shuang.srt", 'w', encoding='utf-8') as f:
                    f.write(c)
        except:
            pass
        self.precent = 100
        time.sleep(1)
        return True
