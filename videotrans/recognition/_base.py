import re, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Union
from tenacity import RetryError
from videotrans.configure import config
from videotrans.configure._base import BaseCon
from videotrans.util import tools
from videotrans.task.vad import get_speech_timestamp, get_speech_timestamp_silero
from pydub import AudioSegment


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
    audio_duration:int=0
    max_speakers: int = -1  # 说话人，-1不启用说话人，0=不限制数量，>0 说话人最大数量
    llm_post: bool = False  # 是否进行llm重新断句，如果是，则无需在识别完成后进行简单修正
    speech_timestamps: List = field(default_factory=list)  # vad切割好的数据
    recogn2pass:bool=False

    def __post_init__(self):
        super().__post_init__()
        config.logger.debug(f'BaseRecogn 初始化')
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

    def _vad_split(self):
        _st = time.time()
        _vad_type = config.settings.get('vad_type', 'tenvad')
        title=f'VAD:{_vad_type} split audio...'
        self._signal(text=title)
        # 重新拉取最新值
        settings=config.parse_init()

        _threshold = float(settings.get('threshold', 0.5))
        _min_speech = max(int(settings.get('min_speech_duration_ms', 1000)),0)
        # ten-vad不得低于500ms
        if _vad_type=='tenvad':
            _min_speech=max(_min_speech,500)
        # 最长不得大于30s,并且不得小于 _min_speech
        _max_speech = max(min(int(float(settings.get('max_speech_duration_s', 6)) * 1000),30000),_min_speech+1000)
        # 静音阈值不得低于50ms
        _min_silence = max(int(settings.get('min_silence_duration_ms', 600)),50)
        if self.recogn2pass:
            # 2次识别，均减半，以便生成简短的字幕
            _min_speech=int(max(0,_min_speech//2))
            # 不可低于 _min_speech 并且不可大于3000ms
            _max_speech=max(min(3000,_max_speech//2),_min_speech+1000)
            # 不可大于1000ms，并且不可小于50ms
            _min_silence=max(min(1000,_min_silence//2),50)

        config.logger.debug(f'[Before VAD {_vad_type}][{self.recogn2pass=}],{_min_speech=}ms,{_max_speech=}ms,{_min_silence=}ms')
        kw={
            "input_wav":self.audio_file,
            "threshold":_threshold,
            "min_speech_duration_ms":_min_speech,
            "max_speech_duration_ms":_max_speech,
            "min_silent_duration_ms":_min_silence
        }
        try:
            self.speech_timestamps=self._new_process(
                callback=get_speech_timestamp if _vad_type == 'tenvad' else get_speech_timestamp_silero,
                title=title,
                kwargs=kw)
        except Exception:
            if not self.recogn2pass:
                raise

        self._signal(text=f'[VAD] process ended {int(time.time() - _st)}s')
    

    # run->_exec
    def run(self) -> Union[List[Dict], None]:
        _st = time.time()
        
        Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)
        self._signal(text=f"check model")
        if hasattr(self, '_download'):
            self._download()

        self._signal(text=f"starting transcription")
        try:
            srt_list = []
            res=self._exec()
            if not res:
                raise RuntimeError('Unknow error')
            for i, it in enumerate(res):
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
                    config.logger.warning(
                        f'修正字幕时间轴重叠：将前面字幕 end_time={srt_list[i - 1]["end_time"]} 改为当前字幕 start_time, {it=}')
                    srt_list[i - 1]['end_time'] = it['start_time']
                    srt_list[i - 1]['endraw'] = tools.ms_to_time_string(ms=it['start_time'])
                    srt_list[i - 1]['time'] = f"{srt_list[i - 1]['startraw']} --> {srt_list[i - 1]['endraw']}"
            if self.recogn2pass:
                return srt_list
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
        finally:
            self._signal(text=f'STT ended:{int(time.time() - _st)}s')
            config.logger.debug(f'[语音识别]渠道{self.recogn_type},{self.model_name}:共耗时:{int(time.time() - _st)}s')

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
                    config.logger.warning(
                        f'字幕时长小于{min_speech=}，需要合并进后面字幕,{prev_diff=},{next_diff=}，当前字幕={it},后边字幕={srt_list[idx + 1]}')
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
            config.logger.warning(f'该字幕原始文字={it["text"]}, 合并进前条字幕的文字={it["text"][:len(t[0]) + 1]}')
            it['text'] = it["text"][len(t[0]) + 1:]
            config.logger.warning(f'剩余问文字 {it["text"]}\n')

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
            config.logger.warning(f'该字幕原始文字={it["text"]}, 合并到下条字幕文字={it["text"][-len(t[-1]):]}')
            it['text'] = it["text"][:-len(t[-1])]
            config.logger.warning(f'剩余文字 {it["text"]}\n')

        # 移除末尾所有 . 。
        for it in post_srt_raws:
            it['text'] = it['text'].strip('。').strip()
        return [it for it in post_srt_raws if it['text'].strip()]

    def _exec(self) -> Union[List[Dict], None]:
        pass

    def _padforaudio(self):
        silent_segment = AudioSegment.silent(duration=500)
        silent_segment.set_channels(1).set_frame_rate(16000)
        return silent_segment

    def cut_audio(self):
        dir_name = f"{config.TEMP_DIR}/clip_{time.time()}"
        Path(dir_name).mkdir(parents=True, exist_ok=True)
        data = []
        if not self.speech_timestamps:
            self._vad_split()
        speech_chunks = self.speech_timestamps
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
        silent_segment = self._padforaudio()
        for i, it in enumerate(speech_chunks):
            start_ms, end_ms = it[0], it[1]
            startraw, endraw = tools.ms_to_time_string(ms=it[0]), tools.ms_to_time_string(ms=it[1])
            chunk = audio[start_ms:end_ms]
            file_name = f"{dir_name}/audio_{i}.wav"
            (silent_segment + chunk + silent_segment).export(file_name, format="wav")
            data.append({
                "line": i + 1,
                "text": "",
                "start_time": start_ms,
                "end_time": end_ms,
                "startraw": startraw,
                "endraw": endraw,
                "time": f'{startraw} --> {endraw}',
                "file": file_name
            })

        return data

    # True 退出
    def _exit(self) -> bool:
        if config.exit_soft or (self.uuid and self.uuid in config.stoped_uuid_set):
            return True
        return False
