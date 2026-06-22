# 原理解释见 @docs/Synchronize.md
import os
import shutil
import time
from pathlib import Path

# 引入 soundfile 和 audio 处理
import soundfile as sf
import numpy as np  # 新增 numpy 用于声道处理
from pydub import AudioSegment

# 尝试导入 pyrubberband
from videotrans.configure.contants import INSTALL_RUBBERBAND_TIPS

try:
    import pyrubberband as pyrb
    HAS_RUBBERBAND = True
except ImportError:
    HAS_RUBBERBAND = False


from videotrans.configure.config import ROOT_DIR,tr, settings, logger
from videotrans.configure import config
from videotrans.util import tools
from concurrent.futures import ProcessPoolExecutor



def _cut_video_get_duration(i, task, novoice_mp4_original, preset, crf,fps_mode):
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
    if abs(pts_factor - 1.0) >= 0.001:
        filter_complex.append(f"setpts={pts_factor}*PTS")
    else:
        filter_complex.append("setpts=PTS")

    cmd.extend(['-vf', ",".join(filter_complex)])
    #cmd.extend(['-fps_mode', 'vfr']) # 关键修正
    cmd.extend(fps_mode) # 关键修正
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
            ]+fps_mode

            cmd_backup.append(os.path.basename(task['filename']))
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
            logger.warning(f"[Audio-RB] 空音频文件: {input_path}")
            return False
            
        current_duration = round((len(y) / sr) * 1000)
        
        if target_duration <= 0: target_duration = 1
        
        if target_duration > current_duration:
             # 允许微小的误差，或者由后续静音填充处理
             logger.debug(f"[Audio-RB] 目标时长({target_duration}) > 当前时长({current_duration})，跳过变速，交由静音填充。")
             return False

        time_stretch_rate = current_duration / target_duration
        
        # 限制范围
        time_stretch_rate = max(0.2, min(time_stretch_rate, 50.0))
        
        logger.debug(f"[Audio-RB] {input_path} 原长:{current_duration}ms -> 目标:{target_duration}ms 倍率:{time_stretch_rate:.2f}")

        y_stretched = pyrb.time_stretch(y, sr, time_stretch_rate)
        
        # 如果是单声道 (ndim=1)，复制为双声道
        if y_stretched.ndim == 1:
            y_stretched = np.column_stack((y_stretched, y_stretched))
        
        sf.write(input_path, y_stretched, sr)
        
    except Exception as e:
        logger.error(f"[Audio-RB] 音频处理失败 {input_path}: {e}")
        return False
    return True

def _precise_speed_up_audio(input_path=None, target_duration=None):
    # 使用 pydub 获取当前时长（避免双重读取）
    current_duration_ms = len(AudioSegment.from_file(input_path, format='wav'))

    # 构造 atempo 滤镜链
    # atempo 限制：参数必须在 [0.5, 2.0] 之间
    atempo_list = []
    speed_factor = current_duration_ms / target_duration

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
        '-t', f"{target_duration/1000.0}",  # 强制裁剪到目标时长，防止精度误差
        '-ar', "48000",
        '-ac', "2",
        '-c:a', 'pcm_s16le',
        f'{input_path}-after.wav'
    ]
    try:
        tools.runffmpeg(cmd)
        shutil.copy2(f'{input_path}-after.wav', input_path)
    except Exception as e:
        logger.exception(f'音频加速失败:{e}')
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
        self.raw_total_time = raw_total_time if raw_total_time is not None else 0
        self.remove_silent_mid = remove_silent_mid
        self.queue_tts = queue_tts
        self.len_queue = len(queue_tts)
        self.should_videorate = should_videorate
        self.should_audiorate = should_audiorate
        self.uuid = uuid
        self.novoice_mp4_original = novoice_mp4
        self.novoice_mp4 = novoice_mp4
        self.cache_folder = cache_folder if cache_folder else Path(
            f'{config.TEMP_DIR}/{str(uuid if uuid else time.time())}').as_posix()
        Path(self.cache_folder).mkdir(parents=True, exist_ok=True)

        self.stop_show_process = False

        self.fps_mode=["-fps_mode","vfr"]
        ## 是否使用固定帧率        
        if settings.get('fps_mode')=='cfr':
            video_fps=tools.get_video_info(novoice_mp4,video_fps=True) if novoice_mp4 and Path(novoice_mp4).exists() else 30
            self.fps_mode=["-r",f"{video_fps}","-fps_mode","cfr"]
            
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
        except Exception:
            pass

        self.audio_speed_rubberband = shutil.which("rubberband")
        logger.debug(f"[SpeedRate] Init. AudioRate={self.should_audiorate}, VideoRate={self.should_videorate}, Rubberband={bool(self.audio_speed_rubberband)}")
        if not HAS_RUBBERBAND or not self.audio_speed_rubberband:
            logger.warning(f"[SpeedRate] Rubberband 不可用，将使用pydub+ffmpeg处理音频加速。\n建议安装，加速效果更佳\n{INSTALL_RUBBERBAND_TIPS}")

    def run(self):
        if not self.queue_tts:
            return []
        if not self.should_audiorate and not self.should_videorate:
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
            self._execute_audio_speedup_rubberband()

        # 4. 视频变速
        if self.should_videorate and self.video_for_clips:
            tools.set_process(text='Processing video speed...', uuid=self.uuid)
            processed_video_clips = self._video_speeddown()
            
            # 回写
            for clip in processed_video_clips:
                tts_idx = clip.get('tts_index',-1)
                if tts_idx <0:
                    continue
                real_duration = clip.get('actual_duration', 0)
                if tts_idx is not None  and 0 <= tts_idx < len(self.queue_tts):
                    # 【关键】这就是最终的视频槽位长度
                    self.queue_tts[tts_idx]['final_duration'] = real_duration
            
            self._concat_video(processed_video_clips)
            
            # 更新总时长
            if Path(self.novoice_mp4).exists():
                try:
                    self.raw_total_time = tools.get_video_duration(self.novoice_mp4)
                    logger.debug(f"[SpeedRate] 新视频生成完毕，总时长: {self.raw_total_time}ms")
                except Exception:
                    pass
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

            # 字幕开始点，用于切分 视频 和 变速
            current['start_time_source']=current['start_time']
            # 有视频慢速并且小于100ms，置为 从0开始，防止短视频片段出错
            if self.should_videorate and i == 0 and current['start_time']<100:
                current['start_time_source'] = 0
            
            # 填补空隙，将字幕结束时间变为下个开始时间，增大变速区间，以减小变速幅度
            # 开始时间点除了第0条，其他不变，只移动结束点
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
                AudioSegment.silent(duration=current['source_duration']).export(dummy_wav, format="wav")
                current['filename'] = dummy_wav
                current['dubb_time'] = current['source_duration']
                logger.debug(f"[Prepare] 字幕[{current['line']}] 无配音，生成 {current['source_duration']}ms 静音占位")
            else:
                current['dubb_time'] = len(AudioSegment.from_file(current['filename']))

    def _calculate_adjustments(self):
        """计算策略"""
        tools.set_process(text="Calculating sync adjustments...", uuid=self.uuid)
        # 视频慢速，第0条字幕之前可能有无声音视频
        if self.should_videorate and self.queue_tts[0]['start_time_source']>0:
            self.video_for_clips.append({
                    "start": 0,
                    "end": self.queue_tts[0]['start_time_source'],
                    "target_time": self.queue_tts[0]['start_time_source'],
                    "pts": 1,
                    "tts_index": -1,
                    "line": -1
            })
            
        
        for i, it in enumerate(self.queue_tts):
            source_dur = it['source_duration']
            dubb_dur = it['dubb_time']
            
            if self.should_videorate and source_dur <= 0:
                logger.warning(f"[Calc] 字幕[{it['line']}] 视频槽位<=0，跳过")
                self.video_for_clips.append({
                    "start": 0, 
                    "end": 0, 
                    "target_time": 0, 
                    "pts": 1,
                    "tts_index": i, 
                })
                continue
            if source_dur<=0:
                continue

            video_target = source_dur
            audio_target = source_dur
            
            mode_log = ""
            # 仅音频加速
            if self.should_audiorate and not self.should_videorate:
                mode_log = "Only Audio"
                if dubb_dur > source_dur:
                    ratio = dubb_dur / source_dur
                    if ratio > self.max_audio_speed_rate:
                        audio_target = int(dubb_dur / self.max_audio_speed_rate)
                    else:
                        audio_target = source_dur

            elif not self.should_audiorate and self.should_videorate:
                mode_log = "Only Video"
                if dubb_dur > source_dur:
                    video_target = dubb_dur
                    pts = video_target / source_dur
                    if pts > self.max_video_pts_rate:
                        video_target = int(source_dur * self.max_video_pts_rate)

            elif self.should_audiorate and self.should_videorate:
                mode_log = "Both"
                if dubb_dur > source_dur:
                    ratio = dubb_dur / source_dur
                    if ratio <= self.BOTH_MODE_AUDIO_ONLY_THRESHOLD:
                        # 倍率较小，仅加速音频即可，无需视频慢速
                        audio_target = source_dur
                        video_target = source_dur
                    else:
                        # 倍率较大，音频加速和视频慢速各自负担一半时间差
                        diff = dubb_dur - source_dur
                        joint_target = int(source_dur + (diff / 2))
                        audio_target = joint_target
                        video_target = joint_target
            


            # 注册任务
            if self.should_audiorate and audio_target < dubb_dur:
                self.audio_data.append({
                    "filename": it['filename'],
                    "dubb_time": dubb_dur,
                    "target_time": audio_target
                })
            
            if self.should_videorate:
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
            logger.debug(f"[Calc] Mode={mode_log} Line={it['line']} | Source_duration={source_dur} Dubb_duration={dubb_dur} -> TargetV={video_target} TargetA={audio_target}")


    def _execute_audio_speedup_rubberband(self):
        logger.debug(f"[Audio] 开始处理 {len(self.audio_data)} 个音频变速任务")
        if len(self.audio_data)<1:
            return
        all_task = []
        
        _wok=min(12, len(self.audio_data), max(os.cpu_count()-1,1) )
        logger.debug(f'使用{_wok}个进程处理音频加速')
        with ProcessPoolExecutor(max_workers=int(_wok)) as pool:
            for i, d in enumerate(self.audio_data):
                all_task.append(pool.submit(_change_speed_rubberband if HAS_RUBBERBAND and self.audio_speed_rubberband else _precise_speed_up_audio,d['filename'], d['target_time'] ))
        
        for i,task in enumerate(all_task):
            try:
                tools.set_process(text=f'audio speedup {i}/{len(all_task)}',uuid=self.uuid)
                res=task.result()
            except Exception:
                pass

    def _video_speeddown(self):
        data = []
        for i, clip_info in enumerate(self.video_for_clips):
            clip_info['queue_index'] = clip_info.get('tts_index',-1)
            clip_info['filename'] = Path(self.cache_folder, f"clip_{i}_{clip_info['pts']:.3f}.mp4").as_posix()
            data.append(clip_info)
        if len(data)<1:
            return []
        all_task = []
        logger.debug(f"[Video] 提交 {len(data)} 个视频片段处理慢速任务")
        _wok=min(12, len(data), max(os.cpu_count()-1,1) )
        logger.debug(f'使用{_wok}个进程处理视频慢速')
        with ProcessPoolExecutor(max_workers=int(_wok)) as pool:
            for i, d in enumerate(data):
                all_task.append(pool.submit(_cut_video_get_duration,i, d, self.novoice_mp4_original, self.preset, self.crf,self.fps_mode  ))
          
        processed_clips = []
        for i,task in enumerate(all_task):
            try:
                tools.set_process(text=f'video speed down {i}/{len(all_task)}',uuid=self.uuid)
                res = task.result()
                if res: 
                    processed_clips.append(res)
            except Exception as e:
                logger.error(f"[Video] 任务异常: {e}")
        
        processed_clips.sort(key=lambda x: x.get('queue_index', -1))
        return processed_clips

    def _concat_video(self, processed_clips):
        txt_content = []
        valid_cnt = 0
        for clip in processed_clips:
            if clip.get('actual_duration', 0) > 0 and Path(clip['filename']).exists():
                path = Path(clip['filename']).as_posix()
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
            # 删除片段
            self._del_mp4_clip()
            
    def _del_mp4_clip(self):
        deleted_count = 0
        for f in Path(self.cache_folder).glob('clip_*.mp4'):
            try:
                f.unlink()
                deleted_count += 1
            except OSError as e:
                logger.exception(f"无法删除文件 {f.name}: {e}", exc_info=True)
        logger.debug(f"清理视频慢速中生成的视频片段，共删除了 {deleted_count} 个文件。")

    def _concat_audio_aligned(self):
        logger.debug("[Audio] 开始对齐拼接...")
        audio_list = []
        current_timeline = self.queue_tts[0]['start_time']
        if current_timeline > 0:
            audio_list.append(self._create_silen_file("head_0", current_timeline))

        for i, it in enumerate(self.queue_tts):
            # 有视频慢速时，使用视频片段实际时长，否则使用字幕区间时长
            slot_duration = it.get('final_duration', it['source_duration'])

            # 【兜底修正】如果视频槽位失效（0ms），回退到 source_duration
            if slot_duration <= 0:
                logger.warning(f"[Audio-Sync] 字幕[{it['line']}] 视频槽时长为0，回退使用原始时长: source_duration={it['source_duration']}ms")
                slot_duration = max(1, it['source_duration'])

            current_slot_audio_len = 0
            seg = None

            # 读取配音文件并缓存时长，避免重复读取
            audio_file = it['filename']
            if Path(audio_file).exists():
                try:
                    seg = AudioSegment.from_file(audio_file)
                    if seg.channels != self.AUDIO_CHANNELS:
                        seg = seg.set_channels(self.AUDIO_CHANNELS)
                        seg.export(audio_file, format='wav')
                    current_slot_audio_len = len(seg)
                except Exception as e:
                    logger.error(f"[Audio-Sync] 读取配音失败 {audio_file}: {e}")

            # 长度对齐
            diff = slot_duration - current_slot_audio_len
            log_flag = f"当前音频时长:{current_slot_audio_len=}, 槽位时长:{slot_duration=}, "

            if current_slot_audio_len > slot_duration:
                # 配音长度大于槽位，截断音频以匹配槽位
                log_flag += f"音频溢出截断 {abs(diff)}"
                try:
                    if seg is None:
                        seg = AudioSegment.from_file(audio_file)
                    cut_seg = seg[:slot_duration]
                    final_slot_path = Path(self.cache_folder, f"final_slot_cut_{i}.wav").as_posix()
                    cut_seg.export(final_slot_path, format='wav')
                    audio_list.append(final_slot_path)
                except Exception as e:
                    logger.error(f"截断音频失败: {e}")
                    audio_list.append(audio_file)

            elif current_slot_audio_len < slot_duration:
                # 补尾部静音                
                log_flag += f"音频变短末尾需补静音 {diff}ms"
                audio_list.append(audio_file)
                audio_list.append(self._create_silen_file(f"tail_{i}", diff))
            else:
                log_flag += "匹配"
                audio_list.append(audio_file)

            logger.debug(f"[Audio-Sync] Line={it['line']} | {log_flag} | Timeline: {current_timeline} -> {current_timeline+slot_duration}")

            it['start_time'] = current_timeline
            it['end_time'] = current_timeline + slot_duration
            current_timeline += slot_duration

        self._exec_concat_audio(audio_list)
    
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
        self.should_videorate=False
        self.max_audio_speed_rate=100


    def run(self):
        if not self.should_audiorate:
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
            self._execute_audio_speedup_rubberband()


        tools.set_process(text='Concatenating final audio...', uuid=self.uuid)
        self._concat_audio_aligned()

        return self.queue_tts

    def _prepare_data(self):
        """数据清洗与预处理"""
        tools.set_process(text="Preparing data...", uuid=self.uuid)
        
        _len=len(self.queue_tts)
        for i in range(_len):
            current = self.queue_tts[i]
            if i<_len-1:
                current['end_time']=self.queue_tts[i+1]['start_time']
                        
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
            if dubb_dur<=0 or source_dur<=0:
                continue
            audio_target = dubb_dur


            mode_log = f"[为字幕配音] {i=}"
            if dubb_dur > source_dur:
                self.audio_data.append({
                    "filename": it['filename'],
                    "dubb_time": dubb_dur,
                    "target_time": source_dur # 不限制，强制加速到对齐
                })

            logger.debug(f"[Calc] Mode={mode_log} Line={it['line']} | Source_duration={source_dur} Dubb_duration={dubb_dur} -> TargetA={audio_target}")


    def _concat_audio_aligned(self):
        logger.debug("[Audio] 开始对齐拼接...")

        audio_concat_list = []

        # 恢复原始时间轴
        for i, it in enumerate(self.queue_tts):
            # 添加前导静音
            if i == 0 and it['start_time']>0:
                audio_concat_list.append(self._create_silen_file(f"gap_{i}", it['start_time']))

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
        self._exec_concat_audio(audio_concat_list)

