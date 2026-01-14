import math
import json,re
import os
import shutil
import subprocess
import time, random
from pathlib import Path
import threading

from pydub import AudioSegment

from videotrans.configure import config
from videotrans.configure.config import tr
from videotrans.util import tools
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import soundfile as sf
import pyrubberband as pyrb

"""
通过音频加速和视频慢放来对齐翻译配音和原始视频时间轴。


*简单起见，视频慢速暂不考虑 插帧 补帧 光流法 等复杂方式,仅仅使用 setpts=X*PTS -fps_mode vfr* 
*音频加速使用 https://breakfastquay.com/rubberband/，ffmpeg atempo作为后备*


主要实现原理

# 功能概述, 使用python3开发视频翻译功能：
1. 即A语言发音的视频，分离出无声画面视频文件和音频文件，使用语音识别对音频文件识别出原始字幕后，将该字幕翻译翻译为B语言的字幕，再将该B语言字幕配音为B语言配音，然后将B语言字幕和B语言配音同A分离出的无声视频，进行音画同步对齐和合并为新视频。
2. 当前正在做的这部分就是“配音、字幕、视频对齐”，B语言字幕是逐条配音的，每条字幕的配音生成一个wav音频文件。
3. 因为语言不同，因此每条配音可能大于该条字幕的时间，例如该条字幕时长是3s，配音后的mp3时长如果小于等于3s，则不影响，但如果配音时长大于3s，则有问题，需要通过将音频片段自动加速到3s实现同步。也可以通过将该字幕的原始字幕所对应原始视频该片段截取下来，慢速播放延长该视频时长直到匹配配音时长，实现对齐。当然也可以同时 音频自动加速 和 视频慢速，从而避免音频加速太多或视频慢速太多。

# 具体音画同步原理说明


## 音频和视频同时启用时的策略
1. 如果配音时长 小于 当前片段的原始字幕时长，则无需音频加速和视频慢速
2. 如果配音时长 大于 当前片段的原始字幕时长，则将 原始字幕时长 加上 和  下条字幕开始时间之间的静默时间,记为  total_a
   * 如果该时长 total_a 大于 配音时长，则配音无需加速，自然播放完毕即可，视频也无需慢速，注意因此导致的时间轴变化和对视频裁切的影响
   * 如果该时长 total_a 小于配音时长，则计算将配音时长缩短到 total_a 时，需要的加速倍数
    - 如果该倍数 小于等于 1.3，则照此加速音频即可，无需视频慢速，注意因此导致的时间轴变化和对视频裁切的影响
    - 如果该倍数 大于1.3，则按之前逻辑，音频加速和视频慢速各自负担一半,忽略所有限制

## 仅仅使用音频加速时

1. 如果配音时长 小于 当前片段的原始字幕时长，则无需音频加速
2. 如果配音时长 大于 当前片段的原始字幕时长，则将原始字幕时长加上 和  下条字幕开始时间之间的静默时间,记为  total_b
   * 如果该时长 total_b 大于配音时长，则将配音无需加速，自然播放完毕即可，total_b 在容下配音后如果还有剩余空间则使用静音填充。
   * 如果该时长 total_b 仍小于配音时长，强制将配音时长缩短到total_a，倍数最大不超过max_audio_speed_rate
3. 注意开头和结尾以及字幕之间的静默区间，尤其是利用后可能还剩余的静默空间，最终合成后的音频长度，在存在视频时(self.novoice_mp4) 长度应等于视频长度，在不存在时，长度应不小于 self.raw_total_time。

## 仅仅视频慢速时
1. 如果配音时长 小于 当前片段的原始字幕时长，则无需视频慢速，直接从本条字幕开始时间裁切到下条字幕开始时间，如果这是第一条字幕，则从0时间开始裁切
2. 如果配音时长 大于 当前片段的原始字幕时长，则判断原始字幕时长加上 和  下条字幕开始时间之间的静默时间,记为  total_c
   * 如果该时长 total_c 大于 配音时长，则无需视频慢速，自然播放完毕即可，此时应裁切 total_c 时长的视频片段，即裁切到到下条字幕开始时间，而且无需慢速处理，同样如果这是第一条字幕，则从0时间开始裁切
   * 如果该时长 total_c 仍小于配音时长，强制将视频片段(时长为total_a) 慢速延长到和配音等长，此处注意下，PTS倍数最大不超过 max_video_pts_rate。
3. 裁切需注意第一条字幕前的区域(开始时间可能大于0)和最后一条字幕后的区域(结束时间可能不到视频末尾)
4. 无需慢速处理的片段，直接裁切本条字幕开始时间到下条字幕开始时间，无需单独区分静默，因为均无慢速。
5. 需要慢速处理的片段，则需要注意其后的静默空间问题，避免导致丢失视频片段


## 没有 `音频加速`也没有`视频慢速`时

- 第一步按字幕拼接音频
1. 如果第一条字幕不是从0开始的，则前面填充静音。
2. 如果本条字幕开始时间到下条字幕开始时间，这个时长 大于 等于本条配音时长，则直接拼接该配音文件，若差值大于0，即还有富裕空间则后面填充静音。
3. 如果本条字幕开始时间到下条字幕开始时间，这个时长小于 本条配音时长，则直接拼接，无需其他处理
4. 如果是最后一条字幕，则直接将该配音片段拼接上即可，无需判断后边是否还有空间。

- 第二步查看是否存在视频文件
1. self.novoice_mp4 is not None, 并且该文件存在，则为存在视频，此时比较合并后的音频时长和视频时长
    - 如果音频时长 小于 视频时长，则音频末尾填充静音直到长度一致
    - 如果音频时长 大于 视频时长，则视频最后定格延长，直到和音频时长一致
2. 如果不存在视频文件，则无需其他处理


## 小于 1024B 的视频片段可视为无效，过滤掉，容器、元信息加一帧图片，尺寸在 1024B以上

## 小于 40ms的视频片段可能达不到一帧，导致获取视频片段时长失败，此时强制将片段时长指定为  1000/帧率

## 在无视频慢速参与情况下，按照配音，整理字幕时间轴，确保声音和字幕同时显示与消失
## 在有视频慢速参与情况下，将配音片段同视频片段挨个对齐，如果配音片段短于当前视频片段，补充静音，如果大于，则无视，继续拼接，字幕时间轴以配音为准显示
===============================================================================================
"""

# 视频慢速处理
def _cut_video_get_duration(i, task,novoice_mp4_original,preset,crf):
    duration = task['end'] - task['start']
    qiwang=duration
    flag = f'视频{i} 切片pts={task["pts"]}  {"gap" if task["pts"] == 1 else "sub"}-{task["start"]}-{task["end"]}'
    if duration <= 0:
        config.logger.debug(f"{flag},时长为0，跳过裁切视频片段")
        return
    # 冗余，弥补最后一帧强制截断时长比预期变短，累计相差太大
    add_offset=50
    duration_s=f'{(duration+add_offset) / 1000.0:.6f}'
    config.logger.debug(flag)
    cmd = [
        '-y',
        '-i',
        novoice_mp4_original,
        '-ss',
        tools.ms_to_time_string(ms=task['start'], sepflag='.'),
        '-t',
        duration_s,
        '-an',
        '-c:v',
        'libx264', "-g", "1",
        '-preset', preset, '-crf', crf,
        '-pix_fmt', 'yuv420p']
    cmd_bak = cmd[:]
    if task['pts'] > 1:
        qiwang=task["pts"]*duration
        cmd.extend(['-vf', f'tpad=stop_mode=clone:stop_duration=0.2,setpts={task["pts"]}*PTS', '-fps_mode', 'vfr','-t',f'{(qiwang+add_offset)/1000.0:.6f}'])
        # 失败后重试不变速
        cmd_bak.extend(['-vf', f'tpad=stop_mode=clone:stop_duration=0.2,setpts=PTS', '-fps_mode', 'vfr','-t',duration_s,task['filename']])
    else:
        cmd.extend(['-vf', f'tpad=stop_mode=clone:stop_duration=0.2,setpts=PTS', '-fps_mode', 'vfr','-t',duration_s])
    cmd.append(task['filename'])
    try:
        tools.runffmpeg(cmd, force_cpu=True)
        if (not Path(task['filename']).exists() or Path(task['filename']).stat().st_size < 1024) and task['pts'] > 1:
            config.logger.warning(f"{flag} 中间片段 {Path(task['filename']).name} 生成失败{cmd=}，尝试无PTS参数重试{cmd_bak=}。")
            tools.runffmpeg(cmd_bak, force_cpu=True)
        # 仍然有错就放弃了
        if Path(task['filename']).exists() and Path(task['filename']).stat().st_size < 1024:
            config.logger.warning(f"{flag} 中间片段 {Path(task['filename']).name} 生成成功，但尺寸为 < 1024B，无效需删除。{cmd=}")
            Path(task['filename']).unlink(missing_ok=True)
        else:
            real_time=tools.get_video_duration(task["filename"])
            diff=real_time-qiwang
            config.logger.debug(f'视频{i} 切片,期望时长={qiwang} ，实际时长={real_time}, {"【变长】" if diff>0 else "【变短】"} {abs(diff)}ms\n')
    except Exception as e:
        try:
            Path(task['filename']).unlink(missing_ok=True)
        except OSError:
            pass

# 音频加速处理
def _change_speed_rubberband(input_path, target_duration):
    """
    使用 Rubber Band 算法进行高保真实时变速
    """
    y, sr = sf.read(input_path)
    current_duration = int((len(y) / sr) * 1000)
    # 计算变速倍率
    time_stretch_rate = current_duration / target_duration
    # pyrubberband 支持多声道，直接传入即可
    # ts_mag 是变速倍率，>1 为变快（时长变短）
    y_stretched = pyrb.time_stretch(y, sr, time_stretch_rate)
    sf.write(input_path, y_stretched, sr)
    real_time=len(AudioSegment.from_file(input_path))
    if real_time-target_duration !=0:
        config.logger.debug(f"""配音原时长: {current_duration}ms -> 期望变速目标时长: {target_duration}ms (pts:{time_stretch_rate})，变速后实际时长:{real_time}ms，实际时长-期望目标时长={real_time-target_duration}ms""")

class SpeedRate:
    MIN_CLIP_DURATION_MS = 100
    # 统一所有中间音频文件的参数，防止拼接错误
    AUDIO_SAMPLE_RATE = 48000
    AUDIO_CHANNELS = 2
    BESTER_AUDIO_RATE = 1.25 # 在此倍数内可对齐则无需调整视频

    def __init__(self,
                 *,
                 queue_tts=None,  # 原始字幕列表 list[dict,...]
                 shoud_videorate=False,  # 是否需要视频慢速
                 shoud_audiorate=False,  # 是否需要音频加速
                 uuid=None,  # 该任务唯一标识符
                 novoice_mp4=None,  # 原始无音轨视频
                 raw_total_time=0,  # 原始视频时长毫秒

                 target_audio=None,  # 合并后的音频绝对路径
                 cache_folder=None,  # 缓存目录
                 remove_silent_mid=False,
                 align_sub_audio=True
                 ):
        self.align_sub_audio = align_sub_audio
        self.raw_total_time = raw_total_time if raw_total_time is not None else 0
        self.remove_silent_mid = remove_silent_mid
        self.queue_tts = queue_tts
        self.len_queue = len(queue_tts)
        self.shoud_videorate = shoud_videorate
        self.shoud_audiorate = shoud_audiorate
        self.uuid = uuid
        self.novoice_mp4_original = novoice_mp4
        self.novoice_mp4 = novoice_mp4
        self.cache_folder = cache_folder if cache_folder else Path(
            f'{config.TEMP_DIR}/{str(uuid if uuid else time.time())}').as_posix()
        Path(self.cache_folder).mkdir(parents=True, exist_ok=True)

        self.stop_show_process = False
        self.video_info = {}
        self.target_audio = target_audio
        config.settings = config.parse_init()
        # 音频加速允许的最大加速倍数
        self.max_audio_speed_rate = float(config.settings.get('max_audio_speed_rate', 100))
        # 视频慢速允许的最大PTS
        self.max_video_pts_rate = float(config.settings.get('max_video_pts_rate', 10))

        # 存储需要变速处理的音频数据、
        self.audio_data = []
        # 存储需要处理的视频数据
        self.video_for_clips = []

        # 默认帧率
        self.source_video_fps = 30
        # 默认一帧时长ms
        self.fps_ms = 1000 // 30

        self.crf = "20"
        self.preset = "veryfast"
        self.audio_speed_filter = 'atempo'
        try:
            if Path(config.ROOT_DIR + "/crf.txt").exists():
                self.crf = str(int(Path(config.ROOT_DIR + "/crf.txt").read_text()))
            if Path(config.ROOT_DIR + "/preset.txt").exists():
                preset = str(Path(config.ROOT_DIR + "/preset.txt").read_text().strip())
                if preset in ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower',
                              'veryslow']:
                    self.preset = preset
        except Exception:
            pass

        # 检测并设置可用的音频变速滤镜
        self.audio_speed_rubberband = shutil.which("rubberband")

        config.logger.debug(f'允许的最大音频加速倍数={self.max_audio_speed_rate},允许的最大视频慢放倍数={self.max_video_pts_rate}')
        config.logger.debug(f"SpeedRate 初始化。音频加速: {self.shoud_audiorate}, 视频慢速: {self.shoud_videorate}")
        config.logger.debug(f"所有中间音频将统一为: {self.AUDIO_SAMPLE_RATE}Hz, {self.AUDIO_CHANNELS} 声道。\n")

    def _check_ffmpeg_filters(self):
        """
        检查FFmpeg支持的音频变速滤镜，优先使用rubberband。
        """
        try:
            # 运行ffmpeg -filters命令并捕获输出
            result = subprocess.run([config.FFMPEG_BIN, '-filters'], capture_output=True, text=True, encoding='utf-8',
                                    errors='ignore')
            filters_output = result.stdout

            if 'rubberband' in filters_output:
                config.logger.debug("检测到FFmpeg支持 'rubberband' 滤镜，将优先使用。")
                return 'rubberband'
            elif 'atempo' in filters_output:
                config.logger.debug("未检测到 'rubberband' 滤镜，将使用 'atempo' 滤镜。")
                return 'atempo'
            else:
                config.logger.warning("FFmpeg中未检测到 'rubberband' 或 'atempo' 滤镜，音频加速功能可能受限。")
                return None
        except Exception as e:
            config.logger.warning(f"检查FFmpeg滤镜时出错: {e}。将无法使用高质量音频变速。")
            return None

    def run(self):
        # 如果既不加速音频也不慢放视频，仅连接音频
        if not self.shoud_audiorate and not self.shoud_videorate:
            config.logger.debug("检测到未启用音视频变速，进入纯净拼接模式。")
            self._run_no_rate_change_mode()
            return self.queue_tts
        # 否则，执行加减速同步流程
        self._prepare_data()
        # 预先计算出 音频和视频应该变化到的新时长
        self._calculate_adjustments()
        # 先执行音频加速
        if self.audio_data:
            tools.set_process(text='process dubbing speed', uuid=self.uuid)
            if self.audio_speed_rubberband:
                self._execute_audio_speedup_rubberband()
            else:
                self._execute_audio_speedup()
        # 配音文件连接
        tools.set_process(text='concat dubbing', uuid=self.uuid)
        self._concat_audio()
        # 视频文件连接
        if self.video_for_clips:
            tools.set_process(text='process video speed', uuid=self.uuid)
            self._concat_video(self._video_speeddown())

        return self.queue_tts

    def _run_no_rate_change_mode(self):
        """
        模式 不对音频视频做任何加减速处理。
        """
        process_text = tr("Merging audio...")
        tools.set_process(text=process_text, uuid=self.uuid)
        config.logger.debug(            f"================== [音频不加速，视频不慢速，{'移除字幕间空隙' if self.remove_silent_mid else '不移除字幕间空隙'},{'强制对齐' if self.align_sub_audio else '不需要对齐'}] 开始处理 ==================")

        # 提前记录原始字幕时间轴，恒定不变
        for it in self.queue_tts:
            it['start_time_source'] = it['start_time']
            it['end_time_source'] = it['end_time']

        audio_concat_list = []
        total_audio_duration = 0

        for i, it in enumerate(self.queue_tts):
            # 1. 填充字幕前的静音
            silence_duration = it['start_time_source'] - (0 if i == 0 else self.queue_tts[i - 1]['end_time_source'])
            if not self.remove_silent_mid and silence_duration > 0:
                audio_concat_list.append(self._create_silen_file(i, silence_duration))
                config.logger.debug(f"字幕[{it['line']}]前，生成静音片段 {silence_duration}ms")
                total_audio_duration += silence_duration
            # 若需要声音 字幕对齐
            if self.align_sub_audio:
                it['start_time'] = total_audio_duration

            # 加载并处理配音片段
            segment = None
            # 原始字幕时长
            source_duration = it['end_time_source'] - it['start_time_source']
            dubb_duration = source_duration
            if tools.vail_file(it['filename']):
                try:
                    segment = AudioSegment.from_file(it['filename'])
                    dubb_duration = len(segment)
                except Exception as e:
                    config.logger.warning(f"字幕[{it['line']}] 加载音频文件 {it['filename']} 失败: {e}，填充静音。")
            else:
                config.logger.warning(f"字幕[{it['line']}] 配音文件不存在: {it['filename']}，将填充静音。")
            # 真实配音时长
            it['dubb_time'] = dubb_duration
            total_audio_duration += dubb_duration

            # 若需声音字幕对齐
            if self.align_sub_audio:
                it['end_time'] = it['start_time'] + dubb_duration
                it['startraw'], it['endraw'] = tools.ms_to_time_string(ms=it['start_time']), tools.ms_to_time_string(
                    ms=it['end_time'])

            if not segment and not self.remove_silent_mid:
                # 配音失败，没有移除静音时，使用使用原始静音填充，否则丢弃
                audio_concat_list.append(self._create_silen_file(i, dubb_duration))
                continue

            audio_concat_list.append(it['filename'])

            # 如果配音时长小于原始字幕时长,需在后边填充静音
            if not self.remove_silent_mid and dubb_duration < source_duration:
                audio_concat_list.append(self._create_silen_file(i, source_duration - dubb_duration))
                total_audio_duration += source_duration - dubb_duration

            config.logger.debug(f"字幕[{it['line']}] 已生成配音片段，配音时长: {dubb_duration}ms, 原时长 {source_duration}\n")

        # 补充判断是否需要补充静音
        if not self.remove_silent_mid and self.raw_total_time > 0 and total_audio_duration < self.raw_total_time:
            audio_concat_list.append(
                self._create_silen_file(len(self.queue_tts), self.raw_total_time - total_audio_duration))
        # 连接配音
        self._exec_concat_audio(audio_concat_list)

    def _prepare_data(self):
        """
        此阶段为所有后续计算提供基础数据。
        音频加速、视频慢速，至少有一项或者2者
        """
        tools.set_process(text="Preparing data...", uuid=self.uuid)


        # 1. 获取 fps 和 视频信息包括时长等
        if self.shoud_videorate and self.novoice_mp4_original and tools.vail_file(self.novoice_mp4_original):
            try:
                self.video_info = tools.get_video_info(self.novoice_mp4_original)
                self.source_video_fps = self.video_info.get('r_frame_rate')
                self.fps_ms = 1000 // (float(self.video_info.get('video_fps')))
                # 获取视频流时长
                self.raw_total_time = tools.get_video_duration(self.novoice_mp4_original)  # 视频毫秒
            except Exception as e:
                config.logger.warning(f"无法探测源视频帧率，将使用默认值30。错误: {e}")
        config.logger.debug(f"源视频帧率被设定为: {self.source_video_fps}\n")
        config.logger.debug("[start]========在变速前，整理数据，修复错误时间轴==============")
        queue_tts_len = len(self.queue_tts)
        
        # 将每个字幕的 end_time 都改为和下一个字幕的 start_time 一致

        for i,it in enumerate(self.queue_tts):
            if i==0 and it['start_time']<self.MIN_CLIP_DURATION_MS:
                it['start_time']=0
            
            if i< queue_tts_len-1:
                it['end_time']=self.queue_tts[i+1]['start_time']

                
        # 处理末尾一条字幕
        if  self.raw_total_time and self.raw_total_time > self.queue_tts[-1]['end_time']:
            # 视频时长大于字幕末尾时长,延长末尾字幕结束时间，最多延长10s
            self.queue_tts[-1]['end_time']=self.raw_total_time

        # 3. 遍历一次，本次仅仅处理字幕文本为空的情况，将它合并进前面的字幕，
        dubb_list = []
        for i, it in enumerate(self.queue_tts):
            # 字幕时长
            it['source_duration'] = it['end_time'] - it['start_time']
            # 字幕的起始时间
            it['start_time_source'] = it['start_time']
            it['end_time_source'] = it['end_time']

            # 如果时长为0，或当前字幕为空，删掉配音文件
            if it['source_duration'] <= 0 or not it['text'].strip():
                it['dubb_time'] = 0
                it['source_duration']=0
                it['filename'] = None
                it['end_time']=max(it['start_time'],it['end_time'])
                continue

            if not it['filename']:
                it['filename']=self.cache_folder+f'/dubb-{i}.wav'
            
            if not Path(it['filename']).exists():
                it['dubb_time']=it['source_duration']
                AudioSegment.silent(duration=it['source_duration']).set_channels(self.AUDIO_CHANNELS).set_frame_rate(self.AUDIO_SAMPLE_RATE).export(it['filename'],  format="wav")
            else:
                it['dubb_time'] = len(AudioSegment.from_file(it['filename'],format="wav"))

            if it['dubb_time']> it['source_duration']:
                dubb_list.append(it['filename'])

            

        config.logger.debug("[end]========在变速前，整理数据，修复错误时间轴 ==============\n")
    
    def _calculate_adjustments_audiorate(self):
        # 仅音频加速
        for i, it in enumerate(self.queue_tts):
            tools.set_process(text=f'Calculating adjustments... {i}/{self.len_queue}', uuid=self.uuid)
            dubb_duration = it['dubb_time']
            source_duration = it['source_duration']
            # 时间轴不正确
            if source_duration <= 0 or dubb_duration <= 0:
                config.logger.debug(f"字幕{it['line']}, 原始时长或配音时长为0，跳过调整计算。")
                continue
                

            block_source_duration = source_duration
            if dubb_duration <= block_source_duration:
                config.logger.debug(f"字幕{it['line']}, 配音({dubb_duration}ms) < ({block_source_duration}ms)，无需调整。")
                continue


            # 以下所有变速均是针对原始字幕时长+gap
            pts = dubb_duration / block_source_duration
            if pts <= self.max_audio_speed_rate:
                # 未超过允许范围 将音频缩短至 block_source_duration
                self.audio_data.append({
                    "filename": it['filename'],
                    "dubb_time": it['dubb_time'],
                    "target_time": block_source_duration
                })
                config.logger.debug(f"""字幕{it['line']}, 仅音频加速 {pts=} < {self.max_audio_speed_rate=}, 未超出pts限制配音时长: {dubb_duration}ms,配音应压缩至: {block_source_duration}ms,原字幕时长:{source_duration}ms""")
            else:
                # 超过了最大允许范围,设定音频需要变速到的时长
                # 此时end_time可能会入侵下条字幕开始时间
                audio_target_duration = int(dubb_duration / self.max_audio_speed_rate)
                it['end_time'] = it['start_time'] + audio_target_duration
                self.audio_data.append({
                    "filename": it['filename'],
                    "dubb_time": it['dubb_time'],
                    "target_time": audio_target_duration
                })
                config.logger.debug(f"""字幕{it['line']}, 仅音频加速 原始pts={pts}超出限制，强制指定为 {self.max_audio_speed_rate=}, 配音时长: {dubb_duration}ms,配音应压缩至: {audio_target_duration}ms,原字幕时长:{source_duration}ms""")


    def _calculate_adjustments_videorate(self):
        #仅视频慢速
        for i, it in enumerate(self.queue_tts):
            tools.set_process(text=f'Calculating adjustments... {i}/{self.len_queue}', uuid=self.uuid)
            dubb_duration = it['dubb_time']
            source_duration = it['source_duration']
            # 时间轴不正确
            if source_duration <= 0 or dubb_duration <= 0 :
                config.logger.warning(f"字幕{it['line']}, 原始时长或配音时长为0，跳过调整计算。")
                continue

            block_source_duration = source_duration
            # 如果加上空隙可以容下，也无需变速,但需修改 start_time和end_time，以便对齐
            if dubb_duration <= block_source_duration:
                config.logger.debug(f"字幕{it['line']}, 配音({dubb_duration}ms) < ({block_source_duration}ms)，无需调整。")
                continue

            pts = dubb_duration / block_source_duration
            if pts <= self.max_video_pts_rate:
                # 如果没有超过限制,则视频延长到 配音等长
                clip_time = {
                    "start": it['start_time_source'],
                    "end": it['start_time_source'] + block_source_duration,
                    "target_time": dubb_duration,
                    "pts": pts
                }
                self.video_for_clips.append(clip_time)
                config.logger.debug(f"""字幕{it['line']}, 仅视频慢速 {pts=}< {self.max_video_pts_rate}, 未超出pts限制配音时长: {dubb_duration}ms,裁切视频时长: {block_source_duration}ms,视频切片应延长到: {dubb_duration}ms, 原字幕时长:{source_duration}ms""")

            else:
                pts = self.max_video_pts_rate
                # 如果超过限制 超过了最大允许范围,设定视频需要变速到的时长
                target_duration = int(dubb_duration / pts)
                clip_time = {
                    "start": it['start_time_source'],
                    "end": it['start_time_source'] + block_source_duration,
                    "target_time": target_duration,
                    "pts": pts
                }
                # 记录需要裁切的视频开始结束片段
                self.video_for_clips.append(clip_time)
                config.logger.debug(f"""字幕[{it['line']}], 仅视频慢速 原始pts={pts}超出限制，已强制指定为 {self.max_video_pts_rate=}, 配音时长: {dubb_duration}ms,裁切视频时长: {block_source_duration}ms,视频切片应延长至: {target_duration}ms,原字幕时长:{source_duration}ms """)


    def _calculate_adjustments_allrate(self):
        # 两者同时存在
        for i, it in enumerate(self.queue_tts):
            tools.set_process(text=f'Calculating adjustments... {i}/{self.len_queue}', uuid=self.uuid)
            
            dubb_duration = it['dubb_time']
            source_duration = it['source_duration']
            # 时间轴不正确
            if source_duration <= 0 or dubb_duration <= 0 :
                config.logger.warning(f"字幕{it['line']}, 原始时长或配音时长为0，跳过调整计算。")
                continue
                
            # 如果加上空隙可以容下，也无需变速,但需修改 start_time和end_time，以便对齐
            # 此处应该
            if dubb_duration <= source_duration:
                config.logger.debug(f"字幕{it['line']}, 配音({dubb_duration}ms) < 字幕+空隙({source_duration}ms)，无需调整。")
            else:
                over_time = dubb_duration - source_duration
                video_extension = over_time / 2
                # 2者都应该达到的时长，视频延长到，配音压缩到
                target_duration = int(source_duration + video_extension)
                pts = target_duration / source_duration
                # 记录需要裁切的视频开始结束片段
                self.video_for_clips.append({
                    "start": it['start_time_source'],
                    "end": it['start_time_source'] + source_duration,
                    "target_time": target_duration,
                    "pts": min(pts,20)#不允许大于20，否则可能出错
                })
                self.audio_data.append({
                    "filename": it['filename'],
                    "dubb_time": it['dubb_time'],
                    "target_time": target_duration#不允许小于1ms
                })
                config.logger.debug(f"""字幕{it['line']}, 音频加速+视频慢速,{pts=}, 配音时长：{dubb_duration}ms,原字幕时长:{source_duration}ms, 配音大于原时长:{over_time}ms, 配音应减小over_time/2={video_extension}ms压缩至: {target_duration}ms, 视频也应延长至:{target_duration}ms, """)
                
    def _calculate_adjustments(self):

        tools.set_process(text="Calculating adjustments...", uuid=self.uuid)
        config.logger.debug("[start]================== 计算调整方案 ==========")
        if self.shoud_videorate and  self.shoud_audiorate:
            config.logger.debug("同时音频加速 和 视频慢速")
            self._calculate_adjustments_allrate()
        elif self.shoud_videorate:
            config.logger.debug("仅视频慢速")
            self._calculate_adjustments_videorate()
        else:
            config.logger.debug("仅音频加速")
            self._calculate_adjustments_audiorate()
        for it in self.queue_tts:
            it['startraw']=tools.ms_to_time_string(ms=it['start_time'])
            it['endraw']=tools.ms_to_time_string(ms=it['end_time'])
        config.logger.debug("[end]================== 计算调整方案 ==================\n")
    # ffmpeg 处理音频加速
    def _execute_audio_speedup(self):
        """
        使用FFmpeg的`rubberband`或`atempo`滤镜进行高质量音频变速。
        """
        tools.set_process(text="Processing audio...", uuid=self.uuid)
        self.audio_speed_filter = self._check_ffmpeg_filters()
        config.logger.debug(f"[start]================== ffmpeg 执行音频加速:滤镜 {self.audio_speed_filter=}============")
        total_tasks = len(self.audio_data)

        def _speedup_set_dubbtime(i, it):
            if it['dubb_time'] <= it['target_time']:
                return
            try:
                temp_output_file = self.cache_folder + f'/temp-{i}-{time.time()}.wav'
                if self.audio_speed_filter == 'rubberband':
                    filter_str = f"rubberband=tempo={it['dubb_time'] / it['target_time']}"
                    cmd = ['-y', '-i', it['filename'], '-filter:a', filter_str, '-t', f"{it['target_time']/1000.0:.6f}", '-ar',
                           str(self.AUDIO_SAMPLE_RATE), '-ac', str(self.AUDIO_CHANNELS), '-c:a', 'pcm_s16le',
                           temp_output_file]
                else:
                    # 完成使用 atempo 滤镜加速
                    # 构造 atempo 滤镜链
                    # atempo 限制：参数必须在 [0.5, 2.0] 之间
                    atempo_list = []
                    speed_factor = it['dubb_time'] / it['target_time']

                    # 处理加速情况 (> 2.0)
                    while speed_factor > 2.0:
                        atempo_list.append("atempo=2.0")
                        speed_factor /= 2.0

                    # 放入剩余的倍率
                    atempo_list.append(f"atempo={speed_factor}")

                    # 用逗号连接滤镜，形成串联效果，如 "atempo=2.0,atempo=1.5"
                    filter_str = ",".join(atempo_list)

                    cmd = [
                        '-y',
                        '-i', it['filename'],
                        '-filter:a', filter_str,
                        '-t', f"{it['target_time']/1000.0:.6f}",  # 强制裁剪到目标时长，防止精度误差
                        '-ar', str(self.AUDIO_SAMPLE_RATE),
                        '-ac', str(self.AUDIO_CHANNELS),
                        '-c:a', 'pcm_s16le',
                        temp_output_file
                    ]
                tools.runffmpeg(cmd, force_cpu=True)
                after_audio = AudioSegment.from_file(temp_output_file)
                after_len = len(after_audio)
                if after_len > it['target_time']:
                    config.logger.debug(f"变速第{i}个，裁剪后时长{after_len}, 长了 {after_len - it['target_time']}")
                    after_audio = after_audio[:it['target_time']].set_frame_rate(self.AUDIO_SAMPLE_RATE).set_channels(
                        self.AUDIO_CHANNELS)
                    after_audio.export(it['filename'], format="wav")
                    config.logger.debug(f'变速第{i}个，最后时长={len(after_audio)}')
                else:
                    shutil.copy2(temp_output_file, it['filename'])
                config.logger.debug(f"变速第{i}个完成")
            except Exception as e:
                config.logger.warning(f"变速第 {i}个失败 {e}")

        all_task = []
        with ThreadPoolExecutor(max_workers=min(12, total_tasks, os.cpu_count())) as pool:
            for i, d in enumerate(self.audio_data):
                all_task.append(pool.submit(_speedup_set_dubbtime, i, d))

            completed_tasks = 0
            for task in all_task:
                try:
                    task.result()  # 等待任务完成
                    completed_tasks += 1
                    tools.set_process(
                        text=f"audio speedup [{completed_tasks}/{total_tasks}] ...",
                        uuid=self.uuid)
                except Exception as e:
                    config.logger.exception(f"Task {completed_tasks + 1} failed with error: {e}", exc_info=True)

        config.logger.debug(f"[end]================ ffmpeg 执行音频加速:滤镜 {self.audio_speed_filter=}========\n")


    # rubberband 库处理音频加速
    def _execute_audio_speedup_rubberband(self):
        """
        使用FFmpeg的`rubberband`或`atempo`滤镜进行高质量音频变速。
        """
        tools.set_process(text="audio speedup rubberband...", uuid=self.uuid)
        config.logger.debug("[start]======执行音频加速,使用 rubberband lib 库 ==================")

        total_tasks = len(self.audio_data)
        if total_tasks == 0:
            return

        all_task = []
        with ProcessPoolExecutor(max_workers=min(12, total_tasks, os.cpu_count())) as pool:
            for i, d in enumerate(self.audio_data):
                all_task.append(pool.submit(_change_speed_rubberband, d['filename'], d['target_time']))

            completed_tasks = 0
            for task in all_task:
                try:
                    task.result()  # 等待任务完成
                    completed_tasks += 1
                    tools.set_process(text=f"audio speedup rubberband [{completed_tasks}/{total_tasks}] ...",
                                      uuid=self.uuid)
                except Exception as e:
                    config.logger.exception(f"Task {completed_tasks + 1} failed with error: {e}", exc_info=True)


        config.logger.debug("[end]======执行音频加速,使用 rubberband lib 库 ==================\n")
    # 视频慢速
    def _video_speeddown(self):
        data = []
        config.logger.debug(f'[start]=========开始对视频变速处理==========')
        for i, it in enumerate(self.video_for_clips):
            gapfilename = f'{self.cache_folder}/gap-{i}-{time.time()}.mp4'
            it["filename"] = f'{self.cache_folder}/sub-{i}-{time.time()}.mp4'
            if i == 0:
                # 第一个片段，如果start不是0，则需要裁剪从0到当前start
                if it['start'] > 0:
                    data.append({
                        "start": 0,
                        "end": it['start'],
                        "pts": 1,
                        "filename": gapfilename
                    })
                data.append(it)
            else:
                # 距离前边一个切片end的距离
                diff = it['start'] - self.video_for_clips[i - 1]['end']
                if diff > 0:
                    # 距离前边切片有空隙，需要先切出来
                    data.append({
                        "start": self.video_for_clips[i - 1]['end'],
                        "end": it['start'],
                        "pts": 1,
                        "filename": gapfilename
                    })
                data.append(it)
        # 判断最后一个距离结束
        if self.video_for_clips[-1]['end'] < self.raw_total_time:
            data.append({
                "start": self.video_for_clips[-1]['end'],
                "end": self.raw_total_time,
                "pts": 1,
                "filename": f'{self.cache_folder}/gap-last-{time.time()}.mp4'
            })

        total_task = len(data)
        config.logger.debug(f'需要处理的视频片段数量={total_task}')
        all_task = []
        with ProcessPoolExecutor(max_workers=min(12, total_task, os.cpu_count())) as pool:
            for i, d in enumerate(data):
                all_task.append(pool.submit(_cut_video_get_duration, i, d,self.novoice_mp4_original,self.preset,self.crf))
                # 监控进度
            completed_tasks = 0
            for t in all_task:
                try:
                    t.result()  # 等待任务完成
                    completed_tasks += 1
                    tools.set_process(
                        text=tr("[{}/{}] Processing video & probing real durations...", completed_tasks, total_task),
                        uuid=self.uuid)
                except Exception as e:
                    config.logger.exception(f"Task {completed_tasks + 1} failed with error: {e}", exc_info=True)

        
        config.logger.debug(f'[end]=========视频变速处理结束==========\n')
        return data

    def _concat_video(self, data):
        config.logger.debug(f'[start]======拼接所有视频切片====')
        valid_clips = [task['filename'] for task in data if Path(task['filename']).exists() and Path(task['filename']).stat().st_size > 1024]
        if not valid_clips:
            config.logger.debug(f'没有可供拼接的有效视频片段，原始{data=}')
            return

        concat_txt_path = Path(f'{self.cache_folder}/concat_list.txt').as_posix()
        tools.create_concat_txt(valid_clips, concat_txt=concat_txt_path)

        protxt = config.TEMP_DIR + f"/rate_video_{time.time()}.txt"
        intermediate_merged_path = Path(f'{self.cache_folder}/intermediate_merged.mp4').as_posix()
        concat_cmd = ['-y', "-progress", protxt, '-fflags', '+genpts', '-f', 'concat', '-safe', '0', '-i',
                      concat_txt_path, '-c:v', 'copy', intermediate_merged_path]
        tools.set_process(text=f"Concat {len(valid_clips)} video file...", uuid=self.uuid)

        self.stop_show_process = False
        threading.Thread(target=self._hebing_pro, args=(protxt, 'Concat video file'),daemon=True).start()

        tools.runffmpeg(concat_cmd, force_cpu=True,cmd_dir=self.cache_folder)
        self.stop_show_process = True

        if not Path(intermediate_merged_path).exists():
            raise RuntimeError("Concat videos error")
        config.logger.debug(f'拼接视频切片后，新视频真实时长:{tools.get_video_duration(intermediate_merged_path)}ms')
        shutil.move(intermediate_merged_path,self.novoice_mp4)
        config.logger.debug(f'[end]======拼接所有视频切片====\n')

    def _concat_audio(self):
        # 拼接音频

        file_list = []

        len_tts = len(self.queue_tts)
        config.logger.debug(f'[start]=====配音变速完成后，拼接之前，重新校正时间轴，字幕数量：{len_tts} ============')
        # 因变速精确度 及 最大倍数限制，可能出现变速后音频时长仍超出，此时需要后移 end_time
        # 这几个变量调试用哪个
        # 理论所有配音和静音总时长
        total_time=0
        # 理论应插入的静音总时长
        insert_silent_nums=0
        # 理论应插入静音片段个数
        insert_silent_time=0
        
        for i, it in enumerate(self.queue_tts):
            # 有视频慢速时，使用原始 
            source = it['end_time']-it['start_time'] #if not self.shoud_videorate else it['source_duration']
            if source <= 0:
                it['real_dubb_time']=0
                continue
            if i==0 and it['start_time']>0:
                file_list.append(self._create_silen_file(i, it['start_time'],f'0-before-{it["start_time"]}'))
                config.logger.debug(f'字幕{it.get("line")} 前添加静音长度={it["start_time"]}')
                total_time+=it['start_time']
                insert_silent_nums+=1
                insert_silent_time+=it['start_time']
            
            seg = AudioSegment.from_file(it['filename'], format='wav')
            seg_len=len(seg)
            
            file_list.append(it['filename'])
            it['real_dubb_time']=seg_len
            # 原始区间 - 当前真实配音时长
            total_time+=seg_len
            diff=source-seg_len
            if diff>0:
                # 配音时长 小于 原字幕时长，后补静音
                file_list.append(self._create_silen_file(i,diff,f'{i}-before-{diff}'))
                config.logger.debug(f'字幕{it.get("line")} 配音真实时长={seg_len},原字幕区间时长={source},配音[短了],后补静音{diff}\n')
                
                total_time+=diff
                insert_silent_nums+=1
                insert_silent_time+=diff
            elif diff<0:
                config.logger.debug(f'字幕{it.get("line")} 配音真实时长={seg_len},原字幕区间时长={source},配音[长了]{abs(diff)}\n')
            
            
        last_end_diff= self.raw_total_time-self.queue_tts[-1]['end_time']   
        if last_end_diff>0:
            config.logger.debug(f"插入最后一条，{self.raw_total_time=},{self.queue_tts[-1]['end_time']=},差值{last_end_diff}")
            self.queue_tts[-1]['end_time']=self.raw_total_time
            file_list.append(self._create_silen_file('lastsilent',last_end_diff,f'jy_{i}-after-{last_end_diff}'))
            insert_silent_nums+=1
            insert_silent_time+=self.raw_total_time-self.queue_tts[-1]['end_time']
            total_time+=last_end_diff
        
        
        # 再一次更新字幕结束时间戳
        offset=0
        for i,it in enumerate(self.queue_tts):
            it['start_time']+=offset
            diff=it.get('real_dubb_time',0)-it['source_duration']
            # 如果配音大于原时长，需要将字幕开始时间后移
            if diff>0:
                offset+=diff
            it['end_time']=it['start_time']+it['real_dubb_time']
            it['startraw']=tools.ms_to_time_string(ms=it['start_time'])
            it['endraw']=tools.ms_to_time_string(ms=it['end_time'])
            config.logger.debug(f'字幕{it.get("line")} {offset=} 持续时长 {it["end_time"]-it["start_time"]}, 配音时长 {it["real_dubb_time"]}')
        
       
       
        # 真实所有配音和静音片段时长
        real_file_time=0
        # 真实静音片段总时长
        real_insert_silent_time=0
        # 真实插入静音个数
        real_insert_silent_nums=0
        for it in file_list:
            t=len(AudioSegment.from_file(it,format="wav"))
            name=Path(it).name
            if name.startswith('dubb-'):
                index=re.findall(r'dubb-(\d+)-',name)
                if not index:
                    real_file_time+=t
                    continue
                index=int(index[0])
                if index>=len(self.queue_tts):
                    real_file_time+=t
                    continue
                item=self.queue_tts[index]
                startraw=item['startraw']
                endraw=item['endraw']
                config.logger.debug(f'字幕{item.get("line")} {startraw}->{endraw}, start_time->end_time={item["start_time"]}->{item["end_time"]}，从0至此配音时长:dubb_start->dubb_end={real_file_time} --> {real_file_time+t}, 两者应相等')
            elif name.startswith('jy_'):
                real_insert_silent_time+=t
                real_insert_silent_nums+=1
            real_file_time+=t
        
        config.logger.debug(f'\n理论应插入 {insert_silent_time} ms 静音,实际插入 {real_insert_silent_time} ms静音，理论应插入 {insert_silent_nums} 个静音，实际插入 {real_insert_silent_nums} 个静音')
        
        end_time_raw=tools.ms_to_time_string(ms=self.queue_tts[-1]["end_time"])        
        real_file_time_raw=tools.ms_to_time_string(ms=real_file_time)
        
        config.logger.debug(f'\n配音后最后音频时刻字幕end_time={end_time_raw},理论音频总时长 {total_time=},实际配音总时长 {real_file_time=},{real_file_time_raw=},')
        
        config.logger.debug(f'[end]=====配音变速完成后，拼接之前，重新校正时间轴，字幕数量：{len_tts}============\n')
        self._exec_concat_audio(file_list)


    def _exec_concat_audio(self, file_list):
        concat_txt_path = Path(f'{self.cache_folder}/audio_concat_list.txt').as_posix()
        tools.create_concat_txt(file_list, concat_txt=concat_txt_path)
        protxt = config.TEMP_DIR + f"/rate_audio_{time.time()}.txt"
        ext = Path(self.target_audio).suffix.lower()
        codecs = {".m4a": "aac", ".mp3": "libmp3lame", ".wav": "copy"}
        outname= self.target_audio if ext=='.wav' else f'{self.cache_folder}/endout.wav'
        cmd_step1 = [
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_txt_path,
            "-c:a", 'copy',
            outname
        ]
        self.stop_show_process = False
        threading.Thread(target=self._hebing_pro, args=(protxt, 'concat audio'),daemon=True).start()
        tools.runffmpeg(cmd_step1, force_cpu=True,cmd_dir=self.cache_folder)
        self.stop_show_process = True
        config.logger.debug(f'===拼接配音片段后，目标音频{outname}, 真实总时长={len(AudioSegment.from_file(outname, format="wav"))}\n')
        # 直接连接，如果输出要求不是wav，需要再转码
        if ext!='.wav':
            cmd_step2 = [
                "-y",
                "-progress", protxt,
                "-i", outname,
                "-c:a", codecs.get(ext),
                self.target_audio
            ]

            self.stop_show_process = False
            threading.Thread(target=self._hebing_pro, args=(protxt, 'conver audio'),daemon=True).start()
            tools.runffmpeg(cmd_step2, force_cpu=True)
            self.stop_show_process = True
        if not tools.vail_file(self.target_audio):
            config.logger.warning(f"音频拼接失败， {self.target_audio} 未生成。")

    # ffmpeg进度日志
    def _hebing_pro(self, protxt, text="") -> None:
        while 1:
            if config.exit_soft or self.stop_show_process: return
            content = tools.read_last_n_lines(protxt)

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
            tools.set_process(text=f'{text} {end_time}', uuid=self.uuid)
            time.sleep(0.5)

    # 创建静音音频文件并返回路径
    def _create_silen_file(self, i, duration,newname=None):
        if not newname:
            silence_path = Path(self.cache_folder, f"jingyin_{i}_{time.time()}.wav").as_posix()
        else:
            silence_path = Path(self.cache_folder, f"jy_{newname}_{time.time()}.wav").as_posix()
        silent_segment = AudioSegment.silent(duration=duration)
        silent_segment.set_channels(self.AUDIO_CHANNELS).set_frame_rate(self.AUDIO_SAMPLE_RATE).export(silence_path,  format="wav")
        return silence_path


