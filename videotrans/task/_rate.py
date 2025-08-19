import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from pydub import AudioSegment

from videotrans.configure import config
from videotrans.util import tools


class SpeedRate:
    """
通过音频加速和视频慢放来对齐翻译配音和原始视频时间轴。

主要实现原理
# 功能概述, 使用python3开发视频翻译功能：
1. 即A语言发音的视频，分离出无声画面视频文件和音频文件，使用语音识别对音频文件识别出原始字幕后，将该字幕翻译翻译为B语言的字幕，再将该B语言字幕配音为B语言配音，然后将B语言字幕和B语言配音同A分离出的无声视频，进行音画同步对齐和合并为新视频。
2. 当前正在做的这部分就是“配音、字幕、视频对齐”，B语言字幕是逐条配音的，每条字幕的配音生成一个mp3音频文件。
3. 因为语言不同，因此每条配音可能大于该条字幕的时间，例如该条字幕时长是3s，配音后的mp3时长如果小于等于3s，则不影响，但如果配音时长大于3s，则有问题，需要通过将音频片段自动加速到3s实现同步。也可以通过将该字幕的原始字幕所对应原始视频该片段截取下来，慢速播放延长该视频时长直到匹配配音时长，实现对齐。当然也可以同时 音频自动加速 和 视频慢速，从而避免音频加速太多或视频慢速太多。

# 具体音画同步原理说明

## 音频和视频同时启用时的策略
1. 如果配音时长 小于 当前片段的原始字幕时长，则无需音频加速和视频慢速
2. 如果配音时长 大于 当前片段的原始字幕时长，则判断音频时长缩短到和原始字幕时长一致时，需要的加速倍数是多少，
- 如果该倍数 小于等于 1.5，则照此对配音加速即可，无需视频慢速处理
- 如果该倍数 大于 1.5，则将 原始字幕时长 加上 和  下条字幕开始时间之间的静默时间(该静默可能时0，也可能小于或大于`self.MIN_CLIP_DURATION_MS`，如果最后一条字幕，可能到视频结尾还有静默区间),记为  total_a
   * 如果该时长 total_a 大于 配音时长，则配音无需加速，自然播放完毕即可，视频也无需慢速，注意因此导致的时间轴变化和对视频裁切的影响
   * 如果该时长 total_a 小于配音时长，则计算将配音时长缩短到 total_a 时，需要的加速倍数
        - 如果该倍数 小于等于 1.5，则照此加速音频即可，无需视频慢速，注意因此导致的时间轴变化和对视频裁切的影响
        - 如果该倍数 大于1.5，则按之前逻辑，音频加速和视频慢速各自负担一半

## 仅仅使用音频加速时

1. 如果配音时长 小于 当前片段的原始字幕时长，则无需音频加速
2. 如果配音时长 大于 当前片段的原始字幕时长，则计算将音频缩短到和原始字幕时长一致时，所需的加速倍数是多少，
- 如果该倍数 小于等于 1.5，则照此对配音加速即可
- 如果该倍数 大于 1.5，则将原始字幕时长加上 和  下条字幕开始时间之间的静默时间(可能时0，也可能小于或大于`self.MIN_CLIP_DURATION_MS`，如果最后一条字幕，可能到视频结尾还有静默区间),记为  total_b
   * 如果该时长 total_b 大于配音时长，则将配音无需加速，自然播放完毕即可，total_b 在容下配音后如果还有剩余空间则使用静音填充。
   * 如果该时长 total_b 仍小于配音时长，则无视倍数，强制将配音时长缩短到total_a
3. 注意开头和结尾以及字幕之间的静默区间，尤其是利用后可能还剩余的静默空间，最终合成后的音频长度，在存在视频时(self.novoice_mp4) 长度应等于视频长度，在不存在时，长度应等于从0到最后一条字幕的结束时间。

## 仅仅视频慢速时
1. 如果配音时长 小于 当前片段的原始字幕时长，则无需视频慢速，直接从本条字幕开始时间裁切到下条字幕开始时间，如果这是第一条字幕，则从0时间开始裁切
2. 如果配音时长 大于 当前片段的原始字幕时长，则判断原始字幕时长加上 和  下条字幕开始时间之间的静默时间(可能时0，也可能小于或大于`self.MIN_CLIP_DURATION_MS`,如果最后一条字幕，可能到视频结尾还有静默区间),记为  total_c
   * 如果该时长 total_c 大于 配音时长，则无需视频慢速，自然播放完毕即可，此时应裁切 total_c 时长的视频片段，即裁切到到下条字幕开始时间，而且无需慢速处理，同样如果这是第一条字幕，则从0时间开始裁切
   * 如果该时长 total_c 仍小于配音时长，强制将视频片段(时长为total_a) 慢速延长到和配音等长，此处注意下，如果PTS倍数大于10，可能失败，因此PTS最大为10，如果到10了，仍短于配音时长，则设PTS=10,并将配音时长强制缩短到和慢速后的视频一样长。
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
1. elf.novoice_mp4 is not None, 并且该文件存在，则为存在视频，此时比较合并后的音频时长和视频时长
    - 如果音频时长 小于 视频时长，则音频末尾填充静音直到长度一致
    - 如果音频时长 大于 视频时长，则视频最后定格延长，直到和音频时长一致
2. 如果不存在视频文件，则无需其他处理


## 小于 1024B 的视频片段可视为无效，过滤掉，容器、元信息加一帧图片，尺寸在 1024B以上

    ===============================================================================================
    """

    MIN_CLIP_DURATION_MS = 50
    # [新增] 统一所有中间音频文件的参数，防止拼接错误
    AUDIO_SAMPLE_RATE = 44100
    AUDIO_CHANNELS = 2

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
        self.noextname = noextname
        self.raw_total_time = raw_total_time
        self.queue_tts = queue_tts
        self.shoud_videorate = shoud_videorate
        self.shoud_audiorate = shoud_audiorate
        self.uuid = uuid
        self.novoice_mp4_original = novoice_mp4
        self.novoice_mp4 = novoice_mp4
        self.cache_folder = cache_folder if cache_folder else Path(
            f'{config.TEMP_DIR}/{str(uuid if uuid else time.time())}').as_posix()
        Path(self.cache_folder).mkdir(parents=True, exist_ok=True)
        # 音频片段缓存目录
        self.audio_clips_folder = Path(f'{self.cache_folder}/audio_clips').as_posix()
        Path(self.audio_clips_folder).mkdir(parents=True, exist_ok=True)

        self.target_audio_original = target_audio
        self.target_audio = Path(f'{self.cache_folder}/final_audio{Path(target_audio).suffix}').as_posix()

        self.max_audio_speed_rate = 100
        self.max_video_pts_rate = 10
        self.source_video_fps = 30

        # 检测并设置可用的音频变速滤镜
        self.audio_speed_filter = self._check_ffmpeg_filters()

        config.logger.info(
            f"SpeedRate 初始化。音频加速: {self.shoud_audiorate}, 视频慢速: {self.shoud_videorate}, 音频变速引擎: {self.audio_speed_filter}")
        config.logger.info(f"所有中间音频将统一为: {self.AUDIO_SAMPLE_RATE}Hz, {self.AUDIO_CHANNELS} 声道。")

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
                config.logger.info("检测到FFmpeg支持 'rubberband' 滤镜，将优先使用。")
                return 'rubberband'
            elif 'atempo' in filters_output:
                config.logger.info("未检测到 'rubberband' 滤镜，将使用 'atempo' 滤镜。")
                return 'atempo'
            else:
                config.logger.warning("FFmpeg中未检测到 'rubberband' 或 'atempo' 滤镜，音频加速功能可能受限。")
                return None
        except Exception as e:
            config.logger.error(f"检查FFmpeg滤镜时出错: {e}。将无法使用高质量音频变速。")
            return None

    def run(self):
        # =========================================================================================
        # 如果既不加速音频也不慢放视频
        if not self.shoud_audiorate and not self.shoud_videorate:
            config.logger.info("检测到未启用音视频变速，进入纯净拼接模式。")
            self._run_no_rate_change_mode()
            return self.queue_tts
        # 否则，执行加减速同步流程
        self._prepare_data()
        self._calculate_adjustments()
        self._execute_audio_speedup()
        clip_meta_list_with_real_durations = self._execute_video_processing()

        audio_concat_list = self._recalculate_timeline_and_merge_audio(clip_meta_list_with_real_durations)
        if audio_concat_list:
            self._finalize_files(audio_concat_list)
        return self.queue_tts

    def _standardize_audio_segment(self, segment):
        """[新增] 辅助函数，用于将任何AudioSegment对象标准化"""
        return segment.set_frame_rate(self.AUDIO_SAMPLE_RATE).set_channels(self.AUDIO_CHANNELS)

    def _run_no_rate_change_mode(self):
        """
        模式 不对音频视频做任何加减速处理。
        [重构] 现在此模式也使用基于FFmpeg的流式拼接，以处理大文件。
        1. 准备数据。
        2. 循环中，生成每个音频片段（配音+静音）的临时WAV文件。
        3. 生成一个文件列表供FFmpeg concat使用。
        4. 调用通用的 `_finalize_files` 方法来处理拼接和与视频的最终对齐。
        """
        process_text = "[纯净模式] 正在拼接音频..." if config.defaulelang == 'zh' else "[Pure Mode] Merging audio..."
        tools.set_process(text=process_text, uuid=self.uuid)
        config.logger.info("================== [纯净模式] 开始处理 ==================")

        self._prepare_data()

        audio_concat_list = []
        last_end_time = 0
        total_audio_duration = 0

        for i, it in enumerate(self.queue_tts):
            # 1. 填充字幕前的静音
            silence_duration = it['start_time_source'] - last_end_time
            if silence_duration > self.MIN_CLIP_DURATION_MS:
                silence_clip_path = Path(self.audio_clips_folder, f"{i:05d}_pre_silence.wav").as_posix()
                # [修正] 标准化静音参数
                silent_segment = AudioSegment.silent(duration=silence_duration)
                self._standardize_audio_segment(silent_segment).export(silence_clip_path, format="wav")
                audio_concat_list.append(silence_clip_path)
                config.logger.info(f"字幕[{it['line']}]前，生成静音片段 {silence_duration}ms")
                total_audio_duration += silence_duration

            # 加载并处理配音片段
            segment = None
            dubb_duration = 0
            if tools.vail_file(it['filename']):
                try:
                    # [修正] 标准化加载的音频
                    segment = AudioSegment.from_file(it['filename'])
                    segment = self._standardize_audio_segment(segment)
                    dubb_duration = len(segment)
                except Exception as e:
                    config.logger.error(f"字幕[{it['line']}] 加载音频文件 {it['filename']} 失败: {e}，将忽略此片段。")
            else:
                config.logger.warning(f"字幕[{it['line']}] 配音文件不存在: {it['filename']}，将忽略此片段。")

            it['dubb_time'] = dubb_duration

            if not segment:
                last_end_time = it['end_time_source']
                continue

            it['start_time'] = total_audio_duration
            it['end_time'] = it['start_time'] + it['dubb_time']
            it['startraw'], it['endraw'] = tools.ms_to_time_string(ms=it['start_time']), tools.ms_to_time_string(
                ms=it['end_time'])

            # 导出当前配音片段
            dub_clip_path = Path(self.audio_clips_folder, f"{i:05d}_dub.wav").as_posix()
            segment.export(dub_clip_path, format="wav")
            audio_concat_list.append(dub_clip_path)
            total_audio_duration += dubb_duration
            config.logger.info(
                f"字幕[{it['line']}] 已生成配音片段，时长: {dubb_duration}ms, 新时间区间: {it['start_time']}-{it['end_time']}")

            # 填充配音后的静音
            if i < len(self.queue_tts) - 1:
                next_start_time = self.queue_tts[i + 1]['start_time_source']
                available_space = next_start_time - it['start_time_source']
                if available_space >= dubb_duration:
                    remaining_silence = available_space - dubb_duration
                    if remaining_silence > self.MIN_CLIP_DURATION_MS:
                        post_silence_path = Path(self.audio_clips_folder, f"{i:05d}_post_silence.wav").as_posix()
                        # [修正] 标准化静音参数
                        silent_segment = AudioSegment.silent(duration=remaining_silence)
                        self._standardize_audio_segment(silent_segment).export(post_silence_path, format="wav")
                        audio_concat_list.append(post_silence_path)
                        total_audio_duration += remaining_silence
                        config.logger.info(f"字幕[{it['line']}]后，生成剩余静音片段 {remaining_silence}ms")
                    last_end_time = next_start_time
                else:
                    last_end_time = it['start_time_source'] + dubb_duration
            else:
                last_end_time = it['start_time'] + it['dubb_time']

        self._finalize_files(audio_concat_list)
        config.logger.info("================== [纯净模式] 处理完成 ==================")

    def _prepare_data(self):
        """
        此阶段为所有后续计算提供基础数据。关键是计算出 `source_duration` (原始时长)
        和 `silent_gap` (与下一条字幕的静默间隙)，这是所有策略判断的依据。
        同时，`final_video_duration_real` 字段也被初始化。
        :return:
        """
        tools.set_process(text="[1/5] 准备数据..." if config.defaulelang == 'zh' else "[1/5] Preparing data...",
                          uuid=self.uuid)
        config.logger.info("================== [阶段 1/5] 准备数据 ==================")

        if self.novoice_mp4_original and tools.vail_file(self.novoice_mp4_original):
            try:
                self.source_video_fps = tools.get_video_info(self.novoice_mp4_original, video_fps=True) or 30
            except Exception as e:
                config.logger.warning(f"无法探测源视频帧率，将使用默认值30。错误: {e}"); self.source_video_fps = 30
        config.logger.info(f"源视频帧率被设定为: {self.source_video_fps}")

        for it in self.queue_tts:
            it['start_time_source'] = it['start_time']
            it['end_time_source'] = it['end_time']
            it['source_duration'] = it['end_time_source'] - it['start_time_source']
            it['dubb_time'] = self._get_audio_time_ms(it['filename'], line=it['line'])
            it['final_audio_duration_theoretical'] = it['dubb_time']
            it['final_video_duration_theoretical'] = it['source_duration']
            # 用于存储探测到的物理时长
            it['final_video_duration_real'] = it['source_duration']

        for i, it in enumerate(self.queue_tts):
            if i < len(self.queue_tts) - 1:
                it['silent_gap'] = self.queue_tts[i + 1]['start_time_source'] - it['end_time_source']
            else:
                it['silent_gap'] = self.raw_total_time - it['end_time_source']
            it['silent_gap'] = max(0, it['silent_gap'])

    def _calculate_adjustments(self):
        """
        - `if self.shoud_audiorate and self.shoud_videorate:` 音频加速和视频慢速同时启用。
        - `elif self.shoud_audiorate:` 仅仅音频加速。
        - `elif self.shoud_videorate:` 仅仅视频慢速。
        里面的嵌套 `if` 则实现了更精细的策略，如“优先利用间隙”、“温和调整优先”等。
        最终，它会为每个需要调整的片段计算出一个“理论目标时长”。
        :return:
        """
        tools.set_process(text="[2/5] 计算调整方案..." if config.defaulelang == 'zh' else "[2/5] Calculating adjustments...",
                          uuid=self.uuid)
        config.logger.info("================== [阶段 2/5] 计算调整方案 ==================")

        for i, it in enumerate(self.queue_tts):
            config.logger.info(f"--- 开始分析字幕[{it['line']}] ---")
            dubb_duration = it['dubb_time']
            source_duration = it['source_duration']

            if source_duration <= 0 or dubb_duration <= 0:
                it['final_video_duration_theoretical'] = source_duration if source_duration > 0 else 0
                it['final_audio_duration_theoretical'] = dubb_duration if dubb_duration > 0 else 0
                config.logger.warning(f"字幕[{it['line']}] 原始时长({source_duration}ms)或配音时长({dubb_duration}ms)为0，跳过调整计算。")
                continue

            silent_gap = it['silent_gap']
            block_source_duration = source_duration + silent_gap

            config.logger.debug(
                f"字幕[{it['line']}]：原始数据：配音时长={dubb_duration}ms, 字幕时长={source_duration}ms, 静默间隙={silent_gap}ms, 可用总长={block_source_duration}ms")

            # 如果音频可以被原始时段容纳，则无需处理
            if dubb_duration <= source_duration:
                config.logger.info(f"字幕[{it['line']}]：配音({dubb_duration}ms) <= 字幕({source_duration}ms)，无需调整。")
                it['final_video_duration_theoretical'] = source_duration
                it['final_audio_duration_theoretical'] = dubb_duration  # 音频时长就是其本身
                continue

            target_duration = dubb_duration

            if self.shoud_audiorate and self.shoud_videorate:
                config.logger.debug(f"字幕[{it['line']}]：进入[音视频结合]决策模式。")
                speed_to_fit_source = dubb_duration / source_duration
                if speed_to_fit_source <= 1.5:
                    config.logger.info(
                        f"字幕[{it['line']}]：[决策] 仅需音频加速（倍率{speed_to_fit_source:.2f} <= 1.5），视频不慢放。目标时长将为原字幕时长。")
                    target_duration = source_duration
                elif block_source_duration >= dubb_duration:
                    config.logger.info(f"字幕[{it['line']}]：[决策] 利用静默间隙({silent_gap}ms)即可容纳配音，音视频均不变速。目标时长将为配音时长。")
                    target_duration = dubb_duration
                else:
                    speed_to_fit_block = dubb_duration / block_source_duration
                    if speed_to_fit_block <= 1.5:
                        config.logger.info(
                            f"字幕[{it['line']}]：[决策] 音频加速填满可用总长即可（倍率{speed_to_fit_block:.2f} <= 1.5）。目标时长将为可用总长。")
                        target_duration = block_source_duration
                    else:
                        config.logger.info(f"字幕[{it['line']}]：[决策] 加速倍率({speed_to_fit_block:.2f}) > 1.5，音视频共同承担调整。")
                        over_time = dubb_duration - block_source_duration
                        video_extension = over_time / 2
                        target_duration = int(block_source_duration + video_extension)
            elif self.shoud_audiorate:
                config.logger.debug(f"字幕[{it['line']}]：进入[仅音频加速]决策模式。")
                speed_to_fit_source = dubb_duration / source_duration
                if speed_to_fit_source <= 1.5:
                    config.logger.info(f"字幕[{it['line']}]：[决策] 加速倍率({speed_to_fit_source:.2f}) <= 1.5，压缩至原字幕时长。")
                    target_duration = source_duration
                elif block_source_duration >= dubb_duration:
                    config.logger.info(f"字幕[{it['line']}]：[决策] 利用静默间隙({silent_gap}ms)即可容纳，无需加速。目标时长将为配音时长。")
                    target_duration = dubb_duration
                else:
                    config.logger.info(f"字幕[{it['line']}]：[决策] 空间不足，强制压缩至可用总长({block_source_duration}ms)。")
                    target_duration = block_source_duration
            elif self.shoud_videorate:
                config.logger.debug(f"字幕[{it['line']}]：进入[仅视频慢速]决策模式。")
                if block_source_duration >= dubb_duration:
                    config.logger.info(f"字幕[{it['line']}]：[决策] 利用静默间隙({silent_gap}ms)即可容纳，无需慢放。目标时长为配音时长。")
                    target_duration = dubb_duration
                else:
                    config.logger.info(f"字幕[{it['line']}]：[决策] 空间不足，视频将慢放到配音时长。")
                    target_duration = dubb_duration

            # 为视频和音频分别设置理论目标时长
            it['final_audio_duration_theoretical'] = target_duration

            if self.shoud_videorate:
                # 当启用视频慢放时，视频的理论时长与音频目标时长一致
                video_target_duration = target_duration
                # 检查视频PTS限制
                # 视频慢放的目标是原始的 source_duration + silent_gap 这段区域
                pts_ratio = video_target_duration / block_source_duration if block_source_duration > 0 else 1.0
                if pts_ratio > self.max_video_pts_rate:
                    config.logger.warning(
                        f"字幕[{it['line']}]：计算出的视频慢放倍率({pts_ratio:.2f})超过最大值({self.max_video_pts_rate})，已强制修正。")
                    video_target_duration = int(block_source_duration * self.max_video_pts_rate)
                    # 如果视频被限制，音频也必须被压缩到同样的时长以保持同步
                    it['final_audio_duration_theoretical'] = video_target_duration
                it['final_video_duration_theoretical'] = video_target_duration
            else:
                # 在非视频慢放模式下，视频的理论时长等于它所占用的空间
                it['final_video_duration_theoretical'] = min(target_duration, block_source_duration)

            config.logger.info(
                f"字幕[{it['line']}]：[最终方案] 理论目标音频时长: {it['final_audio_duration_theoretical']}ms, 理论目标视频时长: {it['final_video_duration_theoretical']}ms")

    def _execute_audio_speedup(self):
        """
        使用FFmpeg的`rubberband`或`atempo`滤镜进行高质量音频变速。
        """
        tools.set_process(text="[3/5] 处理音频..." if config.defaulelang == 'zh' else "[3/5] Processing audio...",
                          uuid=self.uuid)
        config.logger.info("================== [阶段 3/5] 执行音频加速 ==================")

        if not self.audio_speed_filter:
            config.logger.warning("音频加速被跳过，因为未找到合适的FFmpeg滤镜。")
            return

        for it in self.queue_tts:
            target_duration_ms = int(it['final_audio_duration_theoretical'])
            current_duration_ms = it['dubb_time']

            # 只有在需要压缩时才处理
            if current_duration_ms > target_duration_ms and tools.vail_file(it['filename']):
                if target_duration_ms <= 0 or current_duration_ms - target_duration_ms < 20:  # 增加容差
                    continue

                speedup_ratio = current_duration_ms / target_duration_ms
                if speedup_ratio < 1.01: continue

                config.logger.info(
                    f"字幕[{it['line']}]：[执行] 音频加速，倍率={speedup_ratio:.2f} (从 {current_duration_ms}ms -> {target_duration_ms}ms) 使用 {self.audio_speed_filter} 引擎。")

                input_file = it['filename']
                temp_output_file = f"{Path(input_file).parent / (Path(input_file).stem + '_temp')}.wav"

                cmd = ['-y', '-i', input_file]

                filter_str = ""
                if self.audio_speed_filter == 'rubberband':
                    filter_str = f"rubberband=tempo={speedup_ratio}"
                elif self.audio_speed_filter == 'atempo':
                    tempo_filters = []
                    current_tempo = speedup_ratio
                    while current_tempo > 4.0:
                        tempo_filters.append("atempo=4.0")
                        current_tempo /= 4.0
                    if current_tempo >= 0.5:
                        tempo_filters.append(f"atempo={current_tempo}")
                    filter_str = ",".join(tempo_filters)

                if not filter_str:
                    config.logger.error(f"字幕[{it['line']}] 无法为倍率 {speedup_ratio:.2f} 构建有效的filter字符串，跳过变速。")
                    continue

                target_duration_sec = target_duration_ms / 1000.0
                cmd.extend(['-filter:a', filter_str, '-t', f'{target_duration_sec:.4f}'])

                # [修正] 确保输出是标准化的WAV
                cmd.extend(['-ar', str(self.AUDIO_SAMPLE_RATE), '-ac', str(self.AUDIO_CHANNELS), '-c:a', 'pcm_s16le',
                            temp_output_file])

                try:
                    if tools.runffmpeg(cmd, force_cpu=True):
                        shutil.move(temp_output_file, input_file)
                        it['dubb_time'] = self._get_audio_time_ms(input_file, line=it['line'])
                        config.logger.info(f"字幕[{it['line']}] 音频变速成功，新时长: {it['dubb_time']}ms")
                    else:
                        raise RuntimeError("ffmpeg command failed")
                except Exception as e:
                    config.logger.error(f"字幕[{it['line']}]：FFmpeg音频加速失败 {it['filename']}: {e}")
                    if Path(temp_output_file).exists():
                        os.remove(temp_output_file)

    def _execute_video_processing(self):
        """
        [修正] 视频处理阶段
        确保在处理完成后，返回包含了真实物理时长的`clip_meta_list`。
        """
        tools.set_process(
            text="[4/5] 处理视频并探测真实时长..." if config.defaulelang == 'zh' else "[4/5] Processing video & probing real durations...",
            uuid=self.uuid)
        config.logger.info("================== [阶段 4/5] 执行视频处理并探测真实时长 ==================")
        if not self.shoud_videorate or not self.novoice_mp4_original or not tools.vail_file(self.novoice_mp4_original):
            config.logger.warning("视频处理被跳过，因为未启用或无声视频文件不存在。")
            for it in self.queue_tts:
                it['final_video_duration_real'] = it['final_video_duration_theoretical']
            return None

        clip_meta_list = self._create_clip_meta()

        for task in clip_meta_list:
            if config.exit_soft: return None
            # PTS > 1.01 才应用，避免浮点数误差导致不必要的处理
            pts_param = str(task['pts']) if task.get('pts', 1.0) > 1.01 else None
            self._cut_to_intermediate(ss=task['ss'], to=task['to'], source=self.novoice_mp4_original, pts=pts_param,
                                      out=task['out'])

            real_duration_ms = 0
            if Path(task['out']).exists() and Path(task['out']).stat().st_size > 1024:
                real_duration_ms = self._get_video_duration_safe(task['out'])

            task['real_duration_ms'] = real_duration_ms

            if task['type'] == 'sub':
                sub_item = self.queue_tts[task['index']]
                sub_item['final_video_duration_real'] = real_duration_ms
                config.logger.info(
                    f"字幕[{task['line']}] 视频片段处理完成。理论时长: {sub_item['final_video_duration_theoretical']}ms, 物理探测时长: {real_duration_ms}ms")
            else:
                config.logger.info(f"间隙片段 {Path(task['out']).name} 处理完成。物理探测时长: {real_duration_ms}ms")

        self._concat_and_finalize(clip_meta_list)
        return clip_meta_list

    def _create_clip_meta(self):
        """
        创建视频裁切任务列表
        """
        clip_meta_list = []
        last_end_time = 0
        if not self.queue_tts: return []

        # 处理第一条字幕前的间隙
        first_sub_start = self.queue_tts[0]['start_time_source']
        if first_sub_start > self.MIN_CLIP_DURATION_MS:
            clip_path = Path(f'{self.cache_folder}/00000_first_gap.mp4').as_posix()
            clip_meta_list.append({"type": "gap", "out": clip_path, "ss": 0, "to": first_sub_start, "pts": 1.0})
            last_end_time = first_sub_start

        for i, it in enumerate(self.queue_tts):
            # 处理字幕间的间隙
            gap_start = last_end_time
            gap_end = it['start_time_source']
            if gap_end - gap_start >= self.MIN_CLIP_DURATION_MS:
                clip_path = Path(f'{self.cache_folder}/{i:05d}_gap.mp4').as_posix()
                clip_meta_list.append({"type": "gap", "out": clip_path, "ss": gap_start, "to": gap_end, "pts": 1.0})

            # 处理字幕本身
            if it['source_duration'] > 0:
                clip_path = Path(f"{self.cache_folder}/{i:05d}_sub.mp4").as_posix()
                # [修正] 视频慢放的目标是原始的 source_duration, 所以pts基于此计算
                pts_val = it['final_video_duration_theoretical'] / it['source_duration'] if it[
                                                                                                'source_duration'] > 0 else 1.0
                clip_meta_list.append({"type": "sub", "index": i, "out": clip_path, "ss": it['start_time_source'],
                                       "to": it['end_time_source'], "pts": pts_val, "line": it['line']})

            last_end_time = it['end_time_source']

        # 处理最后一条字幕后的间隙
        if self.raw_total_time - last_end_time >= self.MIN_CLIP_DURATION_MS:
            clip_path = Path(f'{self.cache_folder}/zzzz_final_gap.mp4').as_posix()
            clip_meta_list.append(
                {"type": "gap", "out": clip_path, "ss": last_end_time, "to": self.raw_total_time, "pts": 1.0})

        meta_path = Path(f'{self.cache_folder}/clip_meta.json').as_posix()
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(clip_meta_list, f, ensure_ascii=False, indent=2)
        return clip_meta_list

    def _cut_to_intermediate(self, ss, to, source, pts, out):
        """将视频片段裁切为标准化的中间格式"""
        cmd = ['-y', '-ss', tools.ms_to_time_string(ms=ss, sepflag='.'), '-to',
               tools.ms_to_time_string(ms=to, sepflag='.'), '-i', source,
               '-an', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '10',
               '-pix_fmt', 'yuv420p', '-r', str(self.source_video_fps)]
        if pts: cmd.extend(['-vf', f'setpts={pts}*PTS,fps={self.source_video_fps}'])
        cmd.append(out)

        config.logger.info(f"正在生成中间片段: {Path(out).name}, 原始范围: {ss}-{to}, PTS={pts or '1.0'}")

        try:
            tools.runffmpeg(cmd, force_cpu=True)
            if not Path(out).exists() and pts:
                config.logger.warning(f"中间片段 {Path(out).name} 生成失败，尝试无PTS参数重试。")
                if pts: cmd.pop(-2); cmd.pop(-2)
                tools.runffmpeg(cmd, force_cpu=True)
            if Path(out).exists():
                st_size = Path(out).stat().st_size
                if st_size < 1024:
                    config.logger.warning(f"中间片段 {Path(out).name} 生成成功，但尺寸为 {st_size} < 1024B，无效需删除。")
                    Path(out).unlink(missing_ok=True)
        except:
            try:
                Path(out).unlink(missing_ok=True)
            except:
                pass

    def _concat_and_finalize(self, clip_meta_list):
        """无损拼接中间片段，然后进行一次性的最终编码"""
        valid_clips = [task['out'] for task in clip_meta_list if
                       Path(task['out']).exists() and Path(task['out']).stat().st_size > 1024]
        if not valid_clips:
            config.logger.error("没有任何有效的视频中间片段生成，视频处理失败！")
            self.novoice_mp4 = self.novoice_mp4_original
            return

        concat_txt_path = Path(f'{self.cache_folder}/concat_list.txt').as_posix()
        try:
            tools.create_concat_txt(valid_clips, concat_txt=concat_txt_path)
        except ValueError as e:
            config.logger.error(f"创建视频拼接列表失败: {e}")
            return

        intermediate_merged_path = Path(f'{self.cache_folder}/intermediate_merged.mp4').as_posix()
        concat_cmd = ['-y', '-f', 'concat', '-safe', '0', '-i', concat_txt_path, '-c', 'copy', intermediate_merged_path]
        tools.runffmpeg(concat_cmd, force_cpu=True)

        if not Path(intermediate_merged_path).exists():
            config.logger.error("拼接后的中间视频文件未能生成，视频处理失败！")
            return

        final_video_path = Path(f'{self.cache_folder}/merged_{self.noextname}.mp4').as_posix()
        video_codec = config.settings['video_codec']
        finalize_cmd = ['-y', '-i', intermediate_merged_path, '-c:v', f'libx{video_codec}', '-crf',
                        str(config.settings.get("crf", 23)), '-preset', config.settings.get('preset', 'fast'), '-an',
                        final_video_path]
        tools.runffmpeg(finalize_cmd)

        if Path(final_video_path).exists():
            shutil.copy2(final_video_path, self.novoice_mp4)
            config.logger.info(f"最终无声视频已成功生成并复制到: {self.novoice_mp4}")
        else:
            config.logger.error("最终视频编码失败，保留原始无声视频。")
            self.novoice_mp4 = self.novoice_mp4_original
        # 删除临时片段
        for clip_path in valid_clips:
            try:
                if Path(clip_path).exists(): os.remove(clip_path)
            except:
                pass

        try:
            if Path(intermediate_merged_path).exists(): os.remove(intermediate_merged_path)
            if Path(concat_txt_path).exists(): os.remove(concat_txt_path)
        except:
            pass

    def _recalculate_timeline_and_merge_audio(self, clip_meta_list):
        """
        [修正] 音频重建阶段。
        根据 `shoud_videorate` 的值，正确分发到物理时间轴或理论时间轴模型。
        """
        process_text = "[5/5] 生成音频片段..." if config.defaulelang == 'zh' else "[5/5] Generating audio clips..."
        tools.set_process(text=process_text, uuid=self.uuid)
        config.logger.info("================== [阶段 5/5] 生成音频片段以供拼接 ==================")

        # [关键修正] 严格根据 `shoud_videorate` 和 `clip_meta_list` 的有效性来选择路径
        if self.shoud_videorate and clip_meta_list:
            config.logger.info("进入物理时间轴模型（基于视频片段真实时长）构建音频。")
            return self._recalculate_timeline_based_on_physical_video(clip_meta_list)
        else:
            config.logger.info("进入理论时间轴模型（基于计算偏移）构建音频。")
            return self._recalculate_timeline_with_theoretical_offset()

    def _recalculate_timeline_based_on_physical_video(self, clip_meta_list):
        """
        [新增] 基于视频片段的物理真实时长来构建音频片段列表。
        此方法仅在 `shoud_videorate=True` 时被调用。
        """
        audio_concat_list = []
        current_timeline_ms = 0

        for i, task in enumerate(clip_meta_list):
            task_real_duration = int(task.get('real_duration_ms', 0))
            if task_real_duration <= 0:
                continue

            clip_path = Path(self.audio_clips_folder, f"v_clip_{i:05d}.wav").as_posix()
            segment = None

            if task['type'] == 'gap':
                segment = AudioSegment.silent(duration=task_real_duration)
                config.logger.info(f"生成物理间隙音频片段：时长 {task_real_duration}ms -> {clip_path}")
                current_timeline_ms += task_real_duration

            elif task['type'] == 'sub':
                it = self.queue_tts[task['index']]
                it['start_time'] = current_timeline_ms
                it['end_time'] = it['start_time'] + it['dubb_time']
                it['startraw'], it['endraw'] = tools.ms_to_time_string(ms=it['start_time']), tools.ms_to_time_string(
                    ms=it['end_time'])
                config.logger.info(
                    f"字幕[{it['line']}] 字幕时间精确化：新区间 {it['start_time']}-{it['end_time']} (配音时长 {it['dubb_time']}ms)")

                # 创建一个与视频片段等长的静音画布
                base_segment = AudioSegment.silent(duration=task_real_duration)

                if tools.vail_file(it['filename']):
                    try:
                        audio_clip = AudioSegment.from_file(it['filename'])
                        # 将配音叠加到静音画布的开头
                        segment = base_segment.overlay(audio_clip)
                    except Exception as e:
                        config.logger.error(f"字幕[{it['line']}] 加载音频失败: {e}，使用等长静音替代。")
                        segment = base_segment
                else:
                    config.logger.warning(f"字幕[{it['line']}] 配音文件不存在，使用等长静音替代。")
                    segment = base_segment

                current_timeline_ms += task_real_duration
                config.logger.info(f"字幕[{it['line']}] 音频流重建：生成片段，时长 {task_real_duration}ms -> {clip_path}")

            if segment:
                # [核心修正] 导出前统一所有片段的参数
                self._standardize_audio_segment(segment).export(clip_path, format="wav")
                audio_concat_list.append(clip_path)

        return audio_concat_list

    def _recalculate_timeline_with_theoretical_offset(self):
        """
        [修正] 备用方法：当不处理视频时，生成基于理论 time_offset 的音频片段列表。
        修正了时间轴计算的逻辑错误，避免不正确的静音累积。
        """
        audio_concat_list = []
        time_offset = 0
        current_timeline_ms = 0

        for i, it in enumerate(self.queue_tts):
            target_start_time = it['start_time_source'] + time_offset

            it['start_time'] = target_start_time
            it['end_time'] = it['start_time'] + it['dubb_time']
            it['startraw'], it['endraw'] = tools.ms_to_time_string(ms=it['start_time']), tools.ms_to_time_string(
                ms=it['end_time'])
            config.logger.info(
                f"字幕[{it['line']}] 字幕时间精确化：新区间 {it['start_time']}-{it['end_time']} (配音时长 {it['dubb_time']}ms)")

            silence_needed = max(0, target_start_time - current_timeline_ms)

            if silence_needed > self.MIN_CLIP_DURATION_MS:
                silence_path = Path(self.audio_clips_folder, f"t_clip_{i:05d}_silence.wav").as_posix()
                # [修正] 标准化
                silent_segment = AudioSegment.silent(duration=silence_needed)
                self._standardize_audio_segment(silent_segment).export(silence_path, format="wav")
                audio_concat_list.append(silence_path)
                current_timeline_ms += silence_needed
                config.logger.info(f"理论模式：字幕[{it['line']}]前插入静音 {silence_needed}ms")

            final_segment_duration = int(it['final_audio_duration_theoretical'])
            if final_segment_duration <= 0:
                time_offset += (final_segment_duration - it['source_duration'])
                continue

            # 创建一个目标时长的静音画布
            base_segment = AudioSegment.silent(duration=final_segment_duration)
            segment = base_segment
            if tools.vail_file(it['filename']):
                try:
                    audio_clip = AudioSegment.from_file(it['filename'])
                    # 叠加配音
                    segment = base_segment.overlay(audio_clip)
                except Exception as e:
                    config.logger.error(f"字幕[{it['line']}] 加载音频失败: {e}，使用等长静音替代。")
            else:
                config.logger.warning(f"字幕[{it['line']}] 配音文件不存在，使用等长静音替代。")

            clip_path = Path(self.audio_clips_folder, f"t_clip_{i:05d}_sub.wav").as_posix()
            # [修正] 标准化
            self._standardize_audio_segment(segment).export(clip_path, format="wav")
            audio_concat_list.append(clip_path)

            current_timeline_ms += final_segment_duration
            time_offset += (final_segment_duration - it['source_duration'])
            config.logger.info(f"理论模式：字幕[{it['line']}]生成片段，时长 {final_segment_duration}ms，累积时间偏移 {time_offset}ms")

        # 理论模式下的最终视频时长
        final_video_duration = self.raw_total_time + time_offset
        final_gap = final_video_duration - current_timeline_ms
        if final_gap > self.MIN_CLIP_DURATION_MS:
            # final_gap_path = Path(self.audio_clips_folder, "t_clip_zzzz_final_gap.wav").as_posix()
            final_gap_path = Path(self.audio_clips_folder, "t_clip_zzzz_final_gap.wav").as_posix()
            # [修正] 标准化
            silent_segment = AudioSegment.silent(duration=final_gap)
            self._standardize_audio_segment(silent_segment).export(final_gap_path, format="wav")
            audio_concat_list.append(final_gap_path)
            config.logger.info(f"理论模式：末尾添加静音 {final_gap}ms")
        config.logger.info(f"{audio_concat_list=}")
        return audio_concat_list

    def _get_video_duration_safe(self, file_path):
        """
        一个健壮的视频时长获取方法。
        """
        path_obj = Path(file_path)
        if not path_obj.exists() or path_obj.stat().st_size == 0:
            config.logger.warning(f"视频时长探测失败：文件不存在或为空 -> {file_path}")
            return 0
        try:
            duration_ms = tools.get_video_info(file_path, video_time=True)
            if duration_ms is None:
                config.logger.warning(f"视频时长探测返回 None，可能文件已损坏 -> {file_path}")
                return 0
            return duration_ms
        except Exception as e:
            config.logger.error(f"探测视频时长时发生严重错误: {e}。文件 -> {file_path}。将视其时长为0。")
            return 0

    def _finalize_files(self, audio_concat_list):
        """
        负责使用FFmpeg拼接音频片段列表，并执行最后的音视频对齐检查。
        """
        final_step_text = "[最终步骤] 拼接音频并对齐..." if config.defaulelang == 'zh' else '[Final Step] Concatenating audio and finalizing...'
        tools.set_process(text=final_step_text, uuid=self.uuid)
        config.logger.info("================== [最终步骤] 拼接音频、对齐并交付 ==================")

        try:
            # 初始拼接
            self._ffmpeg_concat_audio(audio_concat_list, self.target_audio)

            if not tools.vail_file(self.target_audio):
                raise RuntimeError(f"音频拼接失败，最终文件未生成: {self.target_audio}")

            if self.novoice_mp4 and tools.vail_file(self.novoice_mp4):
                config.logger.info("开始最终音视频时长对齐检查...")
                video_duration_ms = self._get_video_duration_safe(self.novoice_mp4)
                if video_duration_ms == 0:
                    raise RuntimeError(f'视频时长为0，无法对齐: {self.novoice_mp4}')

                audio_duration_ms = self._get_audio_time_ms(self.target_audio)
                if audio_duration_ms == 0:
                    raise RuntimeError(f'拼接后音频时长为0，无法对齐: {self.target_audio}')

                config.logger.info(f"最终检查: 视频物理总长 = {video_duration_ms}ms, 音频物理总长 = {audio_duration_ms}ms")
                duration_diff = video_duration_ms - audio_duration_ms
                config.logger.info(f"时长差异 (视频 - 音频) = {duration_diff}ms")

                TOLERANCE_MS = 250

                if duration_diff > TOLERANCE_MS:
                    config.logger.warning(f"视频比音频长 {duration_diff}ms，将通过FFmpeg apad滤镜在音频末尾补齐等长静音。")

                    # [核心修正] 使用FFmpeg apad滤镜高效添加静音，而不是pydub
                    padded_audio_path = Path(
                        f'{self.cache_folder}/padded_audio{Path(self.target_audio).suffix}').as_posix()
                    pad_dur_sec = duration_diff / 1000.0

                    cmd = ['-y', '-i', str(self.target_audio), '-af', f'apad=pad_dur={pad_dur_sec:.4f}']

                    # 保持编码参数一致
                    ext = Path(self.target_audio).suffix.lower()
                    if ext == '.wav':
                        cmd.extend(["-c:a", "pcm_s16le"])
                    elif ext == '.m4a':
                        cmd.extend(["-c:a", "aac", "-b:a", "128k"])
                    else:  # 默认mp3
                        cmd.extend(["-c:a", "libmp3lame", "-q:a", "2"])
                    cmd.append(padded_audio_path)

                    if tools.runffmpeg(cmd) and tools.vail_file(padded_audio_path):
                        shutil.move(padded_audio_path, self.target_audio)
                        config.logger.info("音频补齐静音并重新导出完成。")
                    else:
                        config.logger.error("使用apad滤镜填充静音失败！")


                elif duration_diff < -TOLERANCE_MS:
                    freeze_duration_sec = abs(duration_diff) / 1000.0
                    config.logger.warning(f"音频比视频长 {abs(duration_diff)}ms，将定格视频最后一帧 {freeze_duration_sec:.3f} 秒以对齐。")

                    final_video_path = Path(f'{self.cache_folder}/final_video_with_freeze.mp4').as_posix()
                    cmd = ['-y', '-i', self.novoice_mp4,
                           '-vf', f'tpad=stop_mode=clone:stop_duration={freeze_duration_sec}',
                           '-c:v', f'libx{config.settings["video_codec"]}',
                           '-crf', str(config.settings.get("crf", 23)),
                           '-preset', config.settings.get('preset', 'fast'),
                           '-an', final_video_path]

                    if tools.runffmpeg(cmd, force_cpu=True) and Path(final_video_path).exists():
                        shutil.copy2(final_video_path, self.novoice_mp4)
                        config.logger.info("视频定格延长操作成功。")
                    else:
                        config.logger.error("视频定格延长操作失败！音视频可能存在时长不一致。")
                else:
                    config.logger.info("音视频时长差异在容忍范围内，无需额外对齐处理。")

            if Path(self.target_audio).exists():
                try:
                    shutil.copy2(self.target_audio, self.target_audio_original)
                    config.logger.info(f"最终音频文件已成功交付到: {self.target_audio_original}")
                except shutil.SameFileError:
                    pass
            else:
                config.logger.error(f"最终音频文件 {self.target_audio} 未能生成，交付失败！")

        except Exception as e:
            config.logger.exception(f"导出或对齐最终音视频时发生致命错误: {e}")
            raise RuntimeError(f"导出或对齐最终音视频时发生致命错误: {e}")

        config.logger.info("所有处理完成，音视频已成功生成。")

    def _get_audio_time_ms(self, file_path, line=None):
        if not tools.vail_file(file_path):
            if line is not None: config.logger.warning(f"字幕[{line}]：配音文件 {file_path} 不存在。")
            return 0
        try:
            # 优先使用 ffprobe，更准确
            duration = tools.get_audio_time(file_path)
            if duration is not None:
                return int(duration * 1000)
            # ffprobe 失败时，使用 pydub 作为备用
            return len(AudioSegment.from_file(file_path))
        except Exception as e:
            config.logger.error(f"字幕[{line or 'N/A'}]：获取音频文件 {file_path} 时长失败: {e}")
            return 0

    def _ffmpeg_concat_audio(self, file_list, output_path):
        """
        [核心修正] 使用混合拼接法来健壮地拼接大量音频文件，以规避Windows命令行长度限制。
        步骤1: 使用concat demuxer + 重新编码，生成一个临时的、干净的WAV文件。
        步骤2: 将这个临时的WAV文件转码为最终的目标格式。
        """
        if not file_list:
            config.logger.warning("音频拼接列表为空，无法生成最终音频。")
            return

        concat_txt_path = Path(f'{self.cache_folder}/audio_clips/audio_concat_list.txt').as_posix()
        temp_wav_output = Path(f'{self.cache_folder}/temp_concatenated.wav').as_posix()

        try:
            # 步骤1: 使用concat demuxer进行稳定的拼接
            config.logger.info(f"混合拼接步骤1: 创建包含 {len(file_list)} 个文件的拼接列表。{concat_txt_path=}")
            tools.create_concat_txt(file_list, concat_txt=concat_txt_path)
            if not Path(concat_txt_path).exists():
                raise RuntimeError(f"No {concat_txt_path}")

            cmd_step1 = [
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_txt_path,
                "-c:a", "pcm_s16le",
                "-ar", str(self.AUDIO_SAMPLE_RATE),
                "-ac", str(self.AUDIO_CHANNELS),
                temp_wav_output
            ]
            config.logger.info(f"混合拼接步骤1: 正在将列表拼接并重新编码为临时WAV文件: {temp_wav_output}")
            tools.runffmpeg(cmd_step1, force_cpu=True)
            os.chdir(config.ROOT_DIR)

            if not tools.vail_file(temp_wav_output):
                config.logger.error(f"音频拼接失败，临时文件 {temp_wav_output} 未生成。")
                return

            # 步骤2: 将拼接好的临时WAV转码为最终格式
            config.logger.info(f"混合拼接步骤2: 正在将临时WAV转码为最终格式: {output_path}")
            cmd_step2 = ["-y", "-i", temp_wav_output]

            ext = Path(output_path).suffix.lower()
            if ext == '.wav':
                # 如果目标就是wav，直接复制即可
                cmd_step2.extend(["-c:a", "copy"])
            elif ext == '.m4a':
                cmd_step2.extend(["-c:a", "aac", "-b:a", "128k"])
            else:  # 默认mp3
                cmd_step2.extend(["-c:a", "libmp3lame", "-q:a", "2"])

            cmd_step2.append(str(output_path))
            if ext == '.wav' and output_path[-4:] == '.wav':
                try:
                    shutil.copy2(temp_wav_output, output_path)
                except shutil.SameFileError:
                    pass
            else:
                tools.runffmpeg(cmd_step2, force_cpu=True)

        finally:
            pass
            # 清理临时文件
            try:
                if Path(concat_txt_path).exists():
                    os.remove(concat_txt_path)
                if Path(temp_wav_output).exists():
                    os.remove(temp_wav_output)
                config.logger.info("已清理音频拼接临时文件。")
            except Exception as e:
                config.logger.warning(f"清理音频拼接临时文件失败: {e}")
