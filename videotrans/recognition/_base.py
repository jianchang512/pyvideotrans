import re, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

from videotrans.configure.config import tr, settings, logger
from videotrans.configure import config
from videotrans.configure.base import BaseCon
from videotrans.task.taskcfg import SrtItem
from videotrans.configure import contants
from videotrans.util.help_srt import ms_to_time_string


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
    audio_duration: int = 0
    max_speakers: int = -1  # 说话人，-1不启用说话人，0=不限制数量，>0 说话人最大数量
    llm_post: bool = False  # 是否进行llm重新断句，如果是，则无需在识别完成后进行简单修正
    speech_timestamps: List = field(default_factory=list)  # vad切割好的数据
    recogn2pass: bool = False

    def __post_init__(self):
        super().__post_init__()
        self.device = 'cuda' if self.is_cuda else 'cpu'
        # 常见标点
        self.flag = contants.PUNC_FLAGS
        # 逗号等软性标点
        self.half_flag = contants.PUNC_FLAGS_HALF
        # 句子终止标点
        self.end_flag = contants.PUNC_FLAGS_END
        # 连接字符 中日韩粤语高棉语泰国语 直接连接，无需空格，其他语言空格连接
        self.join_word_flag = " "
        # 中日韩文字
        self.is_cjk = False

        if self.detect_language and self.detect_language[:2].lower() in contants.CJK_LANG:
            self.maxlen = int(float(settings.get('cjk_len', 20)))
            self.jianfan = True if self.detect_language[:2] == 'zh' and settings.get('zh_hant_s') else False
            self.flag.append(" ")
            self.join_word_flag = ""
            self.is_cjk = True
        else:
            self.maxlen = int(float(settings.get('other_len', 60)))
            self.jianfan = False

    # run->_exec
    def run(self) -> Union[List[SrtItem], None]:
        if hasattr(self, '_download'):
            self.signal(text=f"check or download models")
            self._download()
        self.signal(text=f"starting transcription")
        from tenacity import RetryError
        try:
            res = self._exec()
            if res:
                return self._post_fix(res)
            from videotrans.configure.excepts import SpeechToTextError
            raise SpeechToTextError(
                tr('No speech was detected, please make sure there is human speech in the selected audio/video and that the language is the same as the selected one.'))
        except RetryError as e:
            raise e.last_attempt.exception()
        finally:
            self.signal(text=f'STT ended')


    # 对转录结果进行简单后处理
    def _post_fix(self, res: List[SrtItem]) -> List[SrtItem]:
        srt_list = []
        logger.debug('移除无效字幕行')
        for i, it in enumerate(res):
            text = it['text'].strip()
            # 移除无效字幕行,全部由符号组成的行
            if text and not re.match(contants.NON_WORD, text):
                it['line'] = len(srt_list) + 1
                srt_list.append(it)
            else:
                logger.warning(f'移除无效字幕行,全部由符号组成的行：{i=},{text=}')

        if not srt_list:
            return []

        # 修正时间戳重叠
        logger.debug('修正重叠时间轴')
        for i, it in enumerate(srt_list):
            if i > 0 and srt_list[i - 1]['end_time'] > it['start_time']:
                logger.warning(
                    f'修正字幕时间轴重叠：将前面字幕 end_time={srt_list[i - 1]["end_time"]} 改为当前字幕 start_time, {it=}')
                srt_list[i - 1]['end_time'] = it['start_time']
                srt_list[i - 1]['endraw'] = ms_to_time_string(ms=it['start_time'])
                srt_list[i - 1]['time'] = f"{srt_list[i - 1]['startraw']} --> {srt_list[i - 1]['endraw']}"

        # 不是LLM重新断句，并且选中合并过短字幕, 进行合并
        if not self.recogn2pass and not self.llm_post and settings.get('merge_short_sub', True):
            logger.debug('开始合并邻近短字幕')
            srt_list=self._merge_sub(srt_list)

        if settings.get('del_end_punc'):
            logger.debug(f'开始移除每条字幕末尾标点')
            for it in srt_list:
                # 移除末尾标点
                it['text'] = it['text'].strip('。，？！,.?!').strip()
        return srt_list

    def _exec(self) -> Union[List[SrtItem], None]:
        raise NotImplemented()

    # 有些识别渠道需要预先使用VAD切割为合适时长的音频片段，然后再对片段识别，每个识别结果即为一条字幕
    # whisper模型并且没有选中预先分割，无需切割
    def _vad_split(self):
        _st = time.time()
        _vad_type = settings.get('vad_type', 'tenvad')
        title = f'VAD:{_vad_type} split audio...'
        self.signal(text=title)
        logger.debug(f'开始使用 [{_vad_type}] VAD处理')

        _threshold = float(settings.get('threshold', 0.5))
        _min_speech = max(int(float(settings.get('min_speech_duration_ms', 1000))), 0)
        # ten-vad 不得低于500ms
        if _vad_type == 'tenvad':
            _min_speech = max(_min_speech, 500)

        # 最长不得大于30s,并且不得小于 _min_speech
        _max_speech = max(min(int(float(settings.get('max_speech_duration_s', 6)) * 1000), 30000), _min_speech + 1000)
        # 静音阈值不得低于50ms
        _min_silence = max(int(settings.get('min_silence_duration_ms', 600)), 50)
        if self.recogn2pass:
            # 2次识别， 生成简短的字幕, 最短持续时长>=500ms，最长持续时长>短+500 and <4000ms
            _min_speech = max( int(float(settings.get('min_speech_duration_ms2', 1000))), 500)
            _max_speech = max( min( int(float(settings.get('max_speech_duration_s2', 2)) * 1000), 4000), _min_speech + 500)
            logger.debug(f'[当前是二次语音识别]{_vad_type},{_min_speech=}ms,{_max_speech=}ms,{_min_silence=}ms')

        logger.debug(f'[{_vad_type}语音识别参数],min_speech_duration_ms:{_min_speech}ms,max_speech_duration_ms:{_max_speech=}ms,min_silent_duration_ms:{_min_silence}ms, threshold:{_threshold}')
        kw = {
            "input_wav": self.audio_file,
            "threshold": _threshold,
            "min_speech_duration_ms": _min_speech,
            "max_speech_duration_ms": _max_speech,
            "min_silent_duration_ms": _min_silence
        }

        try:
            from videotrans.process.vad import get_speech_timestamp, get_speech_timestamp_silero
            self.speech_timestamps = self._new_process(
                callback=get_speech_timestamp if _vad_type == 'tenvad' else get_speech_timestamp_silero,
                title=title,
                kwargs=kw)
        except Exception as e:
            logger.exception(f'VAD 处理失败 {e}', exc_info=True)
            if not self.recogn2pass:
                raise
        self.signal(text=f'[VAD] ended {int(time.time() - _st)}s')

    def cut_audio(self) -> List[SrtItem]:
        from pydub import AudioSegment
        dir_name = f"{config.TEMP_DIR}/clip_{time.time()}"
        Path(dir_name).mkdir(parents=True, exist_ok=True)
        if not self.speech_timestamps:
            self._vad_split()
        logger.debug('根据VAD结果切分音频')
        audio = AudioSegment.from_wav(self.audio_file)
        # 裁切出的最小语音时长需符合 min_speech_duration_ms 要求，合并过短的
        min_speech_duration_ms = min(25000, max(int(settings.get('min_speech_duration_ms', 1000)), 1000))

        new_chunk=[]
        speech_chunks = self.speech_timestamps
        speech_len = len(speech_chunks)
        for i, it in enumerate(speech_chunks):
            diff = it[1] - it[0]
            if diff>=min_speech_duration_ms:
                continue
            # 距离前面空隙
            prev_diff = it[0] - speech_chunks[i-1][1] if i > 0 else 0
            # 距离下个空隙
            next_diff = speech_chunks[i + 1][0] - it[1] if i < speech_len - 1 else 0
            msg=f' {prev_diff=},{next_diff=}'
            if i==0:
                #是第一个，
                speech_chunks[i + 1][0] = it[0]
                logger.debug(f'[第0个]:下个片段开始时间向左移, {msg}')
            elif i==speech_len-1:
                # 是最后一个
                speech_chunks[i-1][1] = it[1]
                logger.debug(f'[最后一个{i=}]:当前片段结束时间给上个片段结束时间, {msg}')
            elif prev_diff < next_diff:
                #左侧偏移小, 左侧结束位置延长
                speech_chunks[i-1][1]=it[1]
                logger.debug(f'[{i=}]:距离左侧距离短，当前片段结束时间给上个片段结束时间, {msg}')
            else:
                # 右侧偏移小，右侧开始时间左移
                speech_chunks[i + 1][0] = it[0]
                logger.debug(f'[{i=}]:距离右侧距离短，当前片段开始时间给下个片段开始时间, {msg}')
            speech_chunks[i][0]=-1
        for it in speech_chunks:
            if it[0]==-1:
                continue
            # 超过30s，一分为二
            diff=it[1]-it[0]
            if diff<30000:
                new_chunk.append(it)
                continue
            off = diff // 2
            new_chunk.extend([[it[0], it[0] + off],[it[0] + off, it[1]]])
            logger.warning(f'cut_audio 超过30s需要拆分，{diff=}')

        speech_chunks=new_chunk
        # 两侧填充空白
        silent_segment = AudioSegment.silent(duration=500).set_channels(1).set_frame_rate(16000)
        data=[]
        for i, it in enumerate(speech_chunks):
            start_ms, end_ms = it[0], it[1]
            startraw, endraw = ms_to_time_string(ms=it[0]), ms_to_time_string(ms=it[1])
            chunk = audio[start_ms:end_ms]
            file_name = f"{dir_name}/audio_{i}.wav"
            (silent_segment + chunk + silent_segment).export(file_name, format="wav")
            data.append(SrtItem(
                line=i + 1,
                text="",
                start_time=start_ms,
                end_time=end_ms,
                startraw=startraw,
                endraw=endraw,
                time=f'{startraw} --> {endraw}',
                filename=file_name
            ))
        logger.debug(f'切分为 {len(data)} 个音频片段')
        return data

    def _merge_sub(self, srt_list: List[SrtItem]) -> List[SrtItem]:
        """合并过短字幕，按标点重分配片段"""
        post_srt_raws = []
        min_speech = max(300, int(float(settings.get('min_speech_duration_ms', 1000))))
        max_speech = int(1000*float(settings.get('max_speech_duration_s', 5)))
        logger.debug(f'对识别出的字幕进行简单合并与修正，{min_speech=}ms,{max_speech=}ms')

        # 阶段 1：遍历合并过短项
        post_srt_raws = self._phase1_merge_short(srt_list, min_speech, post_srt_raws,max_speech)

        if len(post_srt_raws) < 2:
            return post_srt_raws

        # 阶段 2：处理首条过短
        post_srt_raws = self._phase2_merge_first(post_srt_raws, min_speech)
        if len(post_srt_raws) < 2:
            return post_srt_raws

        # 阶段 3：处理末条过短
        post_srt_raws = self._phase3_merge_last(post_srt_raws, min_speech)
        if len(post_srt_raws) < 2:
            return post_srt_raws

        # 阶段 4：标点碎片向前重分配
        post_srt_raws = self._phase4_redistribute_by_punct(post_srt_raws, forward=True)
        # 阶段 5：标点碎片向后重分配
        post_srt_raws = self._phase4_redistribute_by_punct(post_srt_raws, forward=False)

        # 阶段 6：清理尾部标点，剔除空白字幕
        if settings.get('del_end_punc'):
            for it in post_srt_raws:
                # 删除尾部标点
                it['text'] = it['text'].strip('。,.').strip()
        return [it for it in post_srt_raws if it['text'].strip()]

    def _phase1_merge_short(self, srt_list, min_speech, post_srt_raws,max_speech=5000):
        """遍历原始列表，短字幕合并到前后邻项"""
        for idx, it in enumerate(srt_list):
            if not it['text'].strip():
                continue
            if  idx == 0 or idx == len(srt_list) - 1 or (it['end_time'] - it['start_time'] >= min_speech and len(it['text'].strip())>1 ):
                post_srt_raws.append(it)
                continue

            prev_diff = it['start_time'] - post_srt_raws[-1]['end_time']
            next_diff = srt_list[idx + 1]['start_time'] - it['end_time']
            merge_forward = (
                    (post_srt_raws[-1]['text'][-1] not in self.flag and it['text'][-1] in self.flag)
                    or (post_srt_raws[-1]['text'][-1] in self.half_flag and it['text'][-1] in self.end_flag)
                    or prev_diff <= next_diff
            )
            # 如果需要合并到前面，并且 prev_diff == next_diff, 并且前面的长度已超过最大允许允许时长，并且差距不超过2s，否则仍合并到前面,则合并到后边
            if merge_forward and (prev_diff+2000>next_diff) and (post_srt_raws[-1]['end_time']-post_srt_raws[-1]['start_time'] >max_speech):
                merge_forward=False
                logger.warning(f'应合并到前边字幕，但已过长，因此强制合并进后个字幕')
            
            if merge_forward:
                self._log_merge('前', it, post_srt_raws[-1], prev_diff, next_diff)
                post_srt_raws[-1]['end_time'] = it['end_time']
                post_srt_raws[-1]['endraw'] = ms_to_time_string(ms=it['end_time'])
                post_srt_raws[-1]['time'] = f"{post_srt_raws[-1]['startraw']} --> {post_srt_raws[-1]['endraw']}"
                post_srt_raws[-1]['text'] += ' ' + it['text']
            else:
                self._log_merge('后', it, srt_list[idx + 1], prev_diff, next_diff)
                srt_list[idx + 1]['text'] = it['text'] + ' ' + srt_list[idx + 1]['text']
                srt_list[idx + 1]['start_time'] = it['start_time']
                srt_list[idx + 1]['startraw'] = ms_to_time_string(ms=it['start_time'])
                srt_list[idx + 1]['time'] = f"{srt_list[idx + 1]['startraw']} --> {srt_list[idx + 1]['endraw']}"
        return post_srt_raws

    def _phase2_merge_first(self, post_srt_raws, min_speech):
        """首条时长不足 min_speech 且与次条间隙 < 2s → 合并"""
        if (post_srt_raws[0]['end_time'] - post_srt_raws[0]['start_time'] < min_speech
                and post_srt_raws[1]['start_time'] - post_srt_raws[0]['end_time'] < 2000) or len(post_srt_raws[0]['text'].strip())<2:
            post_srt_raws[1]['start_time'] = post_srt_raws[0]['start_time']
            post_srt_raws[1]['text'] = post_srt_raws[0]['text'] + self.join_word_flag + post_srt_raws[1]['text']
            post_srt_raws.pop(0)
        return post_srt_raws

    def _phase3_merge_last(self, post_srt_raws, min_speech):
        """末条时长不足 min_speech 且与前条间隙 < 2s → 合并"""
        if (post_srt_raws[-1]['end_time'] - post_srt_raws[-1]['start_time'] < min_speech
                and post_srt_raws[-1]['start_time'] - post_srt_raws[-2]['end_time'] < 2000) or len(post_srt_raws[-1]['text'].strip())<2:
            post_srt_raws[-2]['end_time'] = post_srt_raws[-1]['end_time']
            post_srt_raws[-2]['text'] += self.join_word_flag + post_srt_raws[-1]['text']
            post_srt_raws.pop(-1)
        return post_srt_raws

    def _phase4_redistribute_by_punct(self, post_srt_raws, forward):
        """根据标点把短片段从当前字幕挪给前/后邻字幕"""
        for i, it in enumerate(post_srt_raws):
            if i == 0 or i == len(post_srt_raws) - 1:
                continue
            neighbour = i - 1 if forward else i + 1
            if post_srt_raws[neighbour]['end_time' if forward else 'start_time'] != it[
                'start_time' if forward else 'end_time']:
                continue

            fragments = [t for t in re.split(r'[,.，。]', it['text']) if t.strip()]
            if not fragments:
                it['text'] = ''
                continue
            if len(fragments) == 1:
                continue

            target_fragment = fragments[0] if forward else fragments[-1]
            # 检查片段是否太长
            if self.is_cjk:
                if len(target_fragment.strip()) > 3:
                    continue
            else:
                if len(target_fragment.strip().split(' ')) > 3:
                    continue

            # 邻项末尾/开头有结束标点则跳过
            if forward and post_srt_raws[i - 1]['text'][-1] in self.flag:
                continue
            if not forward and it['text'][-1] in self.flag:
                continue

            cut_len = len(fragments[0]) + 1 if forward else len(fragments[-1]) + 1
            moved_text = it['text'][:cut_len] if forward else it['text'][-len(fragments[-1]):]

            if forward:
                post_srt_raws[i - 1]['text'] += self.join_word_flag + moved_text
                it['text'] = it['text'][cut_len:]
            else:
                post_srt_raws[i + 1]['text'] = moved_text + self.join_word_flag + post_srt_raws[i + 1]['text']
                it['text'] = it['text'][:-len(fragments[-1])]

            logger.warning(f'该字幕原始文字={it["text"]}, 合并进{"前" if forward else "后"}条字幕的文字={moved_text}')
        return post_srt_raws

    @staticmethod
    def _log_merge(direction, current, neighbour, prev_diff, next_diff):
        logger.warning(
            f'\n[P]字幕时长过短，合并进 [{direction}面] 字幕,{prev_diff=},{next_diff=}\n当前被合并字幕={current}\n合并到的字幕={neighbour}')
