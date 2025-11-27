import math
import json
import os
import shutil
import subprocess
import time, random
from pathlib import Path
import threading

from pydub import AudioSegment

from videotrans.configure import config
from videotrans.configure.config import tr, logs
from videotrans.util import tools
from concurrent.futures import ThreadPoolExecutor

import soundfile as sf
try:
    import pyrubberband as pyrb
except ImportError as e:
    print(f'Recommended installation uv add pyrubberband')


"""
通过音频加速和视频慢放来对齐翻译配音和原始视频时间轴。


*简单起见，视频慢速暂不考虑 插帧补帧光流法 等复杂方式,仅仅使用 setpts=X*PTS*
*音频加速使用 https://breakfastquay.com/rubberband/，ffmpeg atempo作为后备*


主要实现原理
# 功能概述, 使用python3开发视频翻译功能：
1. 即A语言发音的视频，分离出无声画面视频文件和音频文件，使用语音识别对音频文件识别出原始字幕后，将该字幕翻译翻译为B语言的字幕，再将该B语言字幕配音为B语言配音，然后将B语言字幕和B语言配音同A分离出的无声视频，进行音画同步对齐和合并为新视频。
2. 当前正在做的这部分就是“配音、字幕、视频对齐”，B语言字幕是逐条配音的，每条字幕的配音生成一个wav音频文件。
3. 因为语言不同，因此每条配音可能大于该条字幕的时间，例如该条字幕时长是3s，配音后的mp3时长如果小于等于3s，则不影响，但如果配音时长大于3s，则有问题，需要通过将音频片段自动加速到3s实现同步。也可以通过将该字幕的原始字幕所对应原始视频该片段截取下来，慢速播放延长该视频时长直到匹配配音时长，实现对齐。当然也可以同时 音频自动加速 和 视频慢速，从而避免音频加速太多或视频慢速太多。

# 具体音画同步原理说明


## 音频和视频同时启用时的策略
1. 如果配音时长 小于 当前片段的原始字幕时长，则无需音频加速和视频慢速
2. 如果配音时长 大于 当前片段的原始字幕时长，则判断音频时长缩短到和原始字幕时长一致时，需要的加速倍数是多少，
- 如果该倍数 小于等于 1.3，则照此对配音加速即可，无需视频慢速处理
- 如果该倍数 大于 1.3，则将 原始字幕时长 加上 和  下条字幕开始时间之间的静默时间,记为  total_a
   * 如果该时长 total_a 大于 配音时长，则配音无需加速，自然播放完毕即可，视频也无需慢速，注意因此导致的时间轴变化和对视频裁切的影响
   * 如果该时长 total_a 小于配音时长，则计算将配音时长缩短到 total_a 时，需要的加速倍数
        - 如果该倍数 小于等于 1.3，则照此加速音频即可，无需视频慢速，注意因此导致的时间轴变化和对视频裁切的影响
        - 如果该倍数 大于1.3，则按之前逻辑，音频加速和视频慢速各自负担一半

## 仅仅使用音频加速时

1. 如果配音时长 小于 当前片段的原始字幕时长，则无需音频加速
2. 如果配音时长 大于 当前片段的原始字幕时长，则计算将音频缩短到和原始字幕时长一致时，所需的加速倍数是多少，
- 如果该倍数 小于等于 1.3，则照此对配音加速即可
- 如果该倍数 大于 1.3，则将原始字幕时长加上 和  下条字幕开始时间之间的静默时间,记为  total_b
   * 如果该时长 total_b 大于配音时长，则将配音无需加速，自然播放完毕即可，total_b 在容下配音后如果还有剩余空间则使用静音填充。
   * 如果该时长 total_b 仍小于配音时长，强制将配音时长缩短到total_a，倍数最大不超过max_audio_speed_rate
3. 注意开头和结尾以及字幕之间的静默区间，尤其是利用后可能还剩余的静默空间，最终合成后的音频长度，在存在视频时(self.novoice_mp4) 长度应等于视频长度，在不存在时，长度应不小于 self.raw_total_time。

## 仅仅视频慢速时
1. 如果配音时长 小于 当前片段的原始字幕时长，则无需视频慢速，直接从本条字幕开始时间裁切到下条字幕开始时间，如果这是第一条字幕，则从0时间开始裁切
2. 如果配音时长 大于 当前片段的原始字幕时长，则判断原始字幕时长加上 和  下条字幕开始时间之间的静默时间,记为  total_c
   * 如果该时长 total_c 大于 配音时长，则无需视频慢速，自然播放完毕即可，此时应裁切 total_c 时长的视频片段，即裁切到到下条字幕开始时间，而且无需慢速处理，同样如果这是第一条字幕，则从0时间开始裁切
   * 如果该时长 total_c 仍小于配音时长，强制将视频片段(时长为total_a) 慢速延长到和配音等长，此处注意下，PTS倍数最大不超过 max_video_speed_rate。
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


class SpeedRate:
    MIN_CLIP_DURATION_MS = 40
    # [新增] 统一所有中间音频文件的参数，防止拼接错误
    AUDIO_SAMPLE_RATE = 44100
    AUDIO_CHANNELS = 2
    BESTER_AUDIO_RATE = 1.3

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
        self.align_sub_audio=align_sub_audio
        self.raw_total_time = raw_total_time
        self.remove_silent_mid=remove_silent_mid
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
        # 音频片段缓存目录
        self.audio_clips_folder = Path(f'{self.cache_folder}/audio_clips').as_posix()
        Path(self.audio_clips_folder).mkdir(parents=True, exist_ok=True)

        self.stop_show_process=False

        self.target_audio = target_audio
        config.settings = config.parse_init()
        # 音频加速允许的最大加速倍数
        self.max_audio_speed_rate = float(config.settings.get('max_audio_speed_rate', 100))
        # 视频慢速允许的最大PTS
        self.max_video_pts_rate = float(config.settings.get('max_video_pts_rate', 10))
        # 默认帧率
        self.source_video_fps = 30
        # 默认一帧时长ms
        self.fps_ms = 1000 // 30
        
        self.crf="20"
        self.preset="fast"
        self.audio_speed_filter='atempo'
        try:
            if Path(config.ROOT_DIR+"/crf.txt").exists():
                self.crf=str(int(Path(config.ROOT_DIR+"/crf.txt").read_text()))
            if Path(config.ROOT_DIR+"/preset.txt").exists():
                preset=str(Path(config.ROOT_DIR+"/preset.txt").read_text().strip())
                if preset in ['ultrafast','superfast','veryfast','faster','fast','medium','slow','slower','veryslow']:
                    self.preset=preset
        except Exception:
            pass
        
        # 检测并设置可用的音频变速滤镜
        self.audio_speed_rubberband = shutil.which("rubberband")

        logs(f'允许的最大音频加速倍数={self.max_audio_speed_rate},允许的最大视频慢放倍数={self.max_video_pts_rate}')
        logs(
            f"SpeedRate 初始化。音频加速: {self.shoud_audiorate}, 视频慢速: {self.shoud_videorate}")
        logs(f"所有中间音频将统一为: {self.AUDIO_SAMPLE_RATE}Hz, {self.AUDIO_CHANNELS} 声道。")

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
                logs("检测到FFmpeg支持 'rubberband' 滤镜，将优先使用。")
                return 'rubberband'
            elif 'atempo' in filters_output:
                logs("未检测到 'rubberband' 滤镜，将使用 'atempo' 滤镜。")
                return 'atempo'
            else:
                logs("FFmpeg中未检测到 'rubberband' 或 'atempo' 滤镜，音频加速功能可能受限。",level='warn')
                return None
        except Exception as e:
            logs(f"检查FFmpeg滤镜时出错: {e}。将无法使用高质量音频变速。",level='warn')
            return None

    def run(self):
        # 如果既不加速音频也不慢放视频，仅连接音频
        if not self.shoud_audiorate and not self.shoud_videorate:
            logs("检测到未启用音视频变速，进入纯净拼接模式。")
            self._run_no_rate_change_mode()
            return self.queue_tts
        # 否则，执行加减速同步流程
        # 组装数据，记录字幕原始时间及配音原始时长等
        self._prepare_data()
        # 预先计算出 音频和视频应该变化到的新时长
        self._calculate_adjustments()
        # 先执行音频加速
        if self.shoud_audiorate:
            if self.audio_speed_rubberband:
                self._execute_audio_speedup_rubberband()
            else:
                print(f'For Windows systems, please download the file, extract it, and place it in the ffmpeg folder in the current directory. Use a better audio acceleration algorithm\nhttps://breakfastquay.com/files/releases/rubberband-4.0.0-gpl-executable-windows.zip')
                print(f'MacOS: `brew install rubberband`  and  `uv add pyrubberband` Use a better audio acceleration algorithm')
                print(f'Ubuntu: `sudo apt install rubberband-cli libsndfile1-dev` and `uv add pyrubberband`  Use a better audio acceleration algorithm')
                self.audio_speed_filter=self._check_ffmpeg_filters()
                self._execute_audio_speedup()
        # 再执行视频慢速
        clip_meta_list_with_real_durations = self._execute_video_processing()
        # 重新校正时间轴，音频加速和视频慢速的新值和理论值存在误差
        audio_concat_list = self._recalculate_timeline_and_merge_audio(clip_meta_list_with_real_durations)
        # 拼接音频和视频
        if audio_concat_list:
            self._finalize_files(audio_concat_list)
        # 返回更新后的队列，有些视频片段丢失，对应的配音和字幕也应当丢弃
        for i, it in enumerate(self.queue_tts):
            if it.get('shoud_del'):
                logs(f'[{i=}]字幕视频创建失败，将字幕清空，因对应的配音也删掉了，需保证一致,{it=}')
                self.queue_tts[i]['text']=''

        return self.queue_tts

    def _run_no_rate_change_mode(self):
        """
        模式 不对音频视频做任何加减速处理。
        此模式也使用基于FFmpeg的流式拼接，以处理大文件。
        1. 准备数据。
        2. 循环中，生成每个音频片段（配音+静音）的临时WAV文件。
        3. 生成一个文件列表供FFmpeg concat使用。
        4. 调用通用的 `_finalize_files` 方法来处理拼接和与字幕的最终对齐。
        """
        process_text = tr("Merging audio...")
        tools.set_process(text=process_text, uuid=self.uuid)
        logs("================== [纯净模式] 开始处理 ==================")

        self._prepare_data()

        audio_concat_list = []
        total_audio_duration = 0

        for i, it in enumerate(self.queue_tts):
            # 1. 填充字幕前的静音
            silence_duration = it['start_time_source'] - (0 if i == 0 else self.queue_tts[i - 1]['end_time_source'])
            if not self.remove_silent_mid and silence_duration > 0:
                audio_concat_list.append(self._create_silen_file(i, silence_duration))
                logs(f"字幕[{it['line']}]前，生成静音片段 {silence_duration}ms")
                total_audio_duration += silence_duration
            if self.align_sub_audio:
                it['start_time'] = total_audio_duration

            # 加载并处理配音片段
            segment = None
            source_duration = it['end_time_source'] - it['start_time_source']
            dubb_duration = source_duration
            if tools.vail_file(it['filename']):
                try:
                    # 标准化加载的音频
                    segment = AudioSegment.from_file(it['filename'])
                    dubb_duration = len(segment)
                except Exception as e:
                    logs(f"字幕[{it['line']}] 加载音频文件 {it['filename']} 失败: {e}，填充静音。",level='warn')
            else:
                logs(f"字幕[{it['line']}] 配音文件不存在: {it['filename']}，将填充静音。",level='warn')
            # 真实配音时长
            it['dubb_time'] = dubb_duration
            total_audio_duration += dubb_duration
            
            if self.align_sub_audio:
                it['end_time'] = it['start_time'] + dubb_duration
                it['startraw'], it['endraw'] = tools.ms_to_time_string(ms=it['start_time']), tools.ms_to_time_string(
                ms=it['end_time'])
                
            if not segment:
                # 配音失败，使用原始静音填充
                audio_concat_list.append(self._create_silen_file(i, dubb_duration))
                continue

            # 导出当前配音片段
            dub_clip_path = Path(self.audio_clips_folder, f"{i:05d}_dub.wav").as_posix()
            segment.export(dub_clip_path, format="wav")
            audio_concat_list.append(dub_clip_path)

            # 如果配音时长小于,需在后边填充静音
            if not self.remove_silent_mid and dubb_duration < source_duration:
                audio_concat_list.append(self._create_silen_file(i, source_duration - dubb_duration))
                total_audio_duration += source_duration - dubb_duration

            logs(
                f"字幕[{it['line']}] 已生成配音片段，配音时长: {dubb_duration}ms, 原时长 {source_duration}\n")

        # 补充判断是否需要补充静音
        if not self.remove_silent_mid and self.raw_total_time > 0 and total_audio_duration < self.raw_total_time:
            audio_concat_list.append(
                self._create_silen_file(len(self.queue_tts), self.raw_total_time - total_audio_duration))

        self._finalize_files(audio_concat_list)
        logs("================== [纯净模式] 处理完成 ==================")

    def _prepare_data(self):
        """
        此阶段为所有后续计算提供基础数据。关键是计算出 `source_duration` (原始时长)
        和 `silent_gap` (与下一条字幕的静默间隙)，这是所有策略判断的依据。
        同时，`final_video_duration_real` 字段也被初始化。
        :return:
        """
        tools.set_process(text=tr("[1/5] Preparing data..."), uuid=self.uuid)
        logs("================== [阶段 1/5] 准备数据 ==================")

        if self.shoud_videorate and self.novoice_mp4_original and tools.vail_file(self.novoice_mp4_original):
            try:
                self.source_video_fps = tools.get_video_info(self.novoice_mp4_original, video_fps=True) or 30
                self.fps_ms = 1000 // self.source_video_fps
            except Exception as e:
                logs(f"无法探测源视频帧率，将使用默认值30。错误: {e}",level='warn')
                self.source_video_fps = 30
        logs(f"源视频帧率被设定为: {self.source_video_fps}")

        # 如果需要视频慢速，额外预先多遍历一次，本次是为了将字幕前小于40ms的空隙去掉，合并进紧邻的后个字幕里，防止过短空隙导致视频裁切出错
        # 使用冗余的多次遍历，每次仅处理一个任务，防止逻辑混乱
        if self.shoud_videorate:
            queue_tts_len=len(self.queue_tts)
            for i,it in enumerate(self.queue_tts):
                if i==0 and 0<it['start_time'] <self.MIN_CLIP_DURATION_MS:
                    it['start_time']=0
                elif i>0 and i<queue_tts_len-1:
                    #不是最后一个,判断和前面的空隙是否小于 self.MIN_CLIP_DURATION_MS
                    diff = it['start_time']-self.queue_tts[i-1]['end_time']
                    if 0<diff < self.MIN_CLIP_DURATION_MS:
                        it['start_time']=self.queue_tts[i-1]['end_time']
                elif i==queue_tts_len-1:
                    diff=self.raw_total_time-it['end_time']
                    if 0<diff<self.MIN_CLIP_DURATION_MS:
                        it['end_time']=self.raw_total_time
        
        # 在启用了视频慢速或音频时，再遍历一次，本次仅仅处理字幕文本为空的情况，将它合并进前面的字幕，
        if self.shoud_videorate or self.shoud_audiorate: 
            for i,it in enumerate(self.queue_tts): 
                if it['text'].strip():
                    continue
                # 文本为空，则配音文件无论是否存在均无意义
                # 但该条字幕不删，以便和原始转录的字幕条数一一对应，防止双字幕时错乱
                it['filename']=None
                if i>0:
                    # 合并进前边的字幕
                    self.queue_tts[i-1]['end_time']=it['end_time']
                    it['start_time']=it['end_time']
        
                    

        for i, it in enumerate(self.queue_tts):
            # 原始字幕时长
            it['source_duration'] = it['end_time'] - it['start_time']
            # 原始字幕的起始时间
            it['start_time_source'] = it['start_time']
            it['end_time_source'] = it['end_time']

            # 如果时长为0，要么因为当前字幕为空已处理，要么出错了，则删掉配音文件，后续音频和视频处理均跳过
            if it['source_duration'] <= 0:
                it['dubb_time'] = 0
                it['filename'] = None
                # 原始视频片段时长
                it['final_video_duration_theoretical'] = 0
                # 用于存储探测到的物理时长
                it['final_video_duration_real'] = 0
                it['final_audio_duration_theoretical'] = 0
                continue
            tools.set_process(text=f"{tr('[1/5] Preparing data...')} {i}/{self.len_queue}", uuid=self.uuid)
            it['dubb_time'] = self._get_audio_time_ms(it['filename'])
            # 如果配音文件不存在或尺寸为0，使用静音替代
            if it['dubb_time'] == 0:
                it['dubb_time'] = it['source_duration']
                it['filename'] = None
                it['final_video_duration_theoretical'] = it['source_duration']
                # 用于存储探测到的物理时长
                it['final_video_duration_real'] = it['source_duration']
                it['final_audio_duration_theoretical'] = it['source_duration']
                continue
            # 这几个值非确定，等待 _calculate_adjustments 再设置
            it['final_audio_duration_theoretical'] = it['dubb_time']
            it['final_video_duration_theoretical'] = it['source_duration']
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
        tools.set_process(text=tr("[2/5] Calculating adjustments..."), uuid=self.uuid)
        logs("================== [阶段 2/5] 计算调整方案 ==================")

        for i, it in enumerate(self.queue_tts):
            dubb_duration = it['dubb_time']
            source_duration = it['source_duration']
            logs(f"\n--- 开始分析字幕[{it['line']}]---")
            tools.set_process(text=f'{tr("[2/5] Calculating adjustments...")} {i}/{self.len_queue}', uuid=self.uuid)
            if source_duration <= 0 or dubb_duration <= 0:
                it['final_video_duration_theoretical'] = source_duration
                it['final_audio_duration_theoretical'] = source_duration
                logs(f"字幕[{it['line']}], 原始时长或配音时长为0，跳过调整计算。",level='warn')
                continue

            silent_gap = it['silent_gap']
            block_source_duration = source_duration + silent_gap

            config.logger.debug(
                f"字幕[{it['line']}], 原始数据：配音时长={dubb_duration}ms, 字幕时长={source_duration}ms, 静默间隙={silent_gap}ms, 可用总长={block_source_duration}ms")

            # 如果音频可以被原始时段容纳，则无需处理
            if dubb_duration <= source_duration:
                logs(f"字幕[{it['line']}], 配音({dubb_duration}ms) <= 字幕({source_duration}ms)，无需调整。")
                it['final_video_duration_theoretical'] = source_duration
                it['final_audio_duration_theoretical'] = dubb_duration  # 音频时长就是其本身
                continue

            # 需要达到的音频目标时长：初始化为配音时长,即不变速
            target_duration = dubb_duration
            # 需要达到的视频目标时长：初始化为原字幕对应时长，即不变速
            video_target_duration = source_duration

            if self.shoud_audiorate and self.shoud_videorate:
                config.logger.debug(f"字幕[{it['line']}], 进入[音频加速 + 视频慢速]模式。")
                # 配音完全缩短的 source_duration 的加速倍数
                speed_to_fit_source = dubb_duration / source_duration

                if block_source_duration >= dubb_duration:
                    logs(f"字幕[{it['line']}], 利用静默间隙({silent_gap}ms)即可容纳配音，音视频均不变速。目标时长将为配音时长。")
                    target_duration = dubb_duration
                elif speed_to_fit_source <= self.BESTER_AUDIO_RATE:
                    logs(
                        f"字幕[{it['line']}], 仅需音频加速（音倍率{speed_to_fit_source:.2f} <= {self.BESTER_AUDIO_RATE}），视频不慢放。目标时长将为原字幕时长。")
                    target_duration = source_duration
                else:
                    logs(f"字幕[{it['line']}], 此时音频和视频共同承担调整，各自负责一半。")
                    over_time = dubb_duration - source_duration
                    video_extension = over_time / 2
                    target_duration = int(source_duration + video_extension)
                    video_target_duration=target_duration
                    # 为保证对齐，忽略最大最小倍数限制，强制两者时长一致                    
            elif self.shoud_audiorate:
                config.logger.debug(f"字幕[{it['line']}], 进入[仅音频加速]模式。")
                speed_to_fit_source = dubb_duration / source_duration
                if block_source_duration >= dubb_duration:
                    logs(f"字幕[{it['line']}], [决策] 利用静默间隙({silent_gap}ms)即可容纳，无需加速。目标时长将为配音时长。")
                    target_duration = dubb_duration
                elif speed_to_fit_source<= self.BESTER_AUDIO_RATE:
                    logs(f"字幕[{it['line']}], 加速倍率({speed_to_fit_source:.2f})< {self.BESTER_AUDIO_RATE}，压缩至原字幕时长。")
                    target_duration = source_duration
                else:
                    speed_to_fit_source=min(speed_to_fit_source,self.max_audio_speed_rate)
                    target_duration=int(dubb_duration/speed_to_fit_source)
                    
            elif self.shoud_videorate:
                # 仅仅视频慢速，此时视频应该慢放到等于配音时长
                config.logger.debug(f"字幕[{it['line']}], 进入[仅视频慢速/音频不变]模式。")
                speed_to_fit_source = dubb_duration / source_duration
                if block_source_duration >= dubb_duration:
                    logs(f"字幕[{it['line']}], [决策] 利用静默间隙({silent_gap}ms)即可容纳，无需慢放。")
                    video_target_duration = source_duration
                elif speed_to_fit_source<=self.max_video_pts_rate:
                    logs(f"字幕[{it['line']}], [决策] 空间不足，视频将慢放到配音时长。")
                    video_target_duration = dubb_duration
                else:
                    speed_to_fit_source=min(speed_to_fit_source,self.max_video_pts_rate)
                    video_target_duration=int(dubb_duration/speed_to_fit_source)
            
            it['final_audio_duration_theoretical']=target_duration
            it['final_video_duration_theoretical']=video_target_duration
            

            logs(
                f"字幕[{it['line']}], [最终方案] 理论目标音频时长: {target_duration}ms,理论视频时长:{video_target_duration}ms")

    def _execute_audio_speedup(self):
        """
        使用FFmpeg的`rubberband`或`atempo`滤镜进行高质量音频变速。
        """
        tools.set_process(text=tr("[3/5] Processing audio..."),
                          uuid=self.uuid)
        logs("================== [阶段 3/5] 执行音频加速 ==================")


        if not self.shoud_audiorate:
            logs("未启用音频加速",level='warn')
            return

        all_cmds = []

        for i, it in enumerate(self.queue_tts):
            tools.set_process(text=f'{tr("[3/5] Processing audio...")} {i}/{self.len_queue}', uuid=self.uuid)
            # 需要加速后的新配音时长
            target_duration_ms = int(it['final_audio_duration_theoretical'])
            if target_duration_ms <= 0:  # 增加容差
                all_cmds.append("1")
                continue
            # 原始配音时长
            current_duration_ms = it['dubb_time']
            # 只有在需要压缩时才处理
            if current_duration_ms <= target_duration_ms or not tools.vail_file(it['filename']):
                all_cmds.append("1")
                continue

            # 在理论计算时已限制最大加速倍数，不再处理超过的情况
            speedup_ratio = current_duration_ms / target_duration_ms
            if float(speedup_ratio) <= 1.0:
                all_cmds.append("1")
                continue
            
            logs(
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
                logs(f"字幕[{it['line']}] 无法为倍率 {speedup_ratio:.2f} 构建有效的filter字符串，跳过变速。",level='warn')
                all_cmds.append("1")
                continue

            target_duration_sec = target_duration_ms / 1000.0
            cmd.extend(['-filter:a', filter_str, '-t', f'{target_duration_sec:.4f}'])

            cmd.extend(['-ar', str(self.AUDIO_SAMPLE_RATE), '-ac', str(self.AUDIO_CHANNELS), '-c:a', 'pcm_s16le',
                        temp_output_file])
            all_cmds.append(cmd)


        total_tasks = len(all_cmds)
        if total_tasks == 0:
            return

        def _speedup_set_dubbtime(i, cmd):
            it = self.queue_tts[i]
            try:
                tools.runffmpeg(cmd, force_cpu=True)
                # 加速后实际的音频新时长，可能和理论不一致
                up_after_time = self._get_audio_time_ms(cmd[-1])
                if up_after_time > 0 and up_after_time < it['dubb_time'] and tools.vail_file(cmd[-1]):
                    self.queue_tts[i]['dubb_time'] = up_after_time
                    try:
                        shutil.copy2(cmd[-1], it['filename'])
                    except shutil.SameFileError:
                        pass
                else:
                    self.queue_tts[i]['dubb_time']=self.queue_tts[i]['source_duration']
                    self.queue_tts[i]['filename']=None
                    logs(f"变速后复制 {cmd[-1]} 到 {it['filename']} 失败", level="except")
            except Exception as e:
                self.queue_tts[i]['dubb_time']=self.queue_tts[i]['source_duration']
                self.queue_tts[i]['filename']=None
                logs(f"字幕[{it['line']}] 音频变速失败 {e}",level='warn')

        all_task = []
        with ThreadPoolExecutor(max_workers=min(12, len(all_cmds), os.cpu_count())) as pool:
            for i, cmd in enumerate(all_cmds):
                if isinstance(cmd, list):
                    all_task.append(pool.submit(_speedup_set_dubbtime, i, cmd))

            completed_tasks = 0
            for task in all_task:
                try:
                    task.result()  # 等待任务完成
                    completed_tasks += 1
                    tools.set_process(
                        text=f"audio speedup [{completed_tasks}/{total_tasks}] ...",
                        uuid=self.uuid)
                except Exception as e:
                    logs(f"Task {completed_tasks + 1} failed with error: {e}", level="except")

    def _execute_video_processing(self):
        """
        视频处理阶段
        确保在处理完成后，返回包含了真实物理时长的`clip_meta_list`。
        """
        if not self.shoud_videorate or not self.novoice_mp4_original or not tools.vail_file(self.novoice_mp4_original):
            logs("视频处理被跳过，因为未启用或无声视频文件不存在。",level='warn')
            for it in self.queue_tts:
                it['final_video_duration_real'] = it['final_video_duration_theoretical']
            return None
        tools.set_process(
            text=tr("[4/5] Processing video & probing real durations..."),
            uuid=self.uuid)
        logs("================== [阶段 4/5] 执行视频处理并探测真实时长 ==================")

        clip_meta_list = self._create_clip_meta()

        all_task = []
        total_tasks = len(clip_meta_list)

        def _cut_video_get_duration(i, task):
            duration = task['to'] - task['ss']
            subject = f"字幕[{task.get('line', 'gap')}],[index={i}],[{os.path.basename(task['out'])}]"
            msg = f"\n{subject} ,start_time_source={task['ss']},正在生成中间片段, 原始范围: {task['ss']}-{task['to']}={duration}ms,"
            if duration <= 0:
                clip_meta_list[i]['final_video_duration_real'] = 0
                logs(f"{msg},字幕时长为0，跳过裁切视频片段\n")
                return
            pts_param = float(task['pts']) if float(task.get('pts', 0)) > 1.0 else None
            # 在理论计算阶段已限制最大倍数，不再处理
            if pts_param:
                logs(f"{msg} [变速]: PTS={pts_param},理论上生成后视频片段时长={float(pts_param) * (duration)}ms")
            else:
                logs(f"{msg} [不变速]: PTS=1")

            self._cut_to_intermediate(ss=task['ss'], to=task['to'], source=self.novoice_mp4_original, pts=pts_param,
                                      out=task['out'],subject=subject)
            # 获取生成后的真实视频片段时长，为0则是生成片段出错，需对应跳过该字幕和配音
            real_duration_ms = 0
            if Path(task['out']).exists() and Path(task['out']).stat().st_size > 1024:
                real_duration_ms = self._get_video_duration_safe(task['out'])
                if real_duration_ms == -1:
                    # 生成真的失败了
                    Path(task['out']).unlink(missing_ok=True)
                elif real_duration_ms == 0:
                    # 可能存在一帧
                    real_duration_ms = self.fps_ms
            if real_duration_ms==0:
                logs(f"{subject} [Error]\n")
                
            logs(f"{subject} 实际生成后物理时长:{real_duration_ms}ms\n")
            clip_meta_list[i]['real_duration_ms'] = real_duration_ms
            if task['type'] == 'sub':
                clip_meta_list[i]['final_video_duration_real'] = real_duration_ms

        with ThreadPoolExecutor(max_workers=min(12, len(clip_meta_list), os.cpu_count())) as pool:
            for i, task in enumerate(clip_meta_list):
                all_task.append(pool.submit(_cut_video_get_duration, i, task))
                # 监控进度
            completed_tasks = 0
            for task in all_task:
                try:
                    task.result()  # 等待任务完成
                    completed_tasks += 1
                    tools.set_process(
                        text=tr("[{}/{}] Processing video & probing real durations...", completed_tasks, total_tasks),
                        uuid=self.uuid)
                except Exception as e:
                    logs(f"Task {completed_tasks + 1} failed with error: {e}", level="except")

        self._concat_and_finalize(clip_meta_list)
        return clip_meta_list

    def _create_clip_meta(self):
        """
        创建视频裁切任务列表
        """
        clip_meta_list = []
        last_end_time = 0

        # 处理第一条字幕前的间隙
        first_sub_start = self.queue_tts[0]['start_time_source']
        if first_sub_start > 0:
            clip_path = Path(f'{self.cache_folder}/00000_first_gap.mp4').as_posix()
            clip_meta_list.append({"type": "gap", "out": clip_path, "ss": 0, "to": first_sub_start, "pts": 1.0})
            last_end_time = first_sub_start
        

        for i, it in enumerate(self.queue_tts):
            tools.set_process(text=f'create clip task {i}/{self.len_queue}', uuid=self.uuid)
            # 处理字幕间的间隙
            gap_start = last_end_time
            gap_end = it['start_time_source']
            start_time = it['start_time_source']
            if gap_end > gap_start:
                clip_path = Path(f'{self.cache_folder}/{i:05d}_gap.mp4').as_posix()
                clip_meta_list.append({"type": "gap", "out": clip_path, "ss": gap_start, "to": gap_end, "pts": 1.0})

            # 处理字幕本身
            if it['source_duration'] > 0:
                clip_path = Path(f"{self.cache_folder}/{i:05d}_sub.mp4").as_posix()
                # 视频慢放的目标是原始的 source_duration, 所以pts基于此计算
                pts_val = it['final_video_duration_theoretical'] / it['source_duration'] if it[
                                                                                                'source_duration'] > 0 else 1.0
                clip_meta_list.append({"type": "sub", "index": i, "out": clip_path, "ss": start_time,
                                       "to": it['end_time_source'], "pts": pts_val, "line": it['line']})

            last_end_time = it['end_time_source']

        # 处理最后一条字幕后的间隙
        if self.raw_total_time > last_end_time:
            clip_path = Path(f'{self.cache_folder}/zzzz_final_gap.mp4').as_posix()
            clip_meta_list.append(
                {"type": "gap", "out": clip_path, "ss": last_end_time, "to": self.raw_total_time, "pts": 1.0})

        meta_path = Path(f'{self.cache_folder}/clip_meta.json').as_posix()
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(clip_meta_list, f, ensure_ascii=False, indent=2)
        return clip_meta_list

    def _cut_to_intermediate(self, ss, to, source, pts, out,subject=""):
        """视频变速"""
        cmd = ['-y',  '-ss', tools.ms_to_time_string(ms=ss, sepflag='.'), '-t',
               f'{(to - ss) / 1000.0}','-i', source, 
               '-an', '-c:v', 'libx264',"-x264-params", "keyint=1:min-keyint=1:scenecut=0", '-preset', self.preset, '-crf', self.crf,
               '-pix_fmt', 'yuv420p']
        if pts:
            cmd.extend(['-vf', f'setpts={pts}*PTS', '-vsync', 'vfr'])
        else:
            cmd.extend(['-vf', f'setpts=PTS', '-vsync', 'vfr'])
        cmd.append(out)
        try:
            tools.runffmpeg(cmd, force_cpu=True)
            if (not Path(out).exists() or Path(out).stat().st_size < 1024) and pts:
                logs(f"[{subject}] 中间片段 {Path(out).name} 生成失败，尝试无PTS参数重试。",level='warn')
                tools.runffmpeg(['-y', '-ss', tools.ms_to_time_string(ms=ss, sepflag='.'), '-t',
                                 f'{(to - ss) / 1000.0}', '-i', source,
                                 '-an', '-c:v', 'libx264', '-preset', self.preset, '-crf', self.crf,
                                 '-pix_fmt', 'yuv420p', '-vf', f'setpts=PTS', '-vsync', 'vfr', out],
                                force_cpu=True)
            # 仍然有错就放弃了
            if Path(out).exists() and Path(out).stat().st_size < 1024:
                logs(f"[{subject}] 中间片段 {Path(out).name} 生成成功，但尺寸为 < 1024B，无效需删除。{cmd=}",level='warn')
                Path(out).unlink(missing_ok=True)
        except Exception:
            try:
                Path(out).unlink(missing_ok=True)
            except OSError:
                pass

    
    # ffmpeg进度日志
    def _hebing_pro(self, protxt,text="") -> None:
        precent=0
        while 1:
            if config.exit_soft or self.stop_show_process:return
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
            tools.set_process(text=f'{text} {end_time}',uuid=self.uuid)
            time.sleep(0.5)

    
    def _concat_and_finalize(self, clip_meta_list):
        """无损拼接中间片段，然后进行一次性的最终编码"""
        valid_clips = [task['out'] for task in clip_meta_list if
                       Path(task['out']).exists() and Path(task['out']).stat().st_size > 1024]
        if not valid_clips:
            logs("没有任何有效的视频中间片段生成，视频处理失败！",level='warn')
            self.novoice_mp4 = self.novoice_mp4_original
            return

        concat_txt_path = Path(f'{self.cache_folder}/concat_list.txt').as_posix()
        try:
            tools.create_concat_txt(valid_clips, concat_txt=concat_txt_path)
        except ValueError as e:
            logs(f"创建视频拼接列表失败: {e}",level='warn')
            return


        protxt=config.TEMP_DIR + f"/rate_video_{time.time()}.txt"
        intermediate_merged_path = Path(f'{self.cache_folder}/intermediate_merged.mp4').as_posix()
        concat_cmd = ['-y',"-progress",protxt, '-fflags', '+genpts', '-f', 'concat', '-safe', '0', '-i', concat_txt_path, '-c:v', 'copy', intermediate_merged_path]
        tools.set_process(text=f"Concat {len(valid_clips)} video file...",uuid=self.uuid)
        
        real_duration_ms=sum([task['real_duration_ms'] for task in clip_meta_list])
        self.stop_show_process=False
        threading.Thread(target=self._hebing_pro,args=(protxt,'Concat video file')).start()
        
        tools.runffmpeg(concat_cmd, force_cpu=True)
        self.stop_show_process=True

        if not Path(intermediate_merged_path).exists():
            logs("拼接后的中间视频文件未能生成，视频处理失败！",level='warn')
            return
        try:
            # 重命名原始novoice.mp4，以便失败时回退原始视频
            Path(self.novoice_mp4).rename(self.novoice_mp4+"-raw.mp4")
            Path(intermediate_merged_path).rename(self.novoice_mp4)
        except Exception:
            shutil.copy2(self.novoice_mp4+"-raw.mp4",self.novoice_mp4)

        # 删除临时片段
        for i,clip_path in enumerate(valid_clips):
            try:
                tools.set_process(text=f"Del temp file {i}...",uuid=self.uuid)
                Path(clip_path).unlink(missing_ok=True)
            except OSError:
                pass
        try:
            Path(concat_txt_path).unlink(missing_ok=True)
        except OSError:
            pass

    def _recalculate_timeline_and_merge_audio(self, clip_meta_list):
        """
        音频重建阶段。
        根据 `shoud_videorate` 的值，正确分发到物理时间轴或理论时间轴模型。
        """
        process_text = tr("[5/5] Generating audio clips...")
        tools.set_process(text=process_text, uuid=self.uuid)
        logs("================== [阶段 5/5] 生成音频片段以供拼接 ==================")

        if self.shoud_videorate and clip_meta_list:
            logs("进入物理时间轴模型（基于视频片段真实时长）构建音频。")
            return self._recalculate_timeline_based_on_physical_video(clip_meta_list)
        else:
            logs("进入理论时间轴模型（基于计算偏移）构建音频。")
            return self._recalculate_timeline_with_theoretical_offset()

    def _recalculate_timeline_based_on_physical_video(self, clip_meta_list=None):
        audio_concat_list = []

        # 需要到 clip_meta_list 种获取对应的本条字幕新视频片段的开始和结束时间 以及真实时间
        def _get_s2e_by_line(line):
            start_time = 0
            for it in clip_meta_list:
                it_line = it.get('line')
                if not it_line or it_line < line:
                    gap_ms = it.get('real_duration_ms', 0)
                    start_time += gap_ms if gap_ms > 0 else self.fps_ms
                elif it_line == line:
                    sub_ms = it.get('real_duration_ms', 0)
                    return start_time, sub_ms if sub_ms > 0 else self.fps_ms
            return 0, 0

        audio_all_duration = 0


        for i, it in enumerate(self.queue_tts):
            tools.set_process(text=f"recalculate timeline  {i}/{self.len_queue}", uuid=self.uuid)
            # 从 clip_meta_list 中获取当前对应片段的视频开始时间和时长
            start_time, video_duration = _get_s2e_by_line(it['line'])
            if video_duration <= 0 or it['start_time'] == it['end_time']:
                continue
            # 如果音频时长小于视频开始时长 start_time,则补充静音
            logs(f'\n【字幕 {it["line"]}】,获取到视频 {start_time=},{video_duration=},当前 {audio_all_duration=}')
            if audio_all_duration < start_time:
                audio_concat_list.append(self._create_silen_file(i, start_time - audio_all_duration))
                audio_all_duration = start_time
                it['start_time'] = start_time
            else:
                # 配音已长于视频开始时间，不处理
                it['start_time'] = audio_all_duration

            clip_path = Path(self.audio_clips_folder, f"t_clip_{i:05d}.wav").as_posix()
            # 判断该配音文件是否出错
            occur_error = False
            # 视频片段时长
            source_duration = video_duration
            
            if  not tools.vail_file(it.get('filename')):
                occur_error = True
                logs(f'[{i=}] 读取配音文件失败，插入原始时长静音')



            # 出错时使用视频片段时长的静音片段替代
            if occur_error:
                it['dubb_time'] = source_duration
                it['end_time'] = it['start_time'] + source_duration
                audio_concat_list.append(self._create_silen_file(i, source_duration))
                audio_all_duration += source_duration
                logs(f'[{i=}] 配音出错，强制配音时长为视频时长={source_duration}ms')
            else:
                logs(f'[{i=}] 配音OK')
                shutil.copy2(it['filename'], clip_path)
                audio_concat_list.append(clip_path)
                it['dubb_time']=self._get_audio_time_ms(clip_path)
                if it['dubb_time'] < source_duration:
                    it['end_time'] = it['start_time'] + it['dubb_time']
                    # 配音短于视频片段时长，需补充静音
                    audio_concat_list.append(self._create_silen_file(i, source_duration - it['dubb_time']))
                    audio_all_duration += source_duration
                    logs(f"[{i=}] 配音短于视频片段时长，需补充静音={source_duration - it['dubb_time']}ms")
                else:
                    # 如果配音长于视频，忽略不处理
                    it['end_time'] = it['start_time'] + it['dubb_time']
                    audio_all_duration += it['dubb_time']
                    logs(f"[{i=}] 配音长于视频片段时长{it['dubb_time'] - source_duration}ms")

            it['startraw'], it['endraw'] = tools.ms_to_time_string(ms=it['start_time']), tools.ms_to_time_string(
                ms=it['end_time'])

        return audio_concat_list

    # 创建静音音频文件并返回路径
    def _create_silen_file(self, i, duration):
        silence_path = Path(self.audio_clips_folder,
                            f"t_clip_{i:05d}_{random.randint(0, 99999)}_silence.wav").as_posix()
        silent_segment = AudioSegment.silent(duration=duration)
        silent_segment.export(silence_path, format="wav")
        return silence_path

    def _recalculate_timeline_with_theoretical_offset(self):
        """
        当不处理视频时，单纯计算配音时长。
        """
        audio_concat_list = []
        logs(f'【仅音频加速】：开始重新整理音频时间轴')

        for i, it in enumerate(self.queue_tts):
            tools.set_process(text=f"fix timeoffset {i}/{self.len_queue}", uuid=self.uuid)
            if i == 0 and it['start_time_source'] > 0:
                # 开头有静音片段，需插入
                audio_concat_list.append(self._create_silen_file(i, it['start_time_source']))

            # 原始字幕时长
            source_duration = it['end_time_source'] - it['start_time_source']
            # 跳过原始字幕时长为0的
            if source_duration <= 0:
                continue
            # 判断该配音文件是否出错
            occur_error = False
            logs(
                f"\n字幕[{it['line']}] 原始区间{it['start_time_source']}-{it['end_time_source']} (原字幕长) {source_duration}ms")
            if not tools.vail_file(it.get('filename')):
                occur_error = True
                logs(f'[{i=}] 读取配音文件失败，插入原始时长静音')

            clip_path = Path(self.audio_clips_folder, f"t_clip_{i:05d}.wav").as_posix()
            # 出错时使用原始字幕时长的静音片段替代
            if occur_error:
                error_silent = self._create_silen_file(i, source_duration)
                it['dubb_time'] = source_duration

            if i == 0:
                it['start_time'] = it['start_time_source']
                logs(
                    f'[{i=}]{"error" if occur_error else "OK"},第一条字幕开始时间保持原始不变，{it["start_time"]=},{it["end_time"]=}')
            else:
                # 后续字幕，如果上一条end_time>start_time_source,则使其等于上条 end_time,否则，两者之间添加静音片段
                last_end_time = self.queue_tts[i - 1]['end_time'] - it['start_time_source']
                if last_end_time >= 0:
                    it['start_time'] = self.queue_tts[i - 1]['end_time']
                    logs(
                        f'[{i=}]{"error" if occur_error else "OK"},当前字幕被上条字幕覆盖时间 {last_end_time}ms，因此将本条start_time,设为上条的end_time,{it["start_time"]=},{it["end_time"]=}')
                else:
                    # 同上一条字幕之间存在空隙，添加静音
                    silen_time = abs(last_end_time)
                    audio_concat_list.append(self._create_silen_file(i, silen_time))

                    it['start_time'] = it['start_time_source']
                    logs(
                        f'[{i=}]{"error" if occur_error else "OK"},当前字幕距离上条字幕存在 {silen_time}ms空隙，因此本条字幕开始时间不变,{it["start_time"]=},{it["end_time"]=}')

            it['end_time'] = it['start_time'] + it['dubb_time']
            if not occur_error:
                shutil.copy2(it['filename'], clip_path)
                audio_concat_list.append(clip_path)
            else:
                audio_concat_list.append(error_silent)
            it['startraw'], it['endraw'] = tools.ms_to_time_string(ms=it['start_time']), tools.ms_to_time_string(
                ms=it['end_time'])

            logs(
                f"字幕[{it['line']}] 新区间 {it['start_time']}-{it['end_time']} (配音时长 {it['dubb_time']}ms)\n")

        return audio_concat_list

    def _get_video_duration_safe(self, file_path):
        """
        一个健壮的视频时长获取方法。
        return -1 出错
        返回0不代表出错，可能仅有一帧数据，无法获取到精确时间
        """
        path_obj = Path(file_path)
        if not path_obj.exists() or path_obj.stat().st_size == 0:
            logs(f"视频时长探测失败：文件不存在或为空 -> {file_path}",level='warn')
            return -1
        try:
            duration_ms = tools.get_video_info(file_path, video_time=True)
            if duration_ms is None:
                logs(f"视频时长探测返回 None，可能文件已损坏 -> {file_path}",level='warn')
                return -1
            return duration_ms
        except Exception as e:
            logs(f"探测视频时长时发生严重错误: {e}。文件 -> {file_path}。将视其时长为0。",level='warn')
            return -1

    def _finalize_files(self, audio_concat_list):
        """
        负责使用FFmpeg拼接音频片段列表，并执行最后的音视频对齐检查。
        """
        final_step_text = tr("Concatenating audio and finalizing...")
        tools.set_process(text=final_step_text, uuid=self.uuid)
        logs("================== [最终步骤] 拼接音频、对齐并交付 ==================")

        self._ffmpeg_concat_audio(audio_concat_list)
        logs("所有处理完成，音视频已成功生成。")
    
    def _standardize_audio_segment(self, segment):
        """辅助函数，用于将任何AudioSegment对象标准化，防止DTS错乱"""
        return segment.set_frame_rate(self.AUDIO_SAMPLE_RATE).set_channels(self.AUDIO_CHANNELS)

    def _get_audio_time_ms(self, file_path):
        if not file_path or not tools.vail_file(file_path):
            return 0
        try:
            return len(AudioSegment.from_file(file_path))
        except Exception as e:
            logs(f"字幕获取音频文件 {file_path} 时长失败: {e}",level='warn')
            return 0

    def _ffmpeg_concat_audio(self, file_list):
        """
        使用混合拼接法来健壮地拼接大量音频文件，以规避Windows命令行长度限制。
        步骤1: 使用concat demuxer + 重新编码，生成一个临时的、干净的WAV文件。
        步骤2: 将这个临时的WAV文件转码为最终的目标格式。
        """
        if not file_list:
            logs("音频拼接列表为空，无法生成最终音频。",level='warn')
            return

        concat_txt_path = Path(f'{self.cache_folder}/audio_clips/audio_concat_list.txt').as_posix()

        # 对所有音频标准化
        
        def _format_wav(file_name):
            try:
                self._standardize_audio_segment(AudioSegment.from_file(file_name, format="wav")).export(file_name,
                                                                                                        format="wav")
            except Exception as e:
                logs(f'对音频切片{file_name} 标准化时出错 {e}', level="except")

        all_task = []
        with ThreadPoolExecutor(max_workers=min(12, len(file_list), os.cpu_count())) as pool:
            for i, fpath in enumerate(file_list):
                all_task.append(pool.submit(_format_wav, fpath))
                # 监控进度
            completed_tasks = 0
            for task in all_task:
                try:
                    task.result()  # 等待任务完成
                    completed_tasks += 1
                    tools.set_process(text=f'audio clip standardize {completed_tasks}/{len(all_task)}',uuid=self.uuid)
                except Exception as e:
                    logs(f"Task:audio clip standardize {completed_tasks + 1} failed with error: {e}",
                                            level="except")
        
        try:
            # 使用concat demuxer进行稳定的拼接
            logs(f"混合拼接步骤1: 创建包含 {len(file_list)} 个文件的拼接列表")
            tools.create_concat_txt(file_list, concat_txt=concat_txt_path)

            protxt=config.TEMP_DIR + f"/rate_audio_{time.time()}.txt"
            ext=Path(self.target_audio).suffix.lower()
            codecs={".m4a":"aac",".mp3":"libmp3lame",".wav":"copy"}
            cmd_step1 = [
                "-y",
                "-progress",protxt,
                "-f", "concat",
                "-safe", "0",
                "-i", concat_txt_path,
                "-c:a", codecs.get(ext,'copy'),
                self.target_audio
            ]
            self.stop_show_process=False
            threading.Thread(target=self._hebing_pro,args=(protxt,'concat audio')).start()
            tools.runffmpeg(cmd_step1, force_cpu=True)
            self.stop_show_process=True
            os.chdir(config.ROOT_DIR)

            if not tools.vail_file(self.target_audio):
                logs(f"音频拼接失败， {self.target_audio} 未生成。",level='warn')
                return

        finally:
            # 清理临时文件
            try:
                shutil.rmtree(f'{self.cache_folder}/audio_clips',ignore_errors=True)
                logs("已清理音频拼接临时文件。")
            except Exception as e:
                logs(f"清理音频拼接临时文件失败: {e}",level='warn')
    
    
    def _execute_audio_speedup_rubberband(self):
        """
        使用FFmpeg的`rubberband`或`atempo`滤镜进行高质量音频变速。
        """
        tools.set_process(text=tr("[3/5] audio by rubberband..."),
                          uuid=self.uuid)
        logs("================== [阶段 3/5] 执行音频加速,使用rubberband算法 ==================")


        all_cmds = []

        for i, it in enumerate(self.queue_tts):
            tools.set_process(text=f'{tr("[3/5] audio by rubberband...")} {i}/{self.len_queue}', uuid=self.uuid)
            # 需要加速后的新配音时长
            target_duration_ms = int(it['final_audio_duration_theoretical'])
            if target_duration_ms <= 0:  # 增加容差
                all_cmds.append("1")
                continue
            # 原始配音时长
            current_duration_ms = it['dubb_time']
            # 只有在需要压缩时才处理
            if current_duration_ms <= target_duration_ms or not tools.vail_file(it['filename']):
                all_cmds.append("1")
                continue

            # 在理论计算时已限制最大加速倍数，不再处理超过的情况
            speedup_ratio = current_duration_ms / target_duration_ms
            if float(speedup_ratio) <= 1.0:
                all_cmds.append("1")
                continue
            cmd = (it['filename'],target_duration_ms)
            all_cmds.append(cmd)


        total_tasks = len(all_cmds)

        if total_tasks == 0:
            return

        def _speedup_set_dubbtime(i, cmd):
            it = self.queue_tts[i]
            try:
                self.change_speed_rubberband(cmd[0],cmd[1])
                # 加速后实际的音频新时长，可能和理论不一致
                up_after_time = self._get_audio_time_ms(cmd[0])
                logs(f"变速后实际时长 {up_after_time}ms, 目标要求时长 {cmd[1]}ms")
            except Exception as e:
                self.queue_tts[i]['dubb_time']=self.queue_tts[i]['source_duration']
                self.queue_tts[i]['filename']=None
                logs(f"字幕[{it['line']}] 音频变速失败 {e}",level='warn')

        all_task = []
        with ThreadPoolExecutor(max_workers=min(12, len(all_cmds), os.cpu_count())) as pool:
            for i, cmd in enumerate(all_cmds):
                if isinstance(cmd, tuple):
                    all_task.append(pool.submit(_speedup_set_dubbtime, i, cmd))

            completed_tasks = 0
            for task in all_task:
                try:
                    task.result()  # 等待任务完成
                    completed_tasks += 1
                    tools.set_process( text=f"audio rubberband [{completed_tasks}/{total_tasks}] ...",
                        uuid=self.uuid)
                except Exception as e:
                    logs(f"Task {completed_tasks + 1} failed with error: {e}", level="except")

    

    def change_speed_rubberband(self,input_path, target_duration):
        """
        使用 Rubber Band 算法进行高保真实时变速
        """
        y, sr = sf.read(input_path)
        
        current_duration = int((len(y) / sr)*1000)
        
        # 计算变速倍率
        time_stretch_rate = current_duration / target_duration
        
        # pyrubberband 支持多声道，直接传入即可
        # ts_mag 是变速倍率，>1 为变快（时长变短）
        y_stretched = pyrb.time_stretch(y, sr, time_stretch_rate)
        
        sf.write(input_path, y_stretched, sr)
        print(f"原时长: {current_duration:.2f}ms -> 目标时长: {target_duration:.2f}ms (倍率: {time_stretch_rate:.2f}x)")


