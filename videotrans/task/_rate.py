import os
import shutil
import time
from pathlib import Path
import concurrent.futures

from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

from videotrans.configure import config
from videotrans.util import tools

class SpeedRate:
    """
    通过音频加速和视频慢放来对齐翻译配音和原始视频时间轴。

    V10 更新日志:
    - 【策略优化】引入微小间隙“吸收”策略，替代原有的“丢弃”策略。
      当一个字幕片段后的间隙小于阈值时，该间隙将被并入前一个字幕片段进行处理，
      避免了“跳帧”现象，并为视频慢速提供了额外时长。
    - 相应地调整了 video_pts 的计算逻辑，以适应动态变化的片段时长。
    """

    MIN_CLIP_DURATION_MS = 50  # 最小有效片段时长（毫秒）

    def __init__(self,
                 *,
                 queue_tts=None,
                 shoud_videorate=False,
                 shoud_audiorate=False,
                 uuid=None,
                 novoice_mp4=None,
                 raw_total_time=0,
                 noextname=None,
                 target_audio=None,
                 cache_folder=None
                 ):
        self.queue_tts = queue_tts
        self.shoud_videorate = shoud_videorate
        self.shoud_audiorate = shoud_audiorate
        self.uuid = uuid
        self.novoice_mp4_original = novoice_mp4
        self.novoice_mp4 = novoice_mp4
        self.raw_total_time = raw_total_time
        self.noextname = noextname
        self.target_audio = target_audio
        self.cache_folder = cache_folder if cache_folder else Path(f'{config.TEMP_DIR}/{str(uuid if uuid else time.time())}').as_posix()
        Path(self.cache_folder).mkdir(parents=True, exist_ok=True)
        
        self.max_audio_speed_rate = max(1.0, float(config.settings.get('audio_rate', 5.0)))
        self.max_video_pts_rate = max(1.0, float(config.settings.get('video_rate', 10.0)))
        
        config.logger.info(f"SpeedRate initialized for '{self.noextname}'. AudioRate: {self.shoud_audiorate}, VideoRate: {self.shoud_videorate}")
        config.logger.info(f"Config limits: MaxAudioSpeed={self.max_audio_speed_rate}, MaxVideoPTS={self.max_video_pts_rate}, MinClipDuration={self.MIN_CLIP_DURATION_MS}ms")

    def run(self):
        """主执行函数"""
        self._prepare_data()
        self._calculate_adjustments()
        self._execute_audio_speedup()
        self._execute_video_processing()
        merged_audio = self._recalculate_timeline_and_merge_audio()
        if merged_audio:
            self._finalize_audio(merged_audio)
        return self.queue_tts

    def _prepare_data(self):
        """第一步：准备和初始化数据。"""
        tools.set_process(text="Preparing data...", uuid=self.uuid)

        # 第一阶段：初始化独立数据
        for it in self.queue_tts:
            it['start_time_source'] = it['start_time']
            it['end_time_source'] = it['end_time']
            it['source_duration'] = it['end_time_source'] - it['start_time_source']
            it['dubb_time'] = int(tools.get_audio_time(it['filename']) * 1000) if tools.vail_file(it['filename']) else 0
            it['target_audio_duration'] = it['dubb_time']
            it['target_video_duration'] = it['source_duration']
            it['video_pts'] = 1.0
        
        # 第二阶段：计算间隙
        for i, it in enumerate(self.queue_tts):
            if i < len(self.queue_tts) - 1:
                next_item = self.queue_tts[i + 1]
                it['silent_gap'] = next_item['start_time_source'] - it['end_time_source']
            else:
                it['silent_gap'] = self.raw_total_time - it['end_time_source']
            it['silent_gap'] = max(0, it['silent_gap'])

    def _calculate_adjustments(self):
        """第二步：计算调整方案。"""
        tools.set_process(text="Calculating adjustments...", uuid=self.uuid)
        for i, it in enumerate(self.queue_tts):
            
            if it['dubb_time'] > it['source_duration'] and tools.vail_file(it['filename']):
                try:
                    original_dubb_time = it['dubb_time']
                    _, new_dubb_length_ms = tools.remove_silence_from_file(
                        it['filename'], silence_threshold=-50.0, chunk_size=10, is_start=True)
                    it['dubb_time'] = new_dubb_length_ms
                    if original_dubb_time != it['dubb_time']:
                        config.logger.info(f"Removed silence from {Path(it['filename']).name}: duration reduced from {original_dubb_time}ms to {it['dubb_time']}ms.")
                except Exception as e:
                    config.logger.warning(f"Could not remove silence from {it['filename']}: {e}")

            # 吸收微小间隙后，可用的视频时长可能会增加
            effective_source_duration = it['source_duration']
            if it.get('silent_gap', 0) < self.MIN_CLIP_DURATION_MS:
                effective_source_duration += it['silent_gap']

            if it['dubb_time'] <= effective_source_duration or effective_source_duration <= 0:
                continue

            dub_duration = it['dubb_time']
            # 使用有效时长进行计算
            source_duration = effective_source_duration
            silent_gap = it['silent_gap']
            over_time = dub_duration - source_duration

            # 决策逻辑现在基于 `effective_source_duration`
            if self.shoud_audiorate and not self.shoud_videorate:
                required_speed = dub_duration / source_duration
                if required_speed <= 1.5:
                    it['target_audio_duration'] = source_duration
                else:
                    # 注意：这里的silent_gap在吸收后实际已经为0，但为了逻辑完整性保留
                    available_time = source_duration + (silent_gap if silent_gap >= self.MIN_CLIP_DURATION_MS else 0)
                    duration_at_1_5x = dub_duration / 1.5
                    it['target_audio_duration'] = duration_at_1_5x if duration_at_1_5x <= available_time else available_time
            
            elif not self.shoud_audiorate and self.shoud_videorate:
                required_pts = dub_duration / source_duration
                if required_pts <= 1.5:
                    it['target_video_duration'] = dub_duration
                else:
                    available_time = source_duration + (silent_gap if silent_gap >= self.MIN_CLIP_DURATION_MS else 0)
                    duration_at_1_5x = source_duration * 1.5
                    it['target_video_duration'] = duration_at_1_5x if duration_at_1_5x <= available_time else available_time

            elif self.shoud_audiorate and self.shoud_videorate:
                if over_time <= 1000:
                    it['target_audio_duration'] = source_duration
                else:
                    adjustment_share = over_time // 2
                    it['target_audio_duration'] = dub_duration - adjustment_share
                    it['target_video_duration'] = source_duration + adjustment_share

            # 安全校验和PTS计算
            if it['target_audio_duration'] < dub_duration:
                speed_ratio = dub_duration / it['target_audio_duration']
                if speed_ratio > self.max_audio_speed_rate: it['target_audio_duration'] = dub_duration / self.max_audio_speed_rate
            
            if it['target_video_duration'] > source_duration:
                pts_ratio = it['target_video_duration'] / source_duration
                if pts_ratio > self.max_video_pts_rate: it['target_video_duration'] = source_duration * self.max_video_pts_rate
                # pts需要基于最终裁切的原始视频时长来计算
                it['video_pts'] = max(1.0, it['target_video_duration'] / source_duration)
    
    def _process_single_audio(self, item):
        """处理单个音频文件的加速任务"""
        input_file_path = item['filename']
        target_duration_ms = int(item['target_duration_ms'])
        
        try:
            audio = AudioSegment.from_file(input_file_path)
            current_duration_ms = len(audio)

            if target_duration_ms <= 0 or current_duration_ms <= target_duration_ms: return input_file_path, current_duration_ms, ""

            speedup_ratio = current_duration_ms / target_duration_ms
            fast_audio = audio.speedup(playback_speed=speedup_ratio)
            config.logger.info(f'音频加速处理:{speedup_ratio=}')
            fast_audio.export(input_file_path, format=Path(input_file_path).suffix[1:])
            item['ref']['dubb_time'] = len(fast_audio)
            return input_file_path, len(fast_audio), ""
        except Exception as e:
            config.logger.error(f"Error processing audio {input_file_path}: {e}")
            return input_file_path, None, str(e)

    def _execute_audio_speedup(self):
        """第三步：执行音频加速。"""
        if not self.shoud_audiorate: return
        tasks = [
            {"filename": it['filename'], "target_duration_ms": it['target_audio_duration'], "ref": it}
            for it in self.queue_tts if it.get('dubb_time', 0) > it.get('target_audio_duration', 0) and tools.vail_file(it['filename'])
        ]
        if not tasks: return

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self._process_single_audio, task) for task in tasks]
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                if config.exit_soft: executor.shutdown(wait=False, cancel_futures=True); return
                future.result()
                tools.set_process(text=f"Audio processing: {i + 1}/{len(tasks)}", uuid=self.uuid)

    def _execute_video_processing(self):
        """第四步：执行视频裁切（采用微小间隙吸收策略）。"""
        if not self.shoud_videorate or not self.novoice_mp4_original:
            return
            
        video_tasks = []
        processed_video_clips = []
        last_end_time = 0

        i = 0
        while i < len(self.queue_tts):
            it = self.queue_tts[i]
            
            # 处理字幕片段前的间隙
            gap_before = it['start_time_source'] - last_end_time
            if gap_before > self.MIN_CLIP_DURATION_MS:
                clip_path = Path(f'{self.cache_folder}/{i:05d}_gap.mp4').as_posix()
                video_tasks.append({"ss": tools.ms_to_time_string(ms=last_end_time), "to": tools.ms_to_time_string(ms=it['start_time_source']), "source": self.novoice_mp4_original, "pts": 1.0, "out": clip_path})
                processed_video_clips.append(clip_path)

            # 确定当前字幕片段的裁切终点
            start_ss = it['start_time_source']
            end_to = it['end_time_source']
            
            # V10 核心逻辑：向前看，决定是否吸收下一个间隙
            if i + 1 < len(self.queue_tts):
                next_it = self.queue_tts[i+1]
                gap_after = next_it['start_time_source'] - it['end_time_source']
                if 0 < gap_after < self.MIN_CLIP_DURATION_MS:
                    end_to = next_it['start_time_source'] # 延伸裁切终点
                    config.logger.info(f"Absorbing small gap ({gap_after}ms) after segment {i} into the clip.")
            
            current_clip_source_duration = end_to - start_ss
            
            # 只有当片段有效时才创建任务
            if current_clip_source_duration > self.MIN_CLIP_DURATION_MS:
                clip_path = Path(f"{self.cache_folder}/{i:05d}_sub.mp4").as_posix()
                
                # 如果需要变速，可能需要重新计算pts
                pts_val = it.get('video_pts', 1.0)
                if pts_val > 1.01:
                    # 新的pts = 目标时长 / 新的源时长
                    new_target_duration = it.get('target_video_duration', current_clip_source_duration)
                    pts_val = max(1.0, new_target_duration / current_clip_source_duration)

                video_tasks.append({"ss": tools.ms_to_time_string(ms=start_ss), "to": tools.ms_to_time_string(ms=end_to), "source": self.novoice_mp4_original, "pts": pts_val, "out": clip_path})
                processed_video_clips.append(clip_path)
            
            last_end_time = end_to
            i += 1
        
        # 处理结尾的最后一个间隙
        if (final_gap := self.raw_total_time - last_end_time) > self.MIN_CLIP_DURATION_MS:
            clip_path = Path(f'{self.cache_folder}/zzzz_final_gap.mp4').as_posix()
            video_tasks.append({"ss": tools.ms_to_time_string(ms=last_end_time), "to": "", "source": self.novoice_mp4_original, "pts": 1.0, "out": clip_path})
            processed_video_clips.append(clip_path)

        # ... (后续的执行、合并逻辑与之前版本相同) ...
        for j, task in enumerate(video_tasks):
            if config.exit_soft: return
            tools.set_process(text=f"Video processing: {j + 1}/{len(video_tasks)}", uuid=self.uuid)
            the_pts = task['pts'] if task.get('pts', 1.0) > 1.01 else ""
            config.logger.info(f'视频慢速:{the_pts=},处理后输出视频片段={task["out"]}')
            tools.cut_from_video(ss=task['ss'], to=task['to'], source=task['source'], pts=the_pts, out=task['out'])
            
            output_path = Path(task['out'])
            if not output_path.exists() or output_path.stat().st_size == 0:
                config.logger.warning(f"Segment {task['out']} failed to generate (PTS={task.get('pts', 1.0)}). Fallback to original speed.")
                tools.cut_from_video(ss=task['ss'], to=task['to'], source=task['source'], pts="", out=task['out'])
                if not output_path.exists() or output_path.stat().st_size == 0:
                    config.logger.error(f"FATAL: Fallback for {task['out']} also failed. Segment will be MISSING.")

        valid_clips = [clip for clip in processed_video_clips if Path(clip).exists() and Path(clip).stat().st_size > 0]
        if not valid_clips:
            config.logger.warning("No valid video clips generated to merge. Skipping video merge.")
            self.novoice_mp4 = self.novoice_mp4_original
            return

        concat_txt_path = Path(f'{self.cache_folder}/concat_list.txt').as_posix()
        tools.create_concat_txt(valid_clips, concat_txt=concat_txt_path)
        
        merged_video_path = Path(f'{self.cache_folder}/merged_{self.noextname}.mp4').as_posix()
        tools.set_process(text="Merging video clips...", uuid=self.uuid)
        tools.concat_multi_mp4(out=merged_video_path, concat_txt=concat_txt_path)
        self.novoice_mp4 = merged_video_path

    def _recalculate_timeline_and_merge_audio(self):
        """第五步：重新计算时间线并合并音频。"""
        merged_audio = AudioSegment.empty()
        
        video_was_processed = self.shoud_videorate and self.novoice_mp4_original and Path(self.novoice_mp4).name.startswith("merged_")

        if video_was_processed:
            config.logger.info("Building audio timeline based on processed video clips.")
            current_timeline_ms = 0
            try:
                sorted_clips = sorted([f for f in os.listdir(self.cache_folder) if f.endswith(".mp4") and ("_sub" in f or "_gap" in f)])
            except FileNotFoundError: return None

            for clip_filename in sorted_clips:
                clip_path = Path(f'{self.cache_folder}/{clip_filename}').as_posix()
                try:
                    if not (Path(clip_path).exists() and Path(clip_path).stat().st_size > 0): continue
                    clip_duration = tools.get_video_duration(clip_path)
                except Exception as e:
                    config.logger.warning(f"Could not get duration for clip {clip_path} (error: {e}). Skipping.")
                    continue

                if "_sub" in clip_filename:
                    index = int(clip_filename.split('_')[0])
                    it = self.queue_tts[index]
                    it['start_time'] = current_timeline_ms
                    segment = AudioSegment.from_file(it['filename']) if tools.vail_file(it['filename']) else AudioSegment.silent(duration=clip_duration)
                    
                    if len(segment) > clip_duration: segment = segment[:clip_duration]
                    elif len(segment) < clip_duration: segment += AudioSegment.silent(duration=clip_duration - len(segment))
                    
                    merged_audio += segment
                    it['end_time'] = current_timeline_ms + clip_duration
                    it['startraw'], it['endraw'] = tools.ms_to_time_string(ms=it['start_time']), tools.ms_to_time_string(ms=it['end_time']) 

                else: # gap
                    merged_audio += AudioSegment.silent(duration=clip_duration)
                current_timeline_ms += clip_duration
        else:
            # 此处的B模式逻辑保持不变，因为它不处理视频，不存在吸收间隙的问题
            config.logger.info("Building audio timeline based on original timings (video not processed).")
            last_end_time = 0
            for i, it in enumerate(self.queue_tts):
                silence_duration = it['start_time_source'] - last_end_time
                if silence_duration > 0: merged_audio += AudioSegment.silent(duration=silence_duration)
                it['start_time'] = len(merged_audio)

                dubb_time = int(tools.get_audio_time(it['filename']) * 1000) if tools.vail_file(it['filename']) else it['source_duration']
                segment = AudioSegment.from_file(it['filename']) if tools.vail_file(it['filename']) else AudioSegment.silent(duration=dubb_time)

                if len(segment) > dubb_time: segment = segment[:dubb_time]
                elif len(segment) < dubb_time: segment += AudioSegment.silent(duration=dubb_time - len(segment))
                merged_audio += segment
                
                it['end_time'] = len(merged_audio)
                last_end_time = it['end_time_source']
                it['startraw'], it['endraw'] = tools.ms_to_time_string(ms=it['start_time']), tools.ms_to_time_string(ms=it['end_time'])

        return merged_audio

    def _export_audio(self, audio_segment, destination_path):
        """将Pydub音频段导出到指定路径，处理不同格式。"""
        wavfile = Path(f'{self.cache_folder}/temp_{time.time_ns()}.wav').as_posix()
        try:
            audio_segment.export(wavfile, format="wav")
            ext = Path(destination_path).suffix.lower()
            if ext == '.wav':
                shutil.copy2(wavfile, destination_path)
            elif ext == '.m4a':
                tools.wav2m4a(wavfile, destination_path)
            else: # .mp3
                tools.runffmpeg(["-y", "-i", wavfile, "-ar", "48000", "-b:a", "192k", destination_path])
        finally:
            if Path(wavfile).exists():
                os.remove(wavfile)
    
    def _finalize_audio(self, merged_audio):
        """第六步：导出并对齐最终音视频时长（仅在视频被处理时）。"""
        tools.set_process(text="Exporting and finalizing audio...", uuid=self.uuid)
        try:
            self._export_audio(merged_audio, self.target_audio)

            video_was_processed = self.shoud_videorate and self.novoice_mp4_original and Path(self.novoice_mp4).name.startswith("merged_")
            if not video_was_processed:
                config.logger.info("Skipping duration alignment as video was not processed.")
                return

            if not (tools.vail_file(self.novoice_mp4) and tools.vail_file(self.target_audio)):
                config.logger.warning("Final video or audio file not found, skipping duration alignment.")
                return

            video_duration_ms = tools.get_video_duration(self.novoice_mp4)
            audio_duration_ms = int(tools.get_audio_time(self.target_audio) * 1000)
            
            padding_needed = video_duration_ms - audio_duration_ms

            if padding_needed > 10:
                config.logger.info(f"Audio is shorter than video by {padding_needed}ms. Padding with silence.")
                final_audio_segment = AudioSegment.from_file(self.target_audio)
                final_audio_segment += AudioSegment.silent(duration=padding_needed)
                self._export_audio(final_audio_segment, self.target_audio)
            elif padding_needed < -10:
                 config.logger.warning(f"Final audio is longer than video by {-padding_needed}ms. This may cause sync issues.")

        except Exception as e:
            config.logger.error(f"Failed to export or finalize audio: {e}")
            raise RuntimeError(f"Failed to finalize audio: {e}")
            
        config.logger.info("Final audio merged and aligned successfully.")