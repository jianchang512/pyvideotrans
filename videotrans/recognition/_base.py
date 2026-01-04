import json, re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Union

from tenacity import RetryError

from videotrans.configure import config
from videotrans.configure._base import BaseCon
from videotrans.configure.config import tr
from videotrans.util import tools
from ten_vad import TenVad
import scipy.io.wavfile as Wavfile
import numpy as np


@dataclass
class BaseRecogn(BaseCon):
    recogn_type: int = 0  # 语音识别类型
    # 字幕检测语言
    detect_language: str = None

    # 模型名字
    model_name: Optional[str] = None
    # 待识别的 16k wav
    audio_file: Optional[str] = None
    # 临时目录
    cache_folder: Optional[str] = None

    # 任务id
    uuid: Optional[str] = None
    # 启用cuda加速
    is_cuda: bool = False

    # 字幕嵌入类型 0 1234
    subtitle_type: int = 0
    # 是否已结束
    has_done: bool = field(default=False, init=False)
    # 错误消息
    error: str = field(default='', init=False)
    # 识别 api地址
    api_url: str = field(default='', init=False)
    # 设备类型 cpu cuda
    device: str = field(init=False, default='cpu')
    # 标点符号
    flag: List[str] = field(init=False, default_factory=list)
    # 存放返回的字幕列表
    raws: List = field(default_factory=list, init=False)
    # 文字之间连接，中日韩粤语直接相连，其他空格
    join_word_flag: str = field(init=False, default=' ')
    # 是否需转为简体中文
    jianfan: bool = False
    # 字幕行字符数
    maxlen: int = 20
    max_speakers: int = -1  # 说话人，-1不启用说话人，0=不限制数量，>0 说话人最大数量
    llm_post: bool = False  # 是否进行llm重新断句，如果是，则无需在识别完成后进行简单修正

    def __post_init__(self):
        super().__post_init__()
        if not tools.vail_file(self.audio_file):
            raise RuntimeError(f'No {self.audio_file}')
        self.device = 'cuda' if self.is_cuda else 'cpu'
        # 常见标点
        self.flag = [",", ".", "?", "!", ";", "，", "。", "？", "；", "！"]
        # 逗号等软性标点
        self.half_flag = [",", "，", "-", "、", ":", "："]
        # 句子终止标点
        self.end_flag = [".", "。", "?", "？", "!", "！"]
        # 连接字符 中日韩粤语 直接连接，无需空格，其他语言空格连接
        self.join_word_flag = " "
        # 中日韩文字
        self.is_cjk = False
        if self.detect_language and self.detect_language[:2].lower() in ['zh', 'ja', 'ko', 'yu']:
            self.maxlen = int(float(config.settings.get('cjk_len', 20)))
            self.jianfan = True if self.detect_language[:2] == 'zh' and config.settings.get('zh_hant_s') else False
            self.flag.append(" ")
            self.join_word_flag = ""
            self.is_cjk = True
        else:
            self.maxlen = int(float(config.settings.get('other_len', 60)))
            self.jianfan = False

    # run->_exec
    def run(self) -> Union[List[Dict], None]:
        Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)
        try:
            srt_list = []
            for i, it in enumerate(self._exec()):
                text = it['text'].strip()
                # 移除无效字幕行,全部由符号组成的行
                if text and not re.match(r'^[,.?!;\'"_，。？；‘’“”！~@#￥%…&*（【】）｛｝《、》\$\(\)\[\]\{\}=+\<\>\s-]+$', text):
                    it['line'] = len(srt_list) + 1
                    srt_list.append(it)

            if not srt_list:
                return []

            # 修正时间戳重叠
            for i, it in enumerate(srt_list):
                if i > 0 and srt_list[i - 1]['end_time'] > it['start_time']:
                    config.logger.warning(f'修正字幕时间轴重叠：将前面字幕 end_time={srt_list[i - 1]["end_time"]} 改为当前字幕 start_time, {it=}')
                    srt_list[i - 1]['end_time'] = it['start_time']
                    srt_list[i - 1]['endraw'] = tools.ms_to_time_string(ms=it['start_time'])
                    srt_list[i - 1]['time'] = f"{srt_list[i - 1]['startraw']} --> {srt_list[i - 1]['endraw']}"

            # 合并过短的字幕到邻近字幕，以便符合 min_speech_duration_ms 要求, 第一个和最后一个字幕不合并
            if self.llm_post or not config.settings.get('merge_short_sub', True):
                if not self.llm_post:
                    for it in srt_list:
                        it['text'] = it['text'].strip('。').strip()
                return srt_list
            return self._fix_post(srt_list)
        except RetryError as e:
            raise e.last_attempt.exception()
        except Exception:
            raise

    # 未选择LLM重新断句并且选了 合并短字幕，则对识别出的字幕进行简单修正
    def _fix_post(self, srt_list):
        post_srt_raws = []
        min_speech = max(300, int(float(config.settings.get('min_speech_duration_ms', 1000))))
        config.logger.debug(f'对识别出的字幕进行简单修正，{min_speech=}')
        for idx, it in enumerate(srt_list):
            if not it['text'].strip():
                continue
            if idx == 0 or idx == len(srt_list) - 1 or it['end_time'] - it['start_time'] >= min_speech:
                post_srt_raws.append(it)
            else:
                # 小于1s
                prev_diff = it['start_time'] - post_srt_raws[-1]['end_time']
                next_diff = srt_list[idx + 1]['start_time'] - it['end_time']
                # 前面不是标点结束，而当前是标点结束
                # 前面是 句子中间停顿标点，而当前是句子结束 标点
                # 距离前个更近
                if (post_srt_raws[-1]['text'][-1] not in self.flag and it['text'][-1] in self.flag) or (
                        post_srt_raws[-1]['text'][-1] in self.half_flag and it['text'][
                    -1] in self.end_flag) or prev_diff <= next_diff:
                    config.logger.warning(
                        f'字幕时长小于{min_speech=}，需要合并进前面字幕,{prev_diff=},{next_diff=}，当前字幕={it},前面字幕={post_srt_raws[-1]}')
                    post_srt_raws[-1]['end_time'] = it['end_time']
                    post_srt_raws[-1]['endraw'] = tools.ms_to_time_string(ms=it['end_time'])
                    post_srt_raws[-1]['time'] = f"{post_srt_raws[-1]['startraw']} --> {post_srt_raws[-1]['endraw']}"
                    post_srt_raws[-1]['text'] += ' ' + it['text']
                else:
                    config.logger.warning(f'字幕时长小于{min_speech=}，需要合并进后面字幕,{prev_diff=},{next_diff=}，当前字幕={it},后边字幕={srt_list[idx + 1]}')
                    srt_list[idx + 1]['text'] = it['text'] + ' ' + srt_list[idx + 1]['text']
                    srt_list[idx + 1]['start_time'] = it['start_time']
                    srt_list[idx + 1]['startraw'] = tools.ms_to_time_string(ms=it['start_time'])
                    srt_list[idx + 1]['time'] = f"{srt_list[idx + 1]['startraw']} --> {srt_list[idx + 1]['endraw']}"

        if len(post_srt_raws) < 2:
            return post_srt_raws

        # 如果第一条字幕时长小于 min_speech,并且距离第二条字幕空隙小于2s，则将第一条字幕合并进第二条；空隙过大则是独立句子，不合并
        if post_srt_raws[0]['end_time'] - post_srt_raws[0]['start_time'] < min_speech and post_srt_raws[1][
            'start_time'] - post_srt_raws[0]['end_time'] < 2000:
            post_srt_raws[1]['start_time'] = post_srt_raws[0]['start_time']
            post_srt_raws[1]['text'] = post_srt_raws[0]['text'] + self.join_word_flag + post_srt_raws[1]['text']
            del post_srt_raws[0]
        if len(post_srt_raws) < 2:
            return post_srt_raws

        # 再判断最后一条字幕时长时长短于 min_speech，并且距离前面字幕空隙小于2s，则最后一条合并进前面一条；空隙过大则是独立句子，不合并
        if post_srt_raws[-1]['end_time'] - post_srt_raws[-1]['start_time'] < min_speech and post_srt_raws[-1][
            'start_time'] - post_srt_raws[-2]['end_time'] < 2000:
            post_srt_raws[-2]['end_time'] = post_srt_raws[-1]['end_time']
            post_srt_raws[-2]['text'] += self.join_word_flag + post_srt_raws[-1]['text']
            del post_srt_raws[-1]
        if len(post_srt_raws) < 2:
            return post_srt_raws

        # 如果当前字幕中间有标点，且第一个标点前的字 词小于4，而前条字幕末尾无标点，则给前个字幕
        for i, it in enumerate(post_srt_raws):
            if i == 0 or i == len(post_srt_raws) - 1:
                continue
            if post_srt_raws[i - 1]['end_time'] != it['start_time']:
                continue
            t = [t for t in re.split(r'[,.，。]', it['text']) if t.strip()]
            # 无有效文字
            if not t:
                it['text'] = ''
                continue
            # 仅一组
            if len(t) == 1:
                continue
            # 中日韩字数>3
            if self.is_cjk and len(t[0].strip()) > 3:
                continue

            # 上个字幕末尾有标点
            if post_srt_raws[i - 1]['text'][-1] in self.flag:
                continue
            if not self.is_cjk and len(t[0].strip().split(' ')) > 3:
                continue

            post_srt_raws[i - 1]['text'] += self.join_word_flag + it['text'][:len(t[0]) + 1]
            config.logger.warning(f'############该字幕原始文字={it["text"]}, 给前个的={it["text"][:len(t[0]) + 1]}')
            it['text'] = it["text"][len(t[0]) + 1:]
            config.logger.warning(f'剩余的 {it["text"]}\n')

        # 如果当前字幕中间有标点，且最后一个标点前的字 词小于4，则给后个字幕
        for i, it in enumerate(post_srt_raws):
            if i == 0 or i == len(post_srt_raws) - 1:
                continue
            if post_srt_raws[i + 1]['start_time'] != it['end_time']:
                continue
            t = [t for t in re.split(r'[,.，。]', it['text']) if t.strip()]
            # 无有效文字
            if not t:
                it['text'] = ''
                continue
            # 仅一组
            if len(t) == 1:
                continue
            # 字幕末尾有标点
            if it['text'][-1] in self.flag:
                continue
            # 中日韩字数>3
            if self.is_cjk and len(t[-1].strip()) > 3:
                continue
            if not self.is_cjk and len(t[-1].strip().split(' ')) > 3:
                continue

            post_srt_raws[i + 1]['text'] = it['text'][-len(t[-1]):] + self.join_word_flag + post_srt_raws[i + 1]['text']
            config.logger.warning(f'$$$$$$$$$$$$$$该字幕原始文字={it["text"]}, 给后个的={it["text"][-len(t[-1]):]}')
            it['text'] = it["text"][:-len(t[-1])]
            config.logger.warning(f'剩余的 {it["text"]}\n')

        # 移除末尾所有 . 。
        for it in post_srt_raws:
            it['text'] = it['text'].strip('。').strip()
        return [it for it in post_srt_raws if it['text'].strip()]

    def _exec(self) -> Union[List[Dict], None]:
        pass

    # 重新进行LLM断句
    def re_segment_sentences_json(self, words):
        try:
            from videotrans.translator._chatgpt import ChatGPT
            ob = ChatGPT()
            self._signal(text=tr("Re-segmenting..."))
            return ob.llm_segment(words, config.settings.get('llm_ai_type', 'openai'))
        except Exception as e:
            self._signal(text=tr("Re-segmenting Error"))
            config.logger.warning(f"重新断句失败[except]，已恢复原样 {e}")
            raise


    def _padforaudio(self):
        from pydub import AudioSegment
        silent_segment = AudioSegment.silent(duration=500)
        silent_segment.set_channels(1).set_frame_rate(16000)
        return silent_segment
    def cut_audio(self):
        from pydub import AudioSegment
        import time
        dir_name = f"{config.TEMP_DIR}/clip_{time.time()}"
        Path(dir_name).mkdir(parents=True, exist_ok=True)
        data = []
        speech_chunks = self.get_speech_timestamp(self.audio_file)
        speech_len = len(speech_chunks)
        audio = AudioSegment.from_wav(self.audio_file)
        # 对大于30s的强制拆分，小于1s的强制合并，防止某些识别引擎不支持而报错
        check_1 = []
        # 裁切出的最小语音时长需符合 min_speech_duration_ms 要求，合并过短的
        min_speech_duration_ms = min(25000, max(int(config.settings.get('min_speech_duration_ms', 1000)), 1000))
        for i, it in enumerate(speech_chunks):
            diff = it[1] - it[0]
            if diff < min_speech_duration_ms:
                # 距离前面空隙
                prev_diff = it[0] - check_1[-1][1] if len(check_1) > 0 else None
                # 距离下个空隙
                next_diff = speech_chunks[i + 1][0] - it[1] if i < speech_len - 1 else None
                if prev_diff is None and next_diff is not None:
                    config.logger.warning(
                        f'cut_audio 时长小于 {min_speech_duration_ms}ms 需要下个字幕左移开始时间,{diff=},{prev_diff=},{next_diff=}')
                    # 插入后边
                    speech_chunks[i + 1][0] = it[0]
                elif prev_diff is not None and next_diff is None:
                    # 前面延长
                    config.logger.warning(
                        f'cut_audio 时长小于 {min_speech_duration_ms}ms 需要前面字幕延长结束时间,{diff=},{prev_diff=},{next_diff=}')
                    check_1[-1][1] = it[1]
                elif prev_diff is not None and next_diff is not None:
                    if prev_diff < next_diff:
                        check_1[-1][1] = it[1]
                        config.logger.warning(
                            f'cut_audio 时长小于 {min_speech_duration_ms}ms 需要前面字幕延长结束时间,{diff=},{prev_diff=},{next_diff=}')
                    else:
                        speech_chunks[i + 1][0] = it[0]
                        config.logger.warning(
                            f'cut_audio 时长小于 {min_speech_duration_ms}ms 需要下个字幕左移开始时间,{diff=},{prev_diff=},{next_diff=}')
                else:
                    check_1.append(it)
            elif diff < 30000:
                check_1.append(it)
            else:
                # 超过30s，一分为二
                off = diff // 2
                check_1.append([it[0], it[0] + off])
                check_1.append([it[0] + off, it[1]])
                config.logger.warning(f'cut_audio 超过30s需要拆分，{diff=}')
        speech_chunks = check_1
        # 两侧填充空白
        silent_segment=self._padforaudio()
        for i, it in enumerate(speech_chunks):
            start_ms, end_ms = it[0], it[1]
            startraw,endraw=tools.ms_to_time_string(ms=it[0]),tools.ms_to_time_string(ms=it[1])
            chunk = audio[start_ms:end_ms]
            file_name = f"{dir_name}/audio_{i}.wav"
            (silent_segment+chunk+silent_segment).export(file_name, format="wav")
            data.append({
                "line": i + 1, 
                "text": "", 
                "start_time": start_ms, 
                "end_time": end_ms, 
                "startraw":startraw,
                "endraw":endraw,
                "time":f'{startraw} --> {endraw}',
                "file": file_name
            })

        return data

    def _detect_raw_segments(self, data, threshold, min_silent_frames, max_speech_frames=None):
        """
        内部辅助函数：根据给定的静音阈值和最大长度检测语音片段。
        """
        hop_size = 256
        ten_vad_instance = TenVad(hop_size, threshold)
        num_frames = data.shape[0] // hop_size

        segments = []
        triggered = False
        speech_start_frame = 0
        silence_frame_count = 0

        for i in range(num_frames):
            audio_frame = data[i * hop_size: (i + 1) * hop_size]
            _, is_speech = ten_vad_instance.process(audio_frame)

            if triggered:
                current_speech_len = i - speech_start_frame
                if is_speech == 1:
                    silence_frame_count = 0
                else:
                    silence_frame_count += 1

                # 结束条件：1. 静音满足长度 2. (可选) 达到最大长度强制切断
                is_silence_timeout = silence_frame_count >= min_silent_frames
                is_max_timeout = max_speech_frames is not None and current_speech_len >= max_speech_frames

                if is_silence_timeout or is_max_timeout:
                    if is_max_timeout:
                        end_frame = i
                    else:
                        end_frame = i - silence_frame_count

                    segments.append([speech_start_frame, end_frame])
                    triggered = False
                    silence_frame_count = 0
            else:
                if is_speech == 1:
                    triggered = True
                    speech_start_frame = i
                    silence_frame_count = 0

        if triggered:
            end_frame = num_frames - silence_frame_count
            segments.append([speech_start_frame, end_frame])

        return segments

    def get_speech_timestamp(self, input_wav,
                             threshold=None,
                             min_speech_duration_ms=None,
                             max_speech_duration_ms=None,
                             min_silent_duration_ms=None):
        """
        优化后的 VAD 策略：
        1. 使用长静音阈值进行初步分割。
        2. 对过长的片段，降低静音阈值进行二次细分。
        3. 对仍超长的片段进行硬截断。
        """
        # --- 参数初始化 ---
        if threshold is None: threshold = float(config.settings.get('threshold', 0.5))
        if min_speech_duration_ms is None: min_speech_duration_ms = int(
            config.settings.get('min_speech_duration_ms', 1000))
        if max_speech_duration_ms is None: max_speech_duration_ms = float(
            config.settings.get('max_speech_duration_s', 6)) * 1000
        if min_silent_duration_ms is None: min_silent_duration_ms = int(
            config.settings.get('min_silence_duration_ms', 500))
        config.logger.debug(f'VAD断句参数：{threshold=},{min_speech_duration_ms=},{max_speech_duration_ms=},{min_silent_duration_ms=}')
        frame_duration_ms = 16
        hop_size = 256

        try:
            sr, data = Wavfile.read(input_wav)
        except Exception as e:
            print(f"Error reading wav file: {e}")
            return []

        # --- 第一阶段：使用初始长静音阈值进行初步切分 (不设 max_speech 限制) ---
        min_sil_frames = min_silent_duration_ms / frame_duration_ms
        initial_segments = self._detect_raw_segments(data, threshold, min_sil_frames, max_speech_frames=None)

        # --- 第二阶段：细化超长片段 ---
        refined_segments = []
        half_max_frames = (max_speech_duration_ms / 2) / frame_duration_ms
        max_frames_limit = max_speech_duration_ms / frame_duration_ms
        tighter_min_sil_frames = (min_silent_duration_ms / 2) / frame_duration_ms

        for s, e in initial_segments:
            duration = e - s
            if duration > half_max_frames:
                # 提取该段音频数据
                sub_data = data[s * hop_size: e * hop_size]
                # 使用减半的静音阈值重新检测，同时带上最大时长限制
                sub_segs = self._detect_raw_segments(sub_data, threshold, tighter_min_sil_frames,
                                                     max_speech_frames=max_frames_limit)

                for ss, se in sub_segs:
                    refined_segments.append([s + ss, s + se])
            else:
                refined_segments.append([s, e])

        if not refined_segments:
            return []

        # --- 第三阶段：毫秒转换 & 强制硬截断保护 ---
        # 即使二次细分，如果有人一口气说了30秒没停顿，仍需硬截断
        segments_ms = []
        for s, e in refined_segments:
            start_ms = int(s * frame_duration_ms)
            end_ms = int(e * frame_duration_ms)

            # 循环确保不超 max_speech_duration_ms
            curr_s = start_ms
            while (end_ms - curr_s) > max_speech_duration_ms:
                segments_ms.append([curr_s, curr_s + int(max_speech_duration_ms)])
                curr_s += int(max_speech_duration_ms)

            if end_ms - curr_s > 0:
                segments_ms.append([curr_s, end_ms])
        speech_len = len(segments_ms)
        if speech_len <= 1:
            return segments_ms

        check_1 = []

        # 不允许最小语音片段低于500ms，可能无法有效识别而报错
        min_speech_duration_ms = max(min_speech_duration_ms or 1000, 500)
        config.logger.debug(f'get_speech_timestamp合并前\n{segments_ms=}')
        for i, it in enumerate(segments_ms):
            diff = it[1] - it[0]

            if diff >= min_speech_duration_ms:
                check_1.append(it)
            elif diff < 200:
                # 低于200ms的视为噪音，直接丢弃
                continue
            else:
                # 200-min_speech_duration_ms 之间的语音片段合并到邻近
                # 距离前面空隙
                prev_diff = it[0] - check_1[-1][1] if len(check_1) > 0 else None
                # 距离下个空隙
                next_diff = segments_ms[i + 1][0] - it[1] if i < speech_len - 1 else None
                if prev_diff is None and next_diff is not None:
                    # 插入后边
                    segments_ms[i + 1][0] = it[0]
                    config.logger.warning(
                        f'get_speech_timestamp 时长小于 {min_speech_duration_ms}ms 需要下个字幕左移开始时间,{diff=},{prev_diff=},{next_diff=}')
                elif prev_diff is not None and next_diff is None:
                    # 前面延长
                    check_1[-1][1] = it[1]
                    config.logger.warning(
                        f'get_speech_timestamp 时长小于 {min_speech_duration_ms}ms 需要前面字幕右移结束时间,{diff=},{prev_diff=},{next_diff=}')
                elif prev_diff is not None and next_diff is not None:
                    if prev_diff < next_diff:
                        check_1[-1][1] = it[1]
                        config.logger.warning(
                            f'get_speech_timestamp 时长小于 {min_speech_duration_ms}ms 需要前面字幕右移结束时间,{diff=},{prev_diff=},{next_diff=}')
                    else:
                        segments_ms[i + 1][0] = it[0]
                        config.logger.warning(
                            f'get_speech_timestamp 时长小于 {min_speech_duration_ms}ms 需要下个字幕左移开始时间,{diff=},{prev_diff=},{next_diff=}')
                else:
                    check_1.append(it)
        config.logger.debug(f'get_speech_timestamp合并后\n{check_1=}')
        return check_1

    # True 退出
    def _exit(self) -> bool:
        if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
            return True
        return False
