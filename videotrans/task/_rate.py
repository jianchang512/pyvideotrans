"""
# 具体同步原理说明

通过音频加速和视频慢放来对齐翻译配音和原始视频时间轴。


*简单起见，视频慢速暂不考虑 插帧 补帧 光流法 等复杂方式,仅仅使用 setpts=X*PTS -fps_mode vfr* 
*音频加速使用 https://breakfastquay.com/rubberband/


主要实现原理

# 功能概述, 使用python3开发视频翻译功能：
1. A语言发音的视频，分离出无声画面视频文件和音频文件，使用语音识别对音频文件识别出原始字幕后，将该字幕翻译翻译为B语言的字幕，再将该B语言字幕配音为B语言配音，然后将B语言字幕和B语言配音同A分离出的无声视频，进行音画同步对齐和合并为新视频。
2. 当前正在做的这部分就是“配音、字幕、视频对齐”，B语言字幕是逐条配音的，每条字幕的配音生成一个wav音频文件。
3. 因为语言不同，因此每条配音可能大于该条字幕的时间，例如该条字幕时长是3s，配音后的mp3时长如果小于等于3s，则不影响，但如果配音时长大于3s，则有问题，需要通过将音频片段自动加速到3s实现同步。也可以通过将该字幕的原始字幕所对应原始视频该片段截取下来，慢速播放延长该视频时长直到匹配配音时长，实现对齐。当然也可以同时 音频自动加速 和 视频慢速，从而避免音频加速太多或视频慢速太多。


## 预先处理

**有音频加速和(或)视频慢速时，先将每个字幕的 end_time 都改为和下一个字幕的 start_time 一致，即去掉字幕间静音区间**

## 音频和视频同时启用时的策略
1. 如果配音时长 小于 当前片段的字幕时长，则无需音频加速和视频慢速
2. 如果配音时长 大于 当前片段的字幕时长，则计算将配音时长缩短到匹配字幕时长时，需要的加速倍数
    - 如果该倍数 小于等于 1.2，则照此加速音频即可，无需视频慢速
    - 如果该倍数 大于1.2，则音频加速和视频慢速各自负担一半,忽略所有限制

## 仅仅使用音频加速时

1. 如果配音时长 小于 当前片段的原始字幕时长，则无需音频加速
2. 如果配音时长 大于 当前片段的原始字幕时长，强制将配音时长缩短到匹配时长，倍数最大不超过预定最大限制
3. 注意开头和结尾以及字幕之间的静默区间，尤其是利用后可能还剩余的静默空间，最终合成后的音频长度，在存在视频时(self.novoice_mp4) 长度应等于视频长度，在不存在时，长度应不小于 self.raw_total_time。

## 仅仅视频慢速时
1. 如果配音时长 小于 当前片段的原始字幕时长，则无需视频慢速，直接从本条字幕开始时间裁切到下条字幕开始时间，如果这是第一条字幕，则从0时间开始裁切
2. 如果配音时长 大于 当前片段的原始字幕时长，强制将视频片段(时长为total_a) 慢速延长到和配音等长，此处注意下，PTS倍数最大不超过 max_video_pts_rate。
3. 裁切需注意第一条字幕前的区域(开始时间可能大于0)和最后一条字幕后的区域(结束时间可能不到视频末尾)
4. 无需慢速处理的片段，直接裁切本条字幕开始时间到下条字幕开始时间。


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

## 在无视频慢速参与情况下，按照配音，整理字幕时间轴，确保声音和字幕同时显示与消失
## 在有视频慢速参与情况下，将配音片段同视频片段挨个对齐，如果配音片段短于当前视频片段，补充静音，如果大于，则无视，继续拼接，字幕时间轴以配音为准显示
===============================================================================================

## 需要注意的点
1. ffmpeg处理视频是无法精确到毫秒级的，因此使用PTS进行慢速时，最终输出的视频可能会短于或长于期望的时长
2. fps是不固定的，可能是25，可能是29或30等，某些片段时长可能小于1帧，如果FFmpeg进行变速处理，大概率会失败，因此在有音频加速或视频慢速参与时，应该提前将当前字幕和下条字幕的空隙都给当前字幕，即当前字幕的结束时间改为下条字幕的开始时间

"""

import math
import json
import os
import shutil
import time
import re
import subprocess
import random
from pathlib import Path
import threading

# 引入 soundfile 和 audio 处理
import soundfile as sf
import numpy as np  # 新增 numpy 用于声道处理
from pydub import AudioSegment

# 尝试导入 pyrubberband
try:
    import pyrubberband as pyrb
    HAS_RUBBERBAND = True
except ImportError:
    HAS_RUBBERBAND = False

from videotrans.configure import config
from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang
from videotrans.process.signelobj import GlobalProcessManager
from videotrans.util import tools


def _cut_video_get_duration(i, task, novoice_mp4_original, preset, crf):
    """
    裁切视频片段，并根据需要进行慢速（PTS）处理。
    """
    task['actual_duration'] = 0 
    
    # 强制使用绝对路径
    input_video_path = Path(novoice_mp4_original).resolve().as_posix()
    
    # 原始片段时长
    source_duration_ms = task['end'] - task['start']
    if source_duration_ms <= 0:
        logger.warning(f"[Video-Cut] 片段{i} 原始时长<=0 ({task['start']}-{task['end']})，跳过处理")
        return task

    # 目标时长
    target_duration_ms = task.get('target_time', source_duration_ms)
    
    ss_time = tools.ms_to_time_string(ms=task['start'], sepflag='.')
    source_duration_s = source_duration_ms / 1000.0
    target_duration_s = target_duration_ms / 1000.0
    
    # PTS 系数
    pts_factor = task.get('pts', 1.0)
    
    flag = f'[Video-Cut] 片段{i} [原:{task["start"]}-{task["end"]}ms] [目标:{target_duration_ms}ms] [PTS:{pts_factor:.4f}]'
    logger.debug(f"{flag} 准备开始处理...")

    # 主命令构建
    cmd = [
        '-y',
        '-ss', ss_time,
        '-t', f'{source_duration_s:.6f}',
        '-i', input_video_path, # 使用绝对路径
        '-an',
        '-c:v', 'libx264', 
        '-g', '1',
        '-preset', preset, 
        '-crf', crf,
        '-pix_fmt', 'yuv420p'
    ]

    filter_complex = []
    if abs(pts_factor - 1.0) > 0.01:
        filter_complex.append(f"setpts={pts_factor}*PTS")
    else:
        filter_complex.append("setpts=PTS")

    cmd.extend(['-vf', ",".join(filter_complex)])
    cmd.extend(['-fps_mode', 'vfr']) # 关键修正
    cmd.extend(['-t', f'{target_duration_s:.6f}']) # 强制限制输出时长
    
    cmd.append(os.path.basename(task['filename']))

    # 获取工作目录（用于存放临时文件）
    work_dir = Path(task['filename']).parent.as_posix()
    
    try:
        # 执行 FFmpeg
        tools.runffmpeg(cmd, force_cpu=True, cmd_dir=work_dir)
        
        file_path = Path(task['filename'])
        
        # 检查是否成功，如果失败则执行兜底逻辑
        if not file_path.exists() or file_path.stat().st_size < 1024:
            logger.warning(f"{flag} 变速生成失败或文件无效，尝试无变速剪切兜底...")
            
            # 【修正】兜底命令也必须包含 fps_mode 和 setpts=PTS 以保证拼接兼容性
            cmd_backup = [
                '-y', 
                '-ss', ss_time, 
                '-t', f'{source_duration_s:.6f}', # 兜底使用原始时长
                '-i', input_video_path,
                '-an', 
                '-c:v', 'libx264', 
                '-g', '1',
                '-preset', preset, 
                '-crf', crf,
                '-pix_fmt', 'yuv420p',
                '-vf', 'setpts=PTS',  # 显式添加
                '-fps_mode', 'vfr',   # 显式添加
                os.path.basename(task['filename'])
            ]
            tools.runffmpeg(cmd_backup, force_cpu=True, cmd_dir=work_dir)

        # 再次检查
        if file_path.exists() and file_path.stat().st_size >= 1024:
            try:
                real_time = tools.get_video_duration(task["filename"])
            except Exception as e:
                logger.error(f"{flag} 获取时长失败: {e}")
                real_time = 0

            task['actual_duration'] = real_time
            logger.debug(f"{flag} 完成。实际生成时长: {real_time}ms")
        else:
            task['actual_duration'] = 0
            logger.error(f"{flag} 最终生成失败。")
            
    except Exception as e:
        logger.error(f"{flag} 处理异常: {e}")
        try:
            if Path(task['filename']).exists():
                Path(task['filename']).unlink()
        except:
            pass
            
    return task


def _change_speed_rubberband(input_path, target_duration):
    """
    使用 Rubber Band 进行音频变速
    """
    if not HAS_RUBBERBAND:
        logger.warning(f"[Audio-RB] Rubberband 未安装，跳过: {input_path}")
        return

    try:
        y, sr = sf.read(input_path)
        if len(y) == 0:
            logger.warning(f"[Audio-RB] 空音频文件: {input_path}")
            return
            
        current_duration = int((len(y) / sr) * 1000)
        
        if target_duration <= 0: target_duration = 1
        
        # 【逻辑优化】如果目标时长比当前还长，说明需要音频慢放。
        # 但在当前的对齐策略中，音频通常只压缩（加速）。
        # 如果确实发生了 target > current，通常意味着我们应该填充静音而不是拉伸音频。
        # 这里为了安全，如果差异过大，不做处理。
        if target_duration > current_duration:
             # 允许微小的误差，或者由后续静音填充处理
             logger.debug(f"[Audio-RB] 目标时长({target_duration}) > 当前时长({current_duration})，跳过变速，交由静音填充。")
             return

        time_stretch_rate = current_duration / target_duration
        
        # 限制范围
        time_stretch_rate = max(0.2, min(time_stretch_rate, 50.0))
        
        logger.debug(f"[Audio-RB] {input_path} 原长:{current_duration}ms -> 目标:{target_duration}ms 倍率:{time_stretch_rate:.2f}")

        y_stretched = pyrb.time_stretch(y, sr, time_stretch_rate)
        
        # 【关键修正】确保输出是 Stereo (2通道)，防止后续 ffmpeg concat 报错
        # 如果是单声道 (ndim=1)，复制为双声道
        if y_stretched.ndim == 1:
            y_stretched = np.column_stack((y_stretched, y_stretched))
        
        sf.write(input_path, y_stretched, sr)
        
    except Exception as e:
        logger.error(f"[Audio-RB] 音频处理失败 {input_path}: {e}")


class SpeedRate:
    MIN_CLIP_DURATION_MS = 40
    AUDIO_SAMPLE_RATE = 48000
    AUDIO_CHANNELS = 2

    def __init__(self,
                 *,
                 queue_tts=None,
                 shoud_videorate=False,
                 shoud_audiorate=False,
                 uuid=None,
                 novoice_mp4=None,
                 raw_total_time=0,
                 target_audio=None,
                 cache_folder=None,
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
            f'{TEMP_DIR}/{str(uuid if uuid else time.time())}').as_posix()
        Path(self.cache_folder).mkdir(parents=True, exist_ok=True)

        self.stop_show_process = False
        self.video_info = {}
        self.target_audio = target_audio

        self.max_audio_speed_rate = float(settings.get('max_audio_speed_rate', 100))
        self.max_video_pts_rate = float(settings.get('max_video_pts_rate', 10))

        self.audio_data = [] 
        self.video_for_clips = [] 

        self.crf = "20"
        self.preset = "veryfast"
        
        try:
            if Path(ROOT_DIR + "/crf.txt").exists():
                self.crf = str(int(Path(ROOT_DIR + "/crf.txt").read_text()))
            if Path(ROOT_DIR + "/preset.txt").exists():
                preset_tmp = str(Path(ROOT_DIR + "/preset.txt").read_text().strip())
                if preset_tmp in ['ultrafast', 'veryfast', 'medium', 'slow']:
                    self.preset = preset_tmp
        except:
            pass

        self.audio_speed_rubberband = shutil.which("rubberband")
        logger.debug(f"[SpeedRate] Init. AudioRate={self.shoud_audiorate}, VideoRate={self.shoud_videorate}, Rubberband={bool(self.audio_speed_rubberband)}")

    def run(self):
        if not self.shoud_audiorate and not self.shoud_videorate:
            logger.debug("[SpeedRate] 未启用变速，进入普通拼接模式。")
            self._run_no_rate_change_mode()
            return self.queue_tts
        
        logger.debug("[SpeedRate] 启用变速，进入对齐模式。")
        
        # 1. 预处理
        self._prepare_data()
        
        # 2. 计算
        self._calculate_adjustments()
        
        # 3. 音频变速
        if self.audio_data:
            tools.set_process(text='Processing audio speed...', uuid=self.uuid)
            if HAS_RUBBERBAND and self.audio_speed_rubberband:
                self._execute_audio_speedup_rubberband()
            else:
                 logger.warning("[SpeedRate] Rubberband 不可用，跳过音频物理变速。")
        
        # 4. 视频变速
        if self.shoud_videorate and self.video_for_clips:
            tools.set_process(text='Processing video speed...', uuid=self.uuid)
            processed_video_clips = self._video_speeddown()
            
            # 回写
            for clip in processed_video_clips:
                real_duration = clip.get('actual_duration', 0)
                tts_idx = clip.get('tts_index')
                if tts_idx is not None and 0 <= tts_idx < len(self.queue_tts):
                    # 【关键】这就是最终的视频槽位长度
                    self.queue_tts[tts_idx]['final_duration'] = real_duration
            
            self._concat_video(processed_video_clips)
            
            # 更新总时长
            if Path(self.novoice_mp4).exists():
                try:
                    self.raw_total_time = tools.get_video_duration(self.novoice_mp4)
                    logger.debug(f"[SpeedRate] 新视频生成完毕，总时长: {self.raw_total_time}ms")
                except: pass
        else:
            # 不变视频，时长为原槽位时长
            for it in self.queue_tts:
                it['final_duration'] = it['source_duration']
            
        # 5. 音频对齐拼接
        tools.set_process(text='Concatenating final audio...', uuid=self.uuid)
        self._concat_audio_aligned()

        return self.queue_tts

    def _prepare_data(self):
        """数据清洗与预处理"""
        tools.set_process(text="Preparing data...", uuid=self.uuid)
        
        if self.novoice_mp4_original and tools.vail_file(self.novoice_mp4_original):
            self.raw_total_time = tools.get_video_duration(self.novoice_mp4_original)

        for i in range(len(self.queue_tts)):
            current = self.queue_tts[i]
            # 保存原始时间轴，供恢复使用
            current['original_start'] = current['start_time']
            current['original_end'] = current['end_time']

            if i == 0:
                # 有视频慢速并且小于50ms，置为 从0开始，防止短视频片段出错
                current['start_time_source'] = current['start_time'] if not self.shoud_videorate or current['start_time']>50 else 0
            else:
                current['start_time_source'] = self.queue_tts[i-1]['end_time_source']
            
            # 填补空隙
            if i < len(self.queue_tts) - 1:
                next_sub = self.queue_tts[i+1]
                current['end_time_source'] = next_sub['start_time']
                current['end_time'] = next_sub['start_time']
            else:
                current['end_time_source'] = self.raw_total_time
                current['end_time'] = self.raw_total_time

            current['source_duration'] = current['end_time_source'] - current['start_time_source']
            
            # 检查配音文件
            if not current.get('filename') or not Path(current['filename']).exists():
                # 生成占位静音
                dummy_wav = Path(self.cache_folder, f'silent_place_{i}.wav').as_posix()
                # 时长至少100ms，或者等于 source_duration 以防太短
                dur = max(50, current['source_duration'])
                AudioSegment.silent(duration=dur).export(dummy_wav, format="wav")
                current['filename'] = dummy_wav
                current['dubb_time'] = dur
                logger.debug(f"[Prepare] 字幕[{current['line']}] 无配音，生成 {dur}ms 静音占位")
            else:
                current['dubb_time'] = len(AudioSegment.from_file(current['filename']))

    def _calculate_adjustments(self):
        """计算策略"""
        tools.set_process(text="Calculating sync adjustments...", uuid=self.uuid)
        
        for i, it in enumerate(self.queue_tts):
            source_dur = it['source_duration']
            dubb_dur = it['dubb_time']
            
            if self.shoud_videorate and source_dur <= 0:
                logger.warning(f"[Calc] 字幕[{it['line']}] 视频槽位<=0，跳过")
                self.video_for_clips.append({
                    "start": 0, "end": 0, "target_time": 0, "pts": 1,
                    "tts_index": i, "filename": ""
                })
                continue
            if source_dur<=0:
                continue

            video_target = source_dur
            audio_target = dubb_dur
            
            mode_log = ""
            # 仅音频加速
            if self.shoud_audiorate and not self.shoud_videorate:
                mode_log = "Only Audio"
                if dubb_dur > source_dur:
                    ratio = dubb_dur / source_dur
                    if ratio > self.max_audio_speed_rate:
                        audio_target = int(dubb_dur / self.max_audio_speed_rate)
                    else:
                        audio_target = source_dur

            elif not self.shoud_audiorate and self.shoud_videorate:
                mode_log = "Only Video"
                if dubb_dur > source_dur:
                    video_target = dubb_dur
                    pts = video_target / source_dur
                    if pts > self.max_video_pts_rate:
                        video_target = int(source_dur * self.max_video_pts_rate)

            elif self.shoud_audiorate and self.shoud_videorate:
                mode_log = "Both"
                if dubb_dur > source_dur:
                    ratio = dubb_dur / source_dur
                    if ratio <= 1.2:
                        audio_target = source_dur
                        video_target = source_dur
                    else:
                        diff = dubb_dur - source_dur
                        joint_target = int(source_dur + (diff / 2))
                        audio_target = joint_target
                        video_target = joint_target
            


            # 注册任务
            if self.shoud_audiorate and audio_target < dubb_dur:
                self.audio_data.append({
                    "filename": it['filename'],
                    "dubb_time": dubb_dur,
                    "target_time": audio_target
                })
            
            if self.shoud_videorate:
                pts = video_target / source_dur if source_dur > 0 else 1.0
                self.video_for_clips.append({
                    "start": it['start_time_source'],
                    "end": it['end_time_source'],
                    "target_time": video_target,
                    "pts": pts,
                    "tts_index": i,
                    "line": it['line']
                })
            
                it['final_duration'] = video_target
            # 记录决策日志
            logger.debug(f"[Calc] Mode={mode_log} Line={it['line']} | Source={source_dur} Dubb={dubb_dur} -> TargetV={video_target} TargetA={audio_target}")


    def _execute_audio_speedup_rubberband(self):
        logger.debug(f"[Audio] 开始处理 {len(self.audio_data)} 个音频变速任务")
        all_task = []
        for d in self.audio_data:
            all_task.append(GlobalProcessManager.submit_task_cpu(
                _change_speed_rubberband, 
                input_path=d['filename'], 
                target_duration=d['target_time']
            ))
        for task in all_task:
            try: task.result()
            except: pass

    def _video_speeddown(self):
        data = []
        for i, clip_info in enumerate(self.video_for_clips):
            clip_info['queue_index'] = i 
            clip_info['filename'] = Path(self.cache_folder, f"clip_{i}_{clip_info['pts']:.3f}.mp4").as_posix()
            data.append(clip_info)
            
        all_task = []
        logger.debug(f"[Video] 提交 {len(data)} 个视频处理任务")
        for i, d in enumerate(data):
            kw = {
                "i": i, 
                "task": d, 
                "novoice_mp4_original": self.novoice_mp4_original, 
                "preset": self.preset, 
                "crf": self.crf
            }
            all_task.append(GlobalProcessManager.submit_task_cpu(_cut_video_get_duration, **kw))

        processed_clips = []
        for task in all_task:
            try:
                res = task.result()
                if res: processed_clips.append(res)
            except Exception as e:
                logger.error(f"[Video] 任务异常: {e}")
        
        processed_clips.sort(key=lambda x: x.get('queue_index', 0))
        return processed_clips

    def _concat_video(self, processed_clips):
        txt_content = []
        valid_cnt = 0
        for clip in processed_clips:
            if clip.get('actual_duration', 0) > 0 and Path(clip['filename']).exists():
                path = clip['filename'].replace("\\", "/")
                txt_content.append(f"file '{path}'")
                valid_cnt += 1
            else:
                logger.warning(f"[Video-Concat] 忽略无效片段: {clip.get('filename')}")
        
        if valid_cnt == 0: 
            logger.error("[Video-Concat] 没有有效片段，跳过拼接")
            return

        concat_list = Path(self.cache_folder, "video_concat.txt").as_posix()
        with open(concat_list, 'w', encoding='utf-8') as f:
            f.write("\n".join(txt_content))
            
        output_path = Path(self.cache_folder, "merged_video.mp4").as_posix()
        logger.debug(f"[Video-Concat] 合并 {valid_cnt} 个片段 -> {output_path}")
        
        cmd = ['-y', '-f', 'concat', '-safe', '0', '-i', concat_list, '-c', 'copy', output_path]
        tools.runffmpeg(cmd, force_cpu=True, cmd_dir=self.cache_folder)

        if Path(output_path).exists():
            shutil.move(output_path, self.novoice_mp4)

    def _concat_audio_aligned(self):
        logger.debug("[Audio] 开始对齐拼接...")
        audio_list = []
        current_timeline = 0
        
        for i, it in enumerate(self.queue_tts):
            # 有视频慢速时，使用视频片段实际时长，否则使用字幕区间时长
            slot_duration = it.get('final_duration', it['source_duration'])
            
            # 【兜底修正】如果视频槽位失效（0ms），回退到 source_duration
            # 这样至少保证音频不会因为视频失败而全部乱掉，保持音频连续性
            if slot_duration <= 0:
                logger.warning(f"[Audio-Sync] 字幕[{it['line']}] 视频槽时长为0，回退使用原始时长: {it['source_duration']}ms")
                slot_duration = max(1, it['source_duration'])

            slot_audio_parts = []
            current_slot_audio_len = 0
            
            # 1. 前导静音处理
            original_offset = it['original_start'] - it['start_time_source']
            if original_offset > 0:
                # 按视频变速比例缩放前导静音
                if it['source_duration'] > 0 and self.shoud_videorate:
                    pts = slot_duration / it['source_duration']
                    # 【修正】只允许延长 (pts >= 1)，避免因为压缩过大导致静音消失
                    pts = max(1.0, pts)
                    offset_scaled = int(original_offset * pts)
                else:
                    offset_scaled = original_offset
                
                if offset_scaled > 0:
                    slot_audio_parts.append(self._create_silen_file(f"pre_{i}", offset_scaled))
                    current_slot_audio_len += offset_scaled

            # 2. 配音文件
            audio_file = it['filename']
            if Path(audio_file).exists():
                try:
                    seg = AudioSegment.from_file(audio_file)
                    if seg.channels != self.AUDIO_CHANNELS:
                        seg = seg.set_channels(self.AUDIO_CHANNELS)
                        seg.export(audio_file, format='wav')
                    
                    slot_audio_parts.append(audio_file)
                    current_slot_audio_len += len(seg)
                except Exception as e:
                    logger.error(f"[Audio-Sync] 读取配音失败 {audio_file}: {e}")
            
            # 3. 长度对其
            log_flag = ""
            if current_slot_audio_len > slot_duration:
                # 溢出截断音频，有视频慢速时，最终生成的视频可能比理论需要的短几十ms
                log_flag = f"音频溢出截断 {current_slot_audio_len}->{slot_duration}"
                combined_path = self._merge_audio_parts(slot_audio_parts, f"temp_slot_{i}")
                
                try:
                    cut_seg = AudioSegment.from_file(combined_path)[:slot_duration]
                    final_slot_path = Path(self.cache_folder, f"final_slot_cut_{i}.wav").as_posix()
                    cut_seg.export(final_slot_path, format='wav')
                    audio_list.append(final_slot_path)
                except Exception as e:
                    logger.error(f"截断音频失败: {e}")
                    audio_list.append(combined_path) # 失败则原样放入

            elif current_slot_audio_len < slot_duration:
                # 补尾部静音
                diff = slot_duration - current_slot_audio_len
                log_flag = f"音频末尾补静音 {diff}ms"
                audio_list.extend(slot_audio_parts)
                audio_list.append(self._create_silen_file(f"tail_{i}", diff))
            else:
                log_flag = "匹配"
                audio_list.extend(slot_audio_parts)

            logger.debug(f"[Audio-Sync] Line={it['line']} | {log_flag} | [{current_slot_audio_len=} {slot_duration=}] | Timeline: {current_timeline} -> {current_timeline+slot_duration}")

            it['start_time'] = current_timeline
            it['end_time'] = current_timeline + slot_duration
            current_timeline += slot_duration

        self._exec_concat_audio(audio_list)

    def _merge_audio_parts(self, file_list, name):
        """临时合并"""
        if len(file_list) == 1:
            return file_list[0]
        
        output = Path(self.cache_folder, f"{name}.wav").as_posix()
        combined = AudioSegment.empty()
        for f in file_list:
            combined += AudioSegment.from_file(f)
        combined.export(output, format="wav")
        
        # 【修正】清理可能的临时文件（如果是 pre_ 或 tail_ 生成的）
        # 这里逻辑较复杂，暂时只清理 file_list 中明显带有 temp 标记的，或者依赖 cache 统一清理
        return output

    def _run_no_rate_change_mode(self):
        # 不变速时直接拼接
        tools.set_process(text=tr("Merging audio (No Speed Change)..."), uuid=self.uuid)
        
        audio_concat_list = []
        total_audio_duration = 0

        for i, it in enumerate(self.queue_tts):

            prev_end = 0 if i == 0 else self.queue_tts[i-1].get('end_pos_for_concat', 0)
            start_time = it['start_time']
            # 前面静音区间
            gap = start_time - prev_end
            
            if not self.remove_silent_mid and gap > 0:
                audio_concat_list.append(self._create_silen_file(f"gap_{i}", gap))
                total_audio_duration += gap
            
            dubb_len = 0
            if it.get('filename') and Path(it['filename']).exists():
                audio_concat_list.append(it['filename'])
                dubb_len = len(AudioSegment.from_file(it['filename']))
            elif it.get('filename'):
                dur = max(0, it['end_time'] - it['start_time'])
                if dur > 0:
                    audio_concat_list.append(self._create_silen_file(f"sub_{i}", dur))
                    dubb_len = dur
            
            total_audio_duration += dubb_len
            it['end_pos_for_concat'] = total_audio_duration
            
            if self.align_sub_audio:
                it['start_time'] = total_audio_duration - dubb_len
                it['end_time'] = total_audio_duration

        if self.raw_total_time > total_audio_duration:
            audio_concat_list.append(self._create_silen_file("tail_end", self.raw_total_time - total_audio_duration))

        self._exec_concat_audio(audio_concat_list)

    def _create_silen_file(self, name, duration_ms):
        path = Path(self.cache_folder, f"silence_{name}.wav").as_posix()
        duration_ms = max(1, int(duration_ms))
        AudioSegment.silent(duration=duration_ms, frame_rate=self.AUDIO_SAMPLE_RATE) \
                    .set_channels(self.AUDIO_CHANNELS) \
                    .export(path, format="wav")
        return path

    def _exec_concat_audio(self, file_list):
        if not file_list: return
        
        concat_txt = Path(self.cache_folder, 'final_audio_concat.txt').as_posix()
        tools.create_concat_txt(file_list, concat_txt=concat_txt)
        
        temp_wav = Path(self.cache_folder, 'final_audio_temp.wav').as_posix()
        # 强制使用 cache_folder 作为 cwd，避免相对路径问题
        cmd = ['-y', '-f', 'concat', '-safe', '0', '-i', concat_txt, '-c:a', 'copy', temp_wav]
        tools.runffmpeg(cmd, force_cpu=True, cmd_dir=self.cache_folder)
        
        if Path(temp_wav).exists():
            shutil.move(temp_wav, self.target_audio)
            logger.debug(f"[Audio-Concat] 最终音频已生成: {self.target_audio}")
        else:
            logger.error("[Audio-Concat] 最终音频生成失败")


# 专门针对 为字幕配音 单独处理
class TtsSpeedRate(SpeedRate):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.shoud_videorate=False
        self.max_audio_speed_rate=100


    def run(self):
        if not self.shoud_audiorate:
            logger.debug("[SpeedRate] 未启用变速，进入普通拼接模式。")
            self._run_no_rate_change_mode()
            return self.queue_tts
        # 删除时间轴不合法的
        self.queue_tts=[it for it in self.queue_tts if it['end_time']-it['start_time']>0]

        logger.debug("[SpeedRate] 启用变速，进入对齐模式。")

        # 1. 预处理
        self._prepare_data()

        # 2. 计算
        self._calculate_adjustments()

        # 3. 音频变速
        if self.audio_data:
            tools.set_process(text='Processing audio speed...', uuid=self.uuid)
            if HAS_RUBBERBAND and self.audio_speed_rubberband:
                self._execute_audio_speedup_rubberband()
            else:
                 logger.warning("[SpeedRate] Rubberband 不可用，跳过音频物理变速。")

        tools.set_process(text='Concatenating final audio...', uuid=self.uuid)
        self._concat_audio_aligned()

        return self.queue_tts

    def _prepare_data(self):
        """数据清洗与预处理"""
        tools.set_process(text="Preparing data...", uuid=self.uuid)

        for i in range(len(self.queue_tts)):
            current = self.queue_tts[i]
            # 保存原始时间轴，供恢复使用
            current['original_start'] = current['start_time']
            current['original_end'] = current['end_time']

            current['start_time_source'] = current['start_time'] if i == 0 else self.queue_tts[i-1]['end_time_source']

            # 填补空隙
            if i < len(self.queue_tts) - 1:
                next_sub = self.queue_tts[i+1]
                current['end_time_source'] = next_sub['start_time']
                current['end_time'] = next_sub['start_time']
            else:
                current['end_time_source'] = self.raw_total_time
                current['end_time'] = self.raw_total_time

            current['source_duration'] = current['end_time_source'] - current['start_time_source']

            # 检查配音文件
            if not current.get('filename') or not Path(current['filename']).exists():
                # 生成占位静音
                dummy_wav = Path(self.cache_folder, f'silent_place_{i}.wav').as_posix()
                # 时长至少100ms，或者等于 source_duration 以防太短
                AudioSegment.silent(duration=current['source_duration']).export(dummy_wav, format="wav")
                current['filename'] = dummy_wav
                current['dubb_time'] = current['source_duration']
                logger.debug(f"[Prepare] 字幕[{current['line']}] 无配音，生成 {current['source_duration']}ms 静音占位")
            else:
                current['dubb_time'] = len(AudioSegment.from_file(current['filename']))

    def _calculate_adjustments(self):
        """计算策略"""
        tools.set_process(text="Calculating sync adjustments...", uuid=self.uuid)

        for i, it in enumerate(self.queue_tts):
            source_dur = it['source_duration']
            dubb_dur = it['dubb_time']
            audio_target = dubb_dur

            # 仅音频加速
            mode_log = f"[为字幕配音] {i=}"
            if dubb_dur > source_dur:
                ratio = dubb_dur / source_dur
                if ratio > self.max_audio_speed_rate:
                    audio_target = int(dubb_dur / self.max_audio_speed_rate)
                else:
                    audio_target = source_dur

            # 注册任务
            if audio_target < dubb_dur:
                self.audio_data.append({
                    "filename": it['filename'],
                    "dubb_time": dubb_dur,
                    "target_time": audio_target
                })

            logger.debug(f"[Calc] Mode={mode_log} Line={it['line']} | Source={source_dur} Dubb={dubb_dur} -> TargetA={audio_target}")


    def _concat_audio_aligned(self):
        logger.debug("[Audio] 开始对齐拼接...")

        audio_concat_list = []
        total_audio_duration = 0

        # 恢复原始时间轴
        for it in self.queue_tts:
            it['start_time']=it['original_start']
            it['end_time']=it['original_end']
            it['source_duration']=it['end_time']-it['start_time']

        for i, it in enumerate(self.queue_tts):
            prev_end = 0 if i == 0 else self.queue_tts[i-1].get('end_pos_for_concat', 0)
            start_time = it['start_time']
            gap = start_time - prev_end

            # 添加前导静音
            if gap > 0:
                audio_concat_list.append(self._create_silen_file(f"gap_{i}", gap))
                total_audio_duration += gap

            # 真实配音时长
            if it.get('filename') and Path(it['filename']).exists():
                audio_concat_list.append(it['filename'])
                dubb_len = len(AudioSegment.from_file(it['filename']))
            else:
                audio_concat_list.append(self._create_silen_file(f"sub_{i}", it['source_duration']))
                dubb_len = it['source_duration']
            # 如果真实配音短于字幕区间，末尾添加静音
            if dubb_len<it['source_duration']:
                audio_concat_list.append(self._create_silen_file(f"end_{i}", it['source_duration']-dubb_len))
                dubb_len=it['source_duration']


            total_audio_duration += dubb_len
            it['end_pos_for_concat'] = total_audio_duration


        if self.raw_total_time > total_audio_duration:
            audio_concat_list.append(self._create_silen_file("tail_end", self.raw_total_time - total_audio_duration))

        self._exec_concat_audio(audio_concat_list)

