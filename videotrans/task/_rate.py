import os
import shutil
import time
from pathlib import Path
import json

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
   * 如果该时长 total_c 大于配音时长，则无需视频慢速，自然播放完毕即可，此时应裁切 total_c 时长的视频片段，即裁切到到下条字幕开始时间，而且无需慢速处理，同样如果这是第一条字幕，则从0时间开始裁切
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



    ===============================================================================================
    """

    MIN_CLIP_DURATION_MS = 50

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
        self.noextname=noextname
        self.raw_total_time=raw_total_time
        self.queue_tts = queue_tts
        self.shoud_videorate = shoud_videorate
        self.shoud_audiorate = shoud_audiorate
        self.uuid = uuid
        self.novoice_mp4_original = novoice_mp4
        self.novoice_mp4 = novoice_mp4
        self.cache_folder = cache_folder if cache_folder else Path(f'{config.TEMP_DIR}/{str(uuid if uuid else time.time())}').as_posix()
        Path(self.cache_folder).mkdir(parents=True, exist_ok=True)

        self.target_audio_original = target_audio
        self.target_audio = Path(f'{self.cache_folder}/final_audio{Path(target_audio).suffix}').as_posix()

        self.max_audio_speed_rate = 100

        self.max_video_pts_rate = 10

        self.source_video_fps = 30

        config.logger.info(f"SpeedRate 初始化。音频加速: {self.shoud_audiorate}, 视频慢速: {self.shoud_videorate}")

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
        merged_audio = self._recalculate_timeline_and_merge_audio(clip_meta_list_with_real_durations)
        if merged_audio:
            self._finalize_files(merged_audio)
        return self.queue_tts

    def _run_no_rate_change_mode(self):
        """
        模式四：“纯净拼接”的完整实现。
        1. 准备数据。
        2. `last_end_time` 精确测量并填充字幕间的静音。
        3. 循环中，拼接配音，然后根据“可用空间”和“配音时长”的关系，决定如何填充后续静音。
        4. 所有片段拼接完后，调用通用的 `_finalize_files` 方法来处理与视频的最终对齐。
        """
        process_text = "[纯净模式] 正在拼接音频..." if config.defaulelang == 'zh' else "[Pure Mode] Merging audio..."
        tools.set_process(text=process_text, uuid=self.uuid)
        config.logger.info("================== [纯净模式] 开始处理 ==================")

        # 确保基础数据已准备
        self._prepare_data()

        merged_audio = AudioSegment.empty()
        last_end_time = 0

        # 第一步：按字幕拼接音频
        for i, it in enumerate(self.queue_tts):
            # 1. 填充字幕前的静音
            silence_duration = it['start_time_source'] - last_end_time
            if silence_duration > 0:
                merged_audio += AudioSegment.silent(duration=silence_duration)
                config.logger.info(f"字幕[{it['line']}]前，填充静音 {silence_duration}ms")

            # 加载配音片段
            segment = None
            if tools.vail_file(it['filename']):
                try:
                    segment = AudioSegment.from_file(it['filename'])
                except Exception as e:
                    config.logger.error(f"字幕[{it['line']}] 加载音频文件 {it['filename']} 失败: {e}，将忽略此片段。")
            else:
                config.logger.warning(f"字幕[{it['line']}] 配音文件不存在: {it['filename']}，将忽略此片段。")

            if not segment:
                last_end_time = it['end_time_source'] # 即使音频不存在，也要推进时间轴
                continue

            # 更新字幕的新时间戳
            it['start_time'] = len(merged_audio)
            it['end_time'] = it['start_time'] + len(segment)
            it['startraw'], it['endraw'] = tools.ms_to_time_string(ms=it['start_time']), tools.ms_to_time_string(ms=it['end_time'])

            merged_audio += segment
            config.logger.info(f"字幕[{it['line']}] 已拼接，配音时长: {len(segment)}ms, 新时间区间: {it['start_time']}-{it['end_time']}")

            # 2. & 3. 填充配音后的静音（如果适用）
            if i < len(self.queue_tts) - 1:
                next_start_time = self.queue_tts[i+1]['start_time_source']
                available_space = next_start_time - it['start_time_source']

                if available_space >= len(segment):
                    remaining_silence = available_space - len(segment)
                    if remaining_silence > 0:
                        merged_audio += AudioSegment.silent(duration=remaining_silence)
                        config.logger.info(f"字幕[{it['line']}]后，填充剩余静音 {remaining_silence}ms")
                    last_end_time = next_start_time
                else:
                    # 配音时长 > 可用空间，直接连接下一个，时间轴自然被推后
                    last_end_time = it['start_time_source'] + len(segment)
            else:
                # 4. 最后一条字幕，后面不再填充静音
                last_end_time = it['end_time']

        # 第二步：检查视频文件并对齐
        self._finalize_files(merged_audio)
        config.logger.info("================== [纯净模式] 处理完成 ==================")

    def _prepare_data(self):
        """
        此阶段为所有后续计算提供基础数据。关键是计算出 `source_duration` (原始时长)
        和 `silent_gap` (与下一条字幕的静默间隙)，这是所有策略判断的依据。
        同时，`final_video_duration_real` 字段也被初始化。
        :return:
        """
        tools.set_process(text="[1/5] 准备数据..." if config.defaulelang == 'zh' else "[1/5] Preparing data...", uuid=self.uuid)
        config.logger.info("================== [阶段 1/5] 准备数据 ==================")

        if self.novoice_mp4_original and tools.vail_file(self.novoice_mp4_original):
            try: self.source_video_fps = tools.get_video_info(self.novoice_mp4_original, video_fps=True) or 30
            except Exception as e: config.logger.warning(f"无法探测源视频帧率，将使用默认值30。错误: {e}"); self.source_video_fps = 30
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
        tools.set_process(text="[2/5] 计算调整方案..." if config.defaulelang == 'zh' else "[2/5] Calculating adjustments...", uuid=self.uuid)
        config.logger.info("================== [阶段 2/5] 计算调整方案 ==================")

        for i, it in enumerate(self.queue_tts):
            config.logger.info(f"--- 开始分析字幕[{it['line']}] ---")
            dubb_duration = it['dubb_time']
            source_duration = it['source_duration']

            if source_duration <= 0:
                it['final_video_duration_theoretical'] = 0
                it['final_audio_duration_theoretical'] = 0
                config.logger.warning(f"字幕[{it['line']}] 原始时长为0，跳过处理。")
                continue

            silent_gap = it['silent_gap']
            block_source_duration = source_duration + silent_gap

            config.logger.debug(f"字幕[{it['line']}]：原始数据：配音时长={dubb_duration}ms, 字幕时长={source_duration}ms, 静默间隙={silent_gap}ms, 片段块总长={block_source_duration}ms")

            # 如果音频可以被原始时段容纳，则无需处理
            if dubb_duration <= source_duration:
                config.logger.info(f"字幕[{it['line']}]：配音({dubb_duration}ms) <= 字幕({source_duration}ms)，无需调整。")
                it['final_video_duration_theoretical'] = source_duration
                it['final_audio_duration_theoretical'] = dubb_duration
                continue

            target_duration = dubb_duration

            if self.shoud_audiorate and self.shoud_videorate:
                config.logger.debug(f"字幕[{it['line']}]：进入[音视频结合]决策模式。")
                speed_to_fit_source = dubb_duration / source_duration
                if speed_to_fit_source <= 1.5:
                    config.logger.info(f"字幕[{it['line']}]：[决策] 仅需音频加速（倍率{speed_to_fit_source:.2f} <= 1.5），视频不慢放。")
                    target_duration = source_duration
                elif block_source_duration >= dubb_duration:
                    config.logger.info(f"字幕[{it['line']}]：[决策] 利用静默间隙即可容纳配音，音视频均不变速。")
                    target_duration = dubb_duration
                else:
                    speed_to_fit_block = dubb_duration / block_source_duration
                    if speed_to_fit_block <= 1.5:
                        config.logger.info(f"字幕[{it['line']}]：[决策] 音频加速填满片段块即可（倍率{speed_to_fit_block:.2f} <= 1.5）。")
                        target_duration = block_source_duration
                    else:
                        config.logger.info(f"字幕[{it['line']}]：[决策] 倍率({speed_to_fit_block:.2f}) > 1.5，音视频共同承担调整。")
                        over_time = dubb_duration - block_source_duration
                        video_extension = over_time / 2
                        target_duration = int(block_source_duration + video_extension)
            elif self.shoud_audiorate:
                config.logger.debug(f"字幕[{it['line']}]：进入[仅音频加速]决策模式。")
                speed_to_fit_source = dubb_duration / source_duration
                if speed_to_fit_source <= 1.5:
                    target_duration = source_duration
                elif block_source_duration >= dubb_duration:
                    target_duration = dubb_duration
                else:
                    target_duration = block_source_duration
            elif self.shoud_videorate:
                config.logger.debug(f"字幕[{it['line']}]：进入[仅视频慢速]决策模式。")
                if block_source_duration >= dubb_duration:
                    target_duration = dubb_duration
                else:
                    target_duration = dubb_duration

            if self.shoud_videorate:
                pts_ratio = target_duration / source_duration
                if pts_ratio > self.max_video_pts_rate:
                    config.logger.warning(f"字幕[{it['line']}]：计算出的PTS({pts_ratio:.2f})超过最大值({self.max_video_pts_rate})，已强制修正。")
                    target_duration = int(source_duration * self.max_video_pts_rate)

            it['final_video_duration_theoretical'] = target_duration
            it['final_audio_duration_theoretical'] = target_duration

            config.logger.info(f"字幕[{it['line']}]：[最终方案] 理论目标音视频时长统一为: {target_duration}ms")

    def _execute_audio_speedup(self):
        """
        1.  遍历所有字幕，检查 `dubb_time` 是否大于 `final_audio_duration`。
        2.  对于需要处理的音频，计算出精确的加速倍率。
        3.  使用 `pydub.speedup` 执行变速。
        4.  **精度微调**: 变速后，使用切片操作 (`[:target_duration_ms]`) 对音频进行微调，确保其最终时长与目标值的误差在10ms以内。
        5.  用处理后的真实时长更新 `it['dubb_time']`。

        :return:
        """
        tools.set_process(text="[3/5] 处理音频..." if config.defaulelang == 'zh' else "[3/5] Processing audio...", uuid=self.uuid)
        config.logger.info("================== [阶段 3/5] 执行音频加速 ==================")

        for it in self.queue_tts:
            target_duration_ms = int(it['final_audio_duration_theoretical'])
            if it['dubb_time'] > target_duration_ms and tools.vail_file(it['filename']):
                try:
                    current_duration_ms = it['dubb_time']
                    if target_duration_ms <= 0 or current_duration_ms - target_duration_ms < 10:
                        continue

                    speedup_ratio = current_duration_ms / target_duration_ms
                    if speedup_ratio < 1.01: continue

                    if speedup_ratio > self.max_audio_speed_rate:
                        config.logger.warning(f"字幕[{it['line']}]：计算出的音频加速倍率({speedup_ratio:.2f})超过限制({self.max_audio_speed_rate})，已强制应用最大值。")
                        speedup_ratio = self.max_audio_speed_rate

                    config.logger.info(f"字幕[{it['line']}]：[执行] 音频加速，倍率={speedup_ratio:.2f} (从 {current_duration_ms}ms -> {target_duration_ms}ms)")
                    audio = AudioSegment.from_file(it['filename'])
                    fast_audio = audio.speedup(playback_speed=speedup_ratio)

                    if len(fast_audio) > target_duration_ms: fast_audio = fast_audio[:target_duration_ms]

                    fast_audio.export(it['filename'], format=Path(it['filename']).suffix[1:])
                    it['dubb_time'] = self._get_audio_time_ms(it['filename'], line=it['line'])
                except Exception as e:
                    config.logger.error(f"字幕[{it['line']}]：音频加速失败 {it['filename']}: {e}")

    def _execute_video_processing(self):
        """
        视频处理阶段
        它的主要任务不再仅仅是处理视频，而是“测量物理现实”。
        1. `_create_clip_meta`：创建一个包含所有裁切任务的“蓝图”。
        2. 循环遍历蓝图，调用 `_cut_to_intermediate` 生成每个视频片段。
        3. **关键一步**：片段生成后，`real_duration_ms = tools.get_video_duration(task['out'])`
           这行代码就是“物理探测仪”，它测量出片段的真实时长。
        4. 将真实时长存回任务元数据中，供后续的音频重建阶段使用。

        :return:
        """
        tools.set_process(text="[4/5] 处理视频并探测真实时长..." if config.defaulelang == 'zh' else "[4/5] Processing video & probing real durations...", uuid=self.uuid)
        config.logger.info("================== [阶段 4/5] 执行视频处理并探测真实时长 ==================")
        if not self.shoud_videorate or not self.novoice_mp4_original:
            return None

        clip_meta_list = self._create_clip_meta()

        for task in clip_meta_list:
            if config.exit_soft: return None
            pts_param = str(task['pts']) if task.get('pts', 1.0) > 1.01 else None
            self._cut_to_intermediate(ss=task['ss'], to=task['to'], source=self.novoice_mp4_original, pts=pts_param, out=task['out'])

            real_duration_ms = 0
            if Path(task['out']).exists() and Path(task['out']).stat().st_size > 0:
                real_duration_ms = tools.get_video_duration(task['out'])

            task['real_duration_ms'] = real_duration_ms

            if task['type'] == 'sub':
                sub_item = self.queue_tts[task['index']]
                sub_item['final_video_duration_real'] = real_duration_ms
                config.logger.info(f"字幕[{task['line']}] 视频片段处理完成。理论时长: {sub_item['final_video_duration_theoretical']}ms, 物理探测时长: {real_duration_ms}ms")
            else:
                config.logger.info(f"间隙片段 {Path(task['out']).name} 处理完成。物理探测时长: {real_duration_ms}ms")


        self._concat_and_finalize(clip_meta_list)
        return clip_meta_list

    def _create_clip_meta(self):
        """
        - 遍历字幕，将每个“字幕”和其前后的“有效间隙”都创建为一个独立的裁切任务。
        - 计算每个字幕片段最终的PTS值：`final_video_duration / source_duration`。
        :return:
        """
        clip_meta_list = []
        if not self.queue_tts: return []

        if self.queue_tts[0]['start_time_source'] > self.MIN_CLIP_DURATION_MS:
            clip_path = Path(f'{self.cache_folder}/00000_first_gap.mp4').as_posix()
            clip_meta_list.append({"type": "gap", "out": clip_path, "ss": 0, "to": self.queue_tts[0]['start_time_source'], "pts": 1.0})

        for i, it in enumerate(self.queue_tts):
            if i > 0:
                gap_start = self.queue_tts[i-1]['end_time_source']
                gap_end = it['start_time_source']
                if gap_end - gap_start >= self.MIN_CLIP_DURATION_MS:
                    clip_path = Path(f'{self.cache_folder}/{i:05d}_gap.mp4').as_posix()
                    clip_meta_list.append({"type": "gap", "out": clip_path, "ss": gap_start, "to": gap_end, "pts": 1.0})

            if it['source_duration'] > 0:
                 clip_path = Path(f"{self.cache_folder}/{i:05d}_sub.mp4").as_posix()
                 pts_val = it['final_video_duration_theoretical'] / it['source_duration'] if it['source_duration'] > 0 else 1.0
                 clip_meta_list.append({"type": "sub", "index": i, "out": clip_path, "ss": it['start_time_source'], "to": it['end_time_source'], "pts": pts_val, "line": it['line']})

        last_item = self.queue_tts[-1]
        final_gap_start = last_item['end_time_source']
        if self.raw_total_time - final_gap_start >= self.MIN_CLIP_DURATION_MS:
            clip_path = Path(f'{self.cache_folder}/zzzz_final_gap.mp4').as_posix()
            clip_meta_list.append({"type": "gap", "out": clip_path, "ss": final_gap_start, "to": self.raw_total_time, "pts": 1.0})

        meta_path = Path(f'{self.cache_folder}/clip_meta.json').as_posix()
        with open(meta_path, 'w', encoding='utf-8') as f: json.dump(clip_meta_list, f, ensure_ascii=False, indent=2)
        return clip_meta_list

    def _cut_to_intermediate(self, ss, to, source, pts, out):
        """将视频片段裁切为标准化的中间格式"""
        config.logger.info(f"正在生成中间片段: {Path(out).name}, 原始范围: {ss}-{to}, PTS={pts or '1.0'}")
        cmd = ['-y', '-ss', tools.ms_to_time_string(ms=ss,sepflag='.'), '-to', tools.ms_to_time_string(ms=to,sepflag='.'), '-i', source,
               '-an', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '10',
               '-pix_fmt', 'yuv420p', '-r', str(self.source_video_fps)]
        if pts: cmd.extend(['-vf', f'setpts={pts}*PTS,fps={self.source_video_fps}'])
        cmd.append(out)
        tools.runffmpeg(cmd, force_cpu=True)
        if not Path(out).exists() or Path(out).stat().st_size == 0:
            config.logger.warning(f"中间片段 {Path(out).name} 生成失败，尝试无PTS参数重试。")
            if pts: cmd.pop(-2); cmd.pop(-2)
            tools.runffmpeg(cmd, force_cpu=True)

    def _concat_and_finalize(self, clip_meta_list):
        """无损拼接中间片段，然后进行一次性的最终编码"""
        valid_clips = [task['out'] for task in clip_meta_list if Path(task['out']).exists() and Path(task['out']).stat().st_size > 0]
        if not valid_clips:
            config.logger.error("没有任何有效的视频中间片段生成，视频处理失败！")
            self.novoice_mp4 = self.novoice_mp4_original
            return

        concat_txt_path = Path(f'{self.cache_folder}/concat_list.txt').as_posix()
        tools.create_concat_txt(valid_clips, concat_txt=concat_txt_path)

        intermediate_merged_path = Path(f'{self.cache_folder}/intermediate_merged.mp4').as_posix()
        concat_cmd = ['-y', '-f', 'concat', '-safe', '0', '-i', concat_txt_path, '-c', 'copy', intermediate_merged_path]
        tools.runffmpeg(concat_cmd, force_cpu=True)

        if not Path(intermediate_merged_path).exists():
            config.logger.error("拼接后的中间视频文件未能生成，视频处理失败！")
            return

        final_video_path = Path(f'{self.cache_folder}/merged_{self.noextname}.mp4').as_posix()
        video_codec = config.settings['video_codec']
        finalize_cmd = ['-y', '-i', intermediate_merged_path, '-c:v', f'libx{video_codec}', '-crf',
                        str(config.settings.get("crf", 23)), '-preset', config.settings.get('preset', 'fast'), '-an', final_video_path]
        tools.runffmpeg(finalize_cmd)

        if Path(final_video_path).exists():
            shutil.copy2(final_video_path, self.novoice_mp4)
            config.logger.info(f"最终无声视频已成功生成并复制到: {self.novoice_mp4}")
        else:
             config.logger.error("最终视频编码失败，保留原始无声视频。")
             self.novoice_mp4 = self.novoice_mp4_original

        if Path(intermediate_merged_path).exists(): os.remove(intermediate_merged_path)
        for clip_path in valid_clips:
            if Path(clip_path).exists(): os.remove(clip_path)
        if Path(concat_txt_path).exists(): os.remove(concat_txt_path)

    def _recalculate_timeline_and_merge_audio(self, clip_meta_list):
        """
        音频重建阶段
        这个方法的设计体现了智能切换。
        - **模式一/二的实现**：如果`clip_meta_list`存在（意味着视频被处理过），
          它就调用 `_recalculate_timeline_based_on_physical_reality`。
          这个函数严格按照视频片段的物理现实来拼接音频，是最终解决时间漂移的关键。
        - **模式三的实现**：如果视频未被处理，它会回退到
          `_recalculate_timeline_with_theoretical_offset`。
        :param clip_meta_list:
        :return:
        """
        process_text = "[5/5] 基于物理现实重建音频..." if config.defaulelang == 'zh' else "[5/5] Reconstructing audio based on physical reality..."
        tools.set_process(text=process_text, uuid=self.uuid)
        config.logger.info("================== [阶段 5/5] 基于物理现实重建音频 ==================")

        if not self.shoud_videorate or not clip_meta_list:
            config.logger.warning("未处理视频或无视频片段信息，回退到理论时间轴模型构建音频。")
            return self._recalculate_timeline_with_theoretical_offset()

        merged_audio = AudioSegment.empty()
        current_timeline_ms = 0

        for task in clip_meta_list:
            task_real_duration = int(task.get('real_duration_ms', 0))
            if task_real_duration <= 0:
                continue

            if task['type'] == 'gap':
                merged_audio += AudioSegment.silent(duration=task_real_duration)
                config.logger.info(f"音频流中添加物理间隙：时长 {task_real_duration}ms")
                current_timeline_ms += task_real_duration

            elif task['type'] == 'sub':
                it = self.queue_tts[task['index']]
                it['start_time'] = current_timeline_ms

                final_duration = task_real_duration

                if tools.vail_file(it['filename']):
                    try:
                        segment = AudioSegment.from_file(it['filename'])
                        if len(segment) < final_duration:
                            segment += AudioSegment.silent(duration=final_duration - len(segment))
                        elif len(segment) > final_duration:
                            segment = segment[:final_duration]
                    except Exception as e:
                        config.logger.error(f"字幕[{it['line']}] 加载音频失败: {e}，使用等长静音替代。")
                        segment = AudioSegment.silent(duration=final_duration)
                else:
                    config.logger.warning(f"字幕[{it['line']}] 配音文件不存在，使用等长静音替代。")
                    segment = AudioSegment.silent(duration=final_duration)

                merged_audio += segment
                current_timeline_ms += final_duration
                it['end_time'] = current_timeline_ms
                it['startraw'], it['endraw'] = tools.ms_to_time_string(ms=it['start_time']), tools.ms_to_time_string(ms=it['end_time'])
                config.logger.info(
                    f"字幕[{it['line']}] 音频重建：新区间 {it['start_time']}-{it['end_time']} (物理时长 {final_duration}ms)"
                )
        return merged_audio

    def _recalculate_timeline_with_theoretical_offset(self):
        """
        备用方法：当不处理视频时，使用基于理论 time_offset 的模型。
        """
        merged_audio = AudioSegment.empty()
        time_offset = 0

        for i, it in enumerate(self.queue_tts):
            it['start_time'] = it['start_time_source'] + time_offset
            current_audio_length = len(merged_audio)
            silence_needed = max(0, it['start_time'] - current_audio_length)

            if silence_needed > 0:
                merged_audio += AudioSegment.silent(duration=silence_needed)

            final_duration = it['final_video_duration_theoretical']
            if final_duration <= 0 : continue

            if tools.vail_file(it['filename']):
                try:
                    segment = AudioSegment.from_file(it['filename'])
                    if len(segment) < final_duration: segment += AudioSegment.silent(duration=final_duration - len(segment))
                    elif len(segment) > final_duration: segment = segment[:final_duration]
                except Exception as e:
                    segment = AudioSegment.silent(duration=final_duration)
            else:
                segment = AudioSegment.silent(duration=final_duration)

            merged_audio += segment
            it['end_time'] = it['start_time'] + final_duration
            it['startraw'], it['endraw'] = tools.ms_to_time_string(ms=it['start_time']), tools.ms_to_time_string(ms=it['end_time'])
            time_offset += (it['final_video_duration_theoretical'] - it['source_duration'])

        new_total_duration = self.raw_total_time + time_offset
        final_gap = new_total_duration - len(merged_audio)
        if final_gap > 0:
            merged_audio += AudioSegment.silent(duration=final_gap)

        return merged_audio

    def _finalize_files(self, merged_audio):
        """
        负责导出最终的音频，并执行最后的音视频对齐检查。
        无论是复杂的物理对齐模式，还是简单的纯净拼接模式，最终都会调用这个方法，
        确保了所有模式下的输出都有统一的质量保证（比如时长对齐）。
        :param merged_audio:
        :return:
        """
        final_step_text = "[最终步骤] 导出并对齐..." if config.defaulelang == 'zh' else '[Final Step] Exporting and finalizing...'
        tools.set_process(text=final_step_text, uuid=self.uuid)
        config.logger.info("================== [最终步骤] 导出、对齐并交付 ==================")
        try:
            self._export_audio(merged_audio, self.target_audio)

            if self.novoice_mp4 and tools.vail_file(self.novoice_mp4):
                config.logger.info("开始最终音视频时长对齐检查...")
                video_duration_ms = tools.get_video_duration(self.novoice_mp4)
                audio_duration_ms = self._get_audio_time_ms(self.target_audio)

                config.logger.info(f"最终检查: 视频物理总长 = {video_duration_ms}ms, 音频物理总长 = {audio_duration_ms}ms")
                duration_diff = video_duration_ms - audio_duration_ms
                config.logger.info(f"时长差异 (视频 - 音频) = {duration_diff}ms")

                TOLERANCE_MS = 150 # 最终对齐的容忍度

                if duration_diff > TOLERANCE_MS:
                    config.logger.warning(f"视频比音频长 {duration_diff}ms，将在音频末尾补齐等长静音。")
                    final_audio_segment = AudioSegment.from_file(self.target_audio)
                    final_audio_segment += AudioSegment.silent(duration=duration_diff)
                    self._export_audio(final_audio_segment, self.target_audio)
                    config.logger.info("音频补齐静音操作完成。")
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
                shutil.copy2(self.target_audio, self.target_audio_original)
                config.logger.info(f"最终音频文件已成功交付到: {self.target_audio_original}")
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
        try: return int(tools.get_audio_time(file_path) * 1000)
        except Exception:
            try: return len(AudioSegment.from_file(file_path))
            except Exception as e:
                config.logger.error(f"字幕[{line or 'N/A'}]：获取音频文件 {file_path} 时长失败: {e}")
                return 0

    def _export_audio(self, audio_segment, destination_path):
        wavfile = Path(f'{self.cache_folder}/temp_{time.time_ns()}.wav').as_posix()
        try:
            audio_segment.export(wavfile, format="wav")
            ext = Path(destination_path).suffix.lower()
            cmd = ["-y", "-i", wavfile]
            if ext == '.wav':
                cmd.extend(["-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2"])
            elif ext == '.m4a':
                cmd.extend(["-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2"])
            else:
                cmd.extend(["-b:a", "128k", "-ar", "44100", "-ac", "2"])
            cmd.append(destination_path)
            tools.runffmpeg(cmd, force_cpu=True)
        finally:
            if Path(wavfile).exists(): os.remove(wavfile)