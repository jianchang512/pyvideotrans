# 原理解释见 @docs/Synchronize.md
"""
# 2026-0923 修改

视频慢速 + 音频加速，单选或全选，进行同步处理

 - 因 【视频慢速】处理无法精确到ms，每个片段会存在 几十ms到几百ms 的误差，随着视频时长增长，误差越来越大，为弥补该误差，先执行【视频慢速】处理，再根据真实视频片段时长，执行配音变速处理，当使用 pyrubberband 扩展处理音频时，误差最终可消除为0

- 若同时选中【音频加速】，实际视频和音频变速幅度均为约一半。

---

处理之前，会将所有字幕开始和结束时刻设为首尾相连，并将第一条字幕开始时间强制设为0，以便吞并可能存在的开始短片段，方便处理。
在最终处理完毕后合并音频前，再判断如果第1条配音时长短语第一条视频片段，则音频左侧再补充静音，防止某些类似 第 3秒才开始的音频错误的第0秒开始

"""

import os
import shutil
import time
from pathlib import Path

# 引入 soundfile 和 audio 处理
import soundfile as sf
import numpy as np  # 新增 numpy 用于声道处理
from pydub import AudioSegment

# 尝试导入 pyrubberband
from videotrans.configure.constants import INSTALL_RUBBERBAND_TIPS

try:
    import pyrubberband as pyrb

    HAS_RUBBERBAND = True
except ImportError:
    HAS_RUBBERBAND = False

from videotrans.configure.config import ROOT_DIR, tr, settings, logger
from videotrans.configure import config
from videotrans.util import tools
from concurrent.futures import ProcessPoolExecutor


def _cut_video_get_duration(task, novoice_mp4_original, preset, crf, fps_mode):
    """
    裁切视频片段，并根据需要进行慢速（PTS）处理。
    """
    # 变速后实际时长 ms
    task['actual_duration'] = 0

    # 强制使用绝对路径
    input_video_path = Path(novoice_mp4_original).resolve().as_posix()

    # 需要裁切的原始片段起始
    source_duration_ms = task['end'] - task['start']
    if source_duration_ms <= 0:
        logger.error(f"[Video-Cut] 片段{task.get('tts_index')} 原始时长<=0: {task=}，跳过处理")
        return task
    source_duration_s = source_duration_ms / 1000.0

    # 目标时长 ms
    target_duration_ms = task.get('target_time', source_duration_ms)
    ss_time = tools.ms_to_time_string(ms=task['start'], sepflag='.')

    # PTS 系数
    pts_factor = task.get('pts', 1.0)

    flag = f'[Video-Cut] 字幕{task.get("tts_index")}: 裁切时长={source_duration_ms}ms,  PTS={pts_factor}, 变速目标时长={target_duration_ms}ms'

    # 主命令构建
    cmd = [
        '-y',
        '-ss', ss_time,
        '-t', f'{source_duration_s:.6f}',
        '-i', input_video_path,  # 使用绝对路径
        '-an',
        '-c:v', 'libx264',
        '-g', '1',
        '-preset', preset,
        '-crf', crf,
        '-pix_fmt', 'yuv420p'
    ]

    cmd.extend(fps_mode)
    cmd.append(os.path.basename(task['filename']))
    # 获取工作目录（用于存放临时文件）
    work_dir = Path(task['filename']).parent.as_posix()
    try:
        # 执行 FFmpeg
        tools.runffmpeg(cmd, force_cpu=True, cmd_dir=work_dir)
        file_path = Path(task['filename'])
        # 检查是否成功，如果失败则执行兜底逻辑
        if not file_path.exists() or file_path.stat().st_size < 1024:
            logger.error(f"{flag} 变速生成失败或文件无效，尝试无变速剪切兜底:{task=}...")

            # 【修正】兜底命令也必须包含 fps_mode 和 setpts=PTS 以保证拼接兼容性
            cmd_backup = [
                             '-y',
                             '-ss', ss_time,
                             '-t', f'{source_duration_s:.6f}',  # 兜底使用原始时长
                             '-i', input_video_path,
                             '-an',
                             '-c:v', 'libx264',
                             '-g', '1',
                             '-preset', preset,
                             '-crf', crf,
                             '-pix_fmt', 'yuv420p',
                             '-vf', 'setpts=PTS',  # 显式添加
                         ] + fps_mode

            cmd_backup.append(os.path.basename(task['filename']))
            tools.runffmpeg(cmd_backup, force_cpu=True, cmd_dir=work_dir)

        # 再次检查
        if file_path.exists() and file_path.stat().st_size >= 1024:
            try:
                real_time = tools.get_video_duration(task["filename"])
            except Exception as e:
                logger.error(f"{flag} 获取视频片段时长失败，对齐可能偏差: {e}")
                real_time = source_duration_ms

            task['actual_duration'] = real_time
            logger.debug(f"{flag}, 变速后实际时长: {real_time}ms, 实际时长-目标时长={real_time - target_duration_ms}ms")
        else:
            task['actual_duration'] = 0
            logger.error(f"{flag} 最终生成失败。")
    except Exception as e:
        logger.error(f"{flag} 处理异常: {e}")
        try:
            if Path(task['filename']).exists():
                Path(task['filename']).unlink()
        except OSError:
            pass

    return task


def _change_speed_rubberband(input_path, target_duration):
    """
    使用 Rubber Band 进行音频变速
    """
    try:
        y, sr = sf.read(input_path)
        if len(y) == 0:
            logger.error(f"[rubberband] 空音频文件: {input_path=},{target_duration=}")
            return False

        current_duration = round((len(y) / sr) * 1000)

        if target_duration <= 0: target_duration = 1

        if target_duration >= current_duration:
            return False

        time_stretch_rate = current_duration / target_duration

        # 限制范围
        time_stretch_rate = max(0.2, min(time_stretch_rate, 50.0))

        logger.debug(
            f"[rubberband] {input_path} 配音时长:{current_duration}ms, 目标时长:{target_duration}ms 倍率:{time_stretch_rate:.2f}")

        y_stretched = pyrb.time_stretch(y, sr, time_stretch_rate)

        # 如果是单声道 (ndim=1)，复制为双声道
        if y_stretched.ndim == 1:
            y_stretched = np.column_stack((y_stretched, y_stretched))

        sf.write(input_path, y_stretched, sr)

    except Exception as e:
        logger.error(f"[rubberband] 音频处理失败 {input_path}: {e}")
        return False
    return True


def _precise_speed_up_audio(input_path=None, target_duration=None):
    # 使用 pydub 获取当前时长（避免双重读取）
    current_duration_ms = len(AudioSegment.from_file(input_path, format='wav'))

    # 构造 atempo 滤镜链
    # atempo 限制：参数必须在 [0.5, 2.0] 之间
    atempo_list = []
    speed_factor = current_duration_ms / target_duration
    logger.debug(
        f"[ffmpeg atempo] {input_path} 配音时长:{current_duration_ms}ms, 目标时长:{target_duration}ms, 倍率:{speed_factor:.2f}")

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
        '-i',
        input_path,
        '-filter:a',
        filter_str,
        '-t', f"{target_duration / 1000.0}",  # 强制裁剪到目标时长，防止精度误差
        '-ar', "48000",
        '-ac', "2",
        '-c:a', 'pcm_s16le',
        f'{input_path}-after.wav'
    ]
    try:
        tools.runffmpeg(cmd)
        shutil.copy2(f'{input_path}-after.wav', input_path)
    except Exception as e:
        logger.exception(f'音频加速atempo失败:{e}')
        return False
    return True


class SpeedRate:
    MIN_CLIP_DURATION_MS = 40
    AUDIO_SAMPLE_RATE = 48000
    AUDIO_CHANNELS = 2
    # 音频和视频同时启用时，如果配音/字幕倍率低于此阈值，仅加速音频，不慢速视频
    BOTH_MODE_AUDIO_ONLY_THRESHOLD = 1.2

    def __init__(self,
                 *,
                 queue_tts=None,
                 should_videorate=False,
                 should_audiorate=False,
                 uuid=None,
                 novoice_mp4=None,
                 raw_total_time=0,
                 target_audio=None,
                 cache_folder=None,
                 remove_silent_mid=False,
                 align_sub_audio=True
                 ):
        self.align_sub_audio = align_sub_audio
        self.remove_silent_mid = remove_silent_mid
        # 原始视频时长 ms
        self.raw_total_time = raw_total_time if raw_total_time is not None else 0
        self.queue_tts = queue_tts
        self.len_queue = len(queue_tts)
        # 是否选中了 视频慢速
        self.should_videorate = should_videorate
        # 是否选中了 音频加速
        self.should_audiorate = should_audiorate
        self.uuid = uuid
        # 原始mp4，用于视频慢速时裁切
        self.novoice_mp4_original = novoice_mp4
        self.novoice_mp4 = novoice_mp4

        self.cache_folder = cache_folder if cache_folder else Path(
            f'{config.TEMP_DIR}/{str(uuid if uuid else time.time())}').as_posix()
        Path(self.cache_folder).mkdir(parents=True, exist_ok=True)

        # 默认动态帧率
        self.fps_mode = ["-fps_mode", "vfr"]
        ## 是否使用固定帧率        
        if settings.get('fps_mode') == 'cfr':
            video_fps = tools.get_video_info(novoice_mp4, video_fps=True) if novoice_mp4 and Path(
                novoice_mp4).exists() else 30
            self.fps_mode = ["-r", f"{video_fps}", "-fps_mode", "cfr"]
        # 输出变速后的音频
        self.target_audio = target_audio
        # 超过 50 和 10 会发生致命错误
        self.max_audio_speed_rate = float(settings.get('max_audio_speed_rate', 50))
        self.max_video_pts_rate = float(settings.get('max_video_pts_rate', 10))
        # 存放待 音频加速 数据
        self.audio_data = []
        # 存放待视频慢速 数据
        self.video_for_clips = []
        # 视频变速结束后数据
        self.had_processed_video_clips = []

        # 为方便处理，将第一条字幕左侧强制左移到0点，但配音实际可能在大于0时开始，因此最终第0条配音应右移
        self.audio0_left_pad = 0

        self.crf = "18"
        self.preset = "veryfast"

        try:
            if Path(ROOT_DIR + "/crf.txt").exists():
                self.crf = str(int(Path(ROOT_DIR + "/crf.txt").read_text()))
            if Path(ROOT_DIR + "/preset.txt").exists():
                preset_tmp = str(Path(ROOT_DIR + "/preset.txt").read_text().strip())
                if preset_tmp in ['ultrafast', 'veryfast', 'medium', 'slow']:
                    self.preset = preset_tmp
        except Exception:
            pass

        self.audio_speed_rubberband = shutil.which("rubberband")
        logger.debug(
            f"开始语音视频字幕对齐处理：音频加速={self.should_audiorate}, 视频慢速={self.should_videorate}")
        if not HAS_RUBBERBAND or not self.audio_speed_rubberband:
            logger.warning(f"Rubberband 不可用，将使用 pydub+ffmpeg 处理音频加速(较粗糙不精确)。\n建议安装，加速效果更精确\n{INSTALL_RUBBERBAND_TIPS}")

    def run(self):
        if not self.queue_tts:
            return []
        if not self.should_audiorate and not self.should_videorate:
            logger.debug("未选中任何变速，进入普通拼接模式。")
            self._run_no_rate_change_mode()
            return self.queue_tts

        # 1. 预处理
        self._prepare_data()

        # 2. 计算
        self._calculate_adjustments()

        # 3. 先视频变速 因视频变速不准确，有误差，变速后，音频再按实际视频时长做变速
        if self.should_videorate and self.video_for_clips:
            tools.set_process(text=tr('Slow video') + '...', uuid=self.uuid)
            self.had_processed_video_clips, _total_ms = self._video_speeddown()
            logger.debug(f'视频慢速处理完毕，有效视频片段:{len(self.had_processed_video_clips)=}个, 片段累计时长:{_total_ms}ms')
            self._concat_video(self.had_processed_video_clips)
            try:
                self.raw_total_time = tools.get_video_duration(self.novoice_mp4)
                logger.debug(f"新视频连接生成完毕，实际总时长: {self.raw_total_time}ms")
            except Exception:
                pass

        # 4. 音频变速
        if self.audio_data:
            tools.set_process(text=tr('Sound speed alignment stage') + '...', uuid=self.uuid)
            self._execute_audio_speedup_rubberband()

        # 5. 音频对齐拼接
        tools.set_process(text=tr('Concatenating final audio'), uuid=self.uuid)
        self._concat_audio_aligned()

        return self.queue_tts

    def _prepare_data(self):
        """数据清洗与预处理"""
        tools.set_process(text=tr("Preparing data"), uuid=self.uuid)

        if self.novoice_mp4_original and tools.vail_file(self.novoice_mp4_original):
            self.raw_total_time = tools.get_video_duration(self.novoice_mp4_original)

        if self.raw_total_time > 0:
            self.queue_tts[-1]['end_time'] = self.raw_total_time
        logger.debug(f'原始视频时长：{self.raw_total_time=}ms')

        # 强制第一条字幕开始时间为0
        if self.queue_tts[0]['start_time'] > 0:
            self.audio0_left_pad = self.queue_tts[0]['start_time']
            self.queue_tts[0]['start_time'] = 0
            logger.debug(f'第0条字幕开始时间强制设为0，记录偏移 {self.audio0_left_pad=}ms')

        for i, current in enumerate(self.queue_tts):
            current['start_time_source'] = current['start_time']
            current['end_time_source'] = current['end_time']
            current['dubb_time'] = 0

        for i, current in enumerate(self.queue_tts):
            if current['start_time'] >= current['end_time']:
                logger.error(f'第 {i} 行字幕时间轴<=0，不正确，跳过处理:{current=}\n')
                continue

            # 将字幕开始时间、结束时间，首尾相连
            if i < len(self.queue_tts) - 1:
                next_sub = self.queue_tts[i + 1]
                current['end_time'] = next_sub['start_time']
                current['end_time_source'] = next_sub['start_time']

            source_duration = current['end_time_source'] - current['start_time_source']
            # 可用字幕区间时长
            current['source_duration'] = source_duration

            # 设置配音文件时长
            if not current.get('filename') or not Path(current['filename']).exists():
                dummy_wav = Path(self.cache_folder, f'silent_place_{i}.wav').as_posix()
                AudioSegment.silent(duration=source_duration).export(dummy_wav, format="wav")
                current['filename'] = dummy_wav
                current['dubb_time'] = source_duration
                logger.debug(f"[Prepare] 字幕[{current['line']}] 无配音，生成 {source_duration}ms 静音占位")
            else:
                current['dubb_time'] = len(AudioSegment.from_file(current['filename']))

    def _calculate_adjustments(self):
        """计算策略"""
        tools.set_process(text=tr("Calculating sync adjustments"), uuid=self.uuid)

        for i, it in enumerate(self.queue_tts):
            source_duration = it['source_duration']
            if source_duration <= 0:
                continue

            dubb_duration = it['dubb_time']  # 实际配音时长
            # 需达到的目标时长
            video_target = source_duration
            audio_target = source_duration

            # 仅音频加速
            if self.should_audiorate and not self.should_videorate:
                # 配音大于原字幕时长时，对音频做加速处理，短于时不处理，在合并时末尾加静音
                ratio = 1.0
                if dubb_duration > source_duration:
                    ratio = dubb_duration / source_duration
                    if ratio > self.max_audio_speed_rate:
                        audio_target = int(dubb_duration / self.max_audio_speed_rate)
                    else:
                        audio_target = source_duration
                # 存在音频加速并且不存在视频慢速时，注册音频加速的任务
                # 存在视频慢速时，无论是否选择音频加速，都会强制应用，区别仅在于视频慢速幅度不同
                self.audio_data.append({
                    "filename": it['filename'],
                    "dubb_time": dubb_duration,  # 变速前实际配音时长
                    "target_time": audio_target  # 变速结束后需达到的目标时长
                })
                logger.debug(
                    f'仅音频加速: dubb_time={dubb_duration}ms, {audio_target=}ms, ratio={min(ratio, self.max_audio_speed_rate)}')
                continue

            mode_log = ""
            if not self.should_audiorate and self.should_videorate:
                mode_log = "Only Video"
                # 配音大于原字幕时长时，对视频做慢速处理，短于时不处理，直接setpts=pts 裁剪
                if dubb_duration > source_duration:
                    video_target = dubb_duration
                    pts = video_target / source_duration
                    if pts > self.max_video_pts_rate:
                        video_target = int(source_duration * self.max_video_pts_rate)

            elif self.should_audiorate and self.should_videorate:
                mode_log = "Both"
                if dubb_duration > source_duration:
                    # 音频加速和视频慢速各自负担一半时间差
                    diff = dubb_duration - source_duration
                    video_target = round(source_duration + (diff / 2))

            # 日志
            flag = f"Mode={mode_log}, 字幕{i} 可用区间: {source_duration}ms, 当前配音时长: {dubb_duration}ms  "

            # 所有片段均注册,无需视频慢速的则 PTS=1.0
            if self.should_videorate:
                pts = video_target / source_duration if video_target > source_duration else 1.0
                self.video_for_clips.append({
                    "start": it['start_time_source'],  # 需截取的开始时间点
                    "end": it['end_time_source'],  # 需截取的结束时间点
                    "target_time": video_target,  # 视频变速后需达到的目标时长
                    "pts": pts,
                    "tts_index": i
                })
                flag += f' 视频慢速目标时长: {video_target}ms，PTS={pts}  '

            logger.debug(flag)

    def _execute_audio_speedup_rubberband(self):
        if len(self.audio_data) < 1: return
        all_task = []
        _wok = min(12, len(self.audio_data), max(os.cpu_count() - 1, 1))
        logger.debug(f"[音频加速] 使用{_wok}个进程，处理 {len(self.audio_data)} 个配音片段")
        with ProcessPoolExecutor(max_workers=int(_wok)) as pool:
            for i, d in enumerate(self.audio_data):
                if d['dubb_time'] > d['target_time']:
                    all_task.append(pool.submit(
                        _change_speed_rubberband if HAS_RUBBERBAND and self.audio_speed_rubberband else _precise_speed_up_audio,
                        d['filename'], d['target_time']))

        for i, task in enumerate(all_task):
            try:
                tools.set_process(text=f'Audio {i}/{len(all_task)}', uuid=self.uuid)
                task.result()
            except Exception:
                pass

    def _video_speeddown(self):
        data = []
        for i, clip_info in enumerate(self.video_for_clips):
            clip_info['filename'] = Path(self.cache_folder, f"clip_{i}_{clip_info['pts']:.3f}.mp4").as_posix()
            data.append(clip_info)

        if len(data) < 1:
            return [], 0

        all_task = []
        _wok = min(12, len(data), max(os.cpu_count() - 1, 1))
        logger.debug(f'[视频慢速] 使用{_wok}个进程处理 {len(data)} 个视频片段')
        with ProcessPoolExecutor(max_workers=int(_wok)) as pool:
            for i, d in enumerate(data):
                all_task.append(
                    pool.submit(_cut_video_get_duration, d, self.novoice_mp4_original, self.preset, self.crf,
                                self.fps_mode))

        processed_clips = []
        for i, task in enumerate(all_task):
            try:
                tools.set_process(text=f'Video {i}/{len(all_task)}', uuid=self.uuid)
                res = task.result()
                if res:
                    processed_clips.append(res)
            except Exception as e:
                logger.error(f"[视频慢速] 任务异常: {e}")

        processed_clips.sort(key=lambda x: x.get('tts_index', 0))
        _total_ms = sum([it.get('actual_duration', 0) for it in processed_clips])
        # 无音频加速，无需处理，直接相连
        if not self.should_audiorate:
            return processed_clips, _total_ms

        if len(processed_clips) != len(self.queue_tts):
            logger.warning(
                f'共 {len(processed_clips)} 个视频切片数量，与原始字幕数量 {len(self.queue_tts)} 不等，可能存在对齐或双字幕嵌入匹配错误, 放弃音频加速处理')
            return processed_clips, _total_ms

        # 根据 process_clips 实际时长，更新队列
        self.audio_data = []
        for i, it in enumerate(processed_clips):
            # 实际视频片段时长
            _actual_duration = it.get('actual_duration', 0)  # 变速结束后需达到的目标时长
            if _actual_duration == 0:
                # 该片段失败，丢弃，同时应删除该字幕
                self.queue_tts[i]['start_time'] = self.queue_tts[i]['end_time']
                self.queue_tts[i]['source_duration'] = 0
                logger.error(f'字幕{i}视频片段失败，对应需丢弃该字幕')
                continue

            # 更新对应字幕队列时长
            _msg = f"字幕{i}: 原始字幕时长 {self.queue_tts[i]['source_duration']}ms, 视频片段实际时长: {_actual_duration}ms，原字幕结束时刻 {self.queue_tts[i]['end_time']}ms, 调整为 "

            # 如果结束时刻大于下条字幕开始时刻，有错误，需更新结束时刻
            if i > 0 and self.queue_tts[i]['start_time'] < self.queue_tts[i - 1]['end_time']:
                self.queue_tts[i]['start_time'] = self.queue_tts[i - 1]['end_time']

            self.queue_tts[i]['end_time'] = self.queue_tts[i]['start_time'] + _actual_duration
            _msg += f"{self.queue_tts[i]['end_time']}ms, "
            self.queue_tts[i]['source_duration'] = _actual_duration

            logger.debug(_msg)
            tmp={
                "filename": self.queue_tts[i]['filename'],
                "dubb_time": self.queue_tts[i]['dubb_time'],  # 变速前实际配音时长
                "target_time": _actual_duration
            }
            logger.debug(f'该片段配音待处理数据: {tmp=}')
            self.audio_data.append(tmp)

        return processed_clips, _total_ms

    def _concat_video(self, processed_clips):
        txt_content = []
        valid_cnt = 0
        for clip in processed_clips:
            if clip.get('actual_duration', 0) > 0 and Path(clip['filename']).exists():
                path = Path(clip['filename']).as_posix()
                txt_content.append(f"file '{path}'")
                valid_cnt += 1
            else:
                logger.error(f"[Video-Concat] 忽略无效片段: {clip=}")

        if valid_cnt == 0:
            logger.error("[Video-Concat] 没有有效片段，跳过拼接")
            return

        concat_list = Path(self.cache_folder, "video_concat.txt").as_posix()
        with open(concat_list, 'w', encoding='utf-8') as f:
            f.write("\n".join(txt_content))

        tools.set_process(text=tr('Concat videos'), uuid=self.uuid)
        output_path = Path(self.cache_folder, "merged_video.mp4").as_posix()
        logger.debug(f"[Video-Concat] 合并 {valid_cnt} 个视频片段 -> {output_path}")
        tools.runffmpeg(['-y', '-f', 'concat', '-safe', '0', '-i', concat_list, '-c', 'copy', output_path], force_cpu=True, cmd_dir=self.cache_folder)

        if Path(output_path).exists():
            shutil.move(output_path, self.novoice_mp4)
            self._del_mp4_clip()

    def _del_mp4_clip(self):
        deleted_count = 0
        for f in Path(self.cache_folder).glob('clip_*.mp4'):
            try:
                f.unlink()
                deleted_count += 1
            except OSError as e:
                logger.exception(f"无法删除文件 {f.name}: {e}", exc_info=True)
        logger.debug(f'共删除了 {deleted_count} 个临时视频切片')

    def _concat_audio_aligned(self):
        audio_list = []
        # 对 第0条 配音 特殊处理
        if self.audio0_left_pad > 0:  # 需左侧填充空白
            logger.debug(f'第0条字幕原始左偏移值: {self.audio0_left_pad=}')
            _audio0_ms = len(AudioSegment.from_file(self.queue_tts[0]['filename']))
            _sub_ms = self.queue_tts[0]['end_time']
            if _sub_ms > _audio0_ms:  # 大于音频片段，第0条字幕开始时间应右移
                _start_time = min(_sub_ms - _audio0_ms, self.audio0_left_pad)
                logger.debug(f'第0条字幕需恢复偏移值:{_start_time=}')
                self.queue_tts[0]['start_time'] = _start_time
                self.queue_tts[0]['source_duration'] = self.queue_tts[0]['end_time'] - _start_time

        if self.queue_tts[0]['start_time'] > 0:
            audio_list.append(self._create_silen_file("head_0", self.queue_tts[0]['start_time']))


        _total_ms = self.queue_tts[0]['start_time']
        for i, it in enumerate(self.queue_tts):
            if it['source_duration'] <= 0:
                continue
            it['start_time'] = _total_ms

            if not it['filename'] or not Path(it['filename']).exists():
                it['end_time'] = it['start_time'] + it['source_duration']
                audio_list.append(self._create_silen_file(f"nofilename_{i}", it['source_duration']))
                _total_ms += it['source_duration']
                continue

            seg = AudioSegment.from_file(it['filename'])
            audio_list.append(it['filename'])
            _len = len(seg)
            _total_ms += _len
            it['end_time'] = it['start_time'] + _len

            if _len < it['source_duration']:
                # 配音时长短于字幕区间，添加静音
                audio_list.append(self._create_silen_file(f"tail_{i}", it['source_duration'] - _len))
                _total_ms += it['source_duration'] - _len

        logger.debug(f'连接音频前，配音音频总时长累计: {_total_ms=}ms , {self.raw_total_time=}ms')
        # 如果音频时长小于视频时长，末尾加静音
        if _total_ms < self.raw_total_time:
            audio_list.append(self._create_silen_file(f"append_video_end", self.raw_total_time - _total_ms))
            _total_ms+=self.raw_total_time - _total_ms
        elif _total_ms > self.raw_total_time:
            # 定格视频
            self._video_extend(_total_ms - self.raw_total_time)
            # 定格后视频可能大于音频，需补音频静音
            if self.raw_total_time > _total_ms:
                audio_list.append(self._create_silen_file(f"append_video_end", self.raw_total_time - _total_ms))
                _total_ms+=self.raw_total_time - _total_ms

        logger.debug(f'变速处理后，音频片段连接前， 配音总时长: {_total_ms}ms, 视频总时长: {self.raw_total_time}ms')
        self._exec_concat_audio(audio_list)


    def _video_extend(self, duration_ms=1000):
        sec = (duration_ms / 1000.0) + 0.1
        final_video_path = Path(f'{self.cache_folder}/final_video_with_freeze_lastend.mp4').as_posix()

        cmd = ['-y', '-i', os.path.basename(self.novoice_mp4),
               '-vf', f'tpad=stop_mode=clone:stop_duration={sec:.3f}',
               '-c:v', 'libx264',
               '-crf', f'{settings.get("crf", 23)}',
               '-preset', settings.get('preset', 'veryfast'),
               '-an', 'final_video_with_freeze_lastend.mp4'
               ]
        tools.get_video_duration(self.novoice_mp4)
        tools.runffmpeg(cmd, force_cpu=True, cmd_dir=self.cache_folder)

        shutil.copy2(final_video_path, self.novoice_mp4)
        self.raw_total_time = tools.get_video_duration(final_video_path)
        logger.debug(f"视频延长后实际时长 {self.raw_total_time=}ms")
        return self.raw_total_time

    def _run_no_rate_change_mode(self):
        # 不变速时直接拼接
        tools.set_process(text=tr("Merging audio (No Speed Change)..."), uuid=self.uuid)

        audio_concat_list = []
        total_audio_duration = 0

        for i, it in enumerate(self.queue_tts):

            prev_end = 0 if i == 0 else self.queue_tts[i - 1].get('end_pos_for_concat', 0)
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


        if self.novoice_mp4 and Path(self.novoice_mp4).exists() and total_audio_duration>self.raw_total_time:
            # 存在视频，需定格
            self._video_extend(total_audio_duration>self.raw_total_time)

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
            _last_len = len(AudioSegment.from_file(temp_wav, format="wav"))
            shutil.move(temp_wav, self.target_audio)
            logger.debug(f"音频片段连接后，实际时长 {_last_len}ms, 已生成到: {self.target_audio}")
        else:
            logger.error("音频片段连接失败")
            _last_len = 0
        return _last_len  # 返回音频长度 ms


# 专门针对 文字配音 单独处理
class TtsSpeedRate(SpeedRate):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.should_videorate = False
        self.max_audio_speed_rate = 50

    def run(self):
        if not self.should_audiorate:
            logger.debug("[SpeedRate] 未启用变速，进入普通拼接模式。")
            self._run_no_rate_change_mode()
            return self.queue_tts
        # 删除时间轴不合法的
        self.queue_tts = [it for it in self.queue_tts if it['end_time'] - it['start_time'] > 0]
        logger.debug("[SpeedRate] 启用变速，进入对齐模式。")
        # 1. 预处理
        self._prepare_data()
        # 2. 计算
        self._calculate_adjustments()
        # 3. 音频变速
        if self.audio_data:
            tools.set_process(text='Processing audio speed...', uuid=self.uuid)
            self._execute_audio_speedup_rubberband()

        tools.set_process(text='Concatenating final audio...', uuid=self.uuid)
        self._concat_audio_aligned()

        return self.queue_tts

    def _prepare_data(self):
        """数据清洗与预处理"""
        tools.set_process(text="Preparing data...", uuid=self.uuid)

        _len = len(self.queue_tts)
        for i in range(_len):
            current = self.queue_tts[i]
            if i < _len - 1:
                current['end_time'] = self.queue_tts[i + 1]['start_time']

            current['source_duration'] = current['end_time'] - current['start_time']

            # 检查配音文件
            if not current.get('filename') or not Path(current['filename']).exists():
                # 生成占位静音
                dummy_wav = Path(self.cache_folder, f'silent_place_{i}.wav').as_posix()
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
            if dubb_dur <= 0 or source_dur <= 0:
                continue
            audio_target = dubb_dur

            mode_log = f"[为字幕配音] {i=}"
            if dubb_dur > source_dur:
                self.audio_data.append({
                    "filename": it['filename'],
                    "dubb_time": dubb_dur,
                    "target_time": source_dur  # 不限制，强制加速到对齐
                })

            logger.debug(
                f"[Calc] Mode={mode_log} Line={it['line']} | Source_duration={source_dur} Dubb_duration={dubb_dur} -> TargetA={audio_target}")

    def _concat_audio_aligned(self):
        logger.debug("[Audio] 开始对齐拼接...")

        audio_concat_list = []

        # 恢复原始时间轴
        for i, it in enumerate(self.queue_tts):
            # 添加前导静音
            if i == 0 and it['start_time'] > 0:
                audio_concat_list.append(self._create_silen_file(f"gap_{i}", it['start_time']))

            # 真实配音时长
            if it.get('filename') and Path(it['filename']).exists():
                audio_concat_list.append(it['filename'])
                dubb_len = len(AudioSegment.from_file(it['filename']))
            else:
                audio_concat_list.append(self._create_silen_file(f"sub_{i}", it['source_duration']))
                dubb_len = it['source_duration']
            # 如果真实配音短于字幕区间，末尾添加静音
            if dubb_len < it['source_duration']:
                audio_concat_list.append(self._create_silen_file(f"end_{i}", it['source_duration'] - dubb_len))
        self._exec_concat_audio(audio_concat_list)
