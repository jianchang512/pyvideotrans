import json,re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict,  Optional, Union

from tenacity import RetryError

from videotrans.configure import config
from videotrans.configure._base import BaseCon
from videotrans.configure.config import tr, logs
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
    split_type: int=0 #0 整体识别，1 均等分割
    max_speakers:int=-1 # 说话人，-1不启用说话人，0=不限制数量，>0 说话人最大数量

    def __post_init__(self):
        super().__post_init__()
        if not tools.vail_file(self.audio_file):
            raise RuntimeError(f'No {self.audio_file}')
        self.device = 'cuda' if self.is_cuda else 'cpu'
        # 断句标志
        self.flag = [",", ".", "?", "!", ";", "，", "。", "？", "；", "！"]
        # 连接字符 中日韩粤语 直接连接，无需空格，其他语言空格连接
        self.join_word_flag = " "

        if self.detect_language and self.detect_language[:2].lower() in ['zh', 'ja', 'ko', 'yu']:
            self.maxlen = int(float(config.settings.get('cjk_len', 20)))
            self.jianfan = True if self.detect_language[:2] == 'zh' and config.settings.get('zh_hant_s') else False
            self.flag.append(" ")
            self.join_word_flag = ""
        else:
            self.maxlen = int(float(config.settings.get('other_len', 60)))
            self.jianfan = False

    # run->_exec
    def run(self) -> Union[List[Dict], None]:
        Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)
        try:
            srt_list=[]
            for i,it in enumerate(self._exec()):
                text=it['text'].strip()
                # 移除无效字幕行,全部由符号组成的行
                if text and not re.match(r'^[,.?!;\'"_，。？；‘’“”！~@#￥%…&*（【】）｛｝《、》\$\(\)\[\]\{\}=+\<\>\s-]+$',text):
                    it['line']=len(srt_list)+1
                    srt_list.append(it)
            
            if not srt_list:
                return []

            #Path("test-1.json").write_text(json.dumps(srt_list,indent=4,ensure_ascii=False),encoding='utf-8')
            # 修正时间戳重叠
            for i,it in enumerate(srt_list):
                if i>0 and srt_list[i-1]['end_time']>it['start_time']:
                    config.logger.warning(f'修正字幕时间轴重叠：{it=}')
                    srt_list[i-1]['end_time']=it['start_time']
                    srt_list[i-1]['endraw']=tools.ms_to_time_string(ms=it['start_time'])
                    srt_list[i-1]['time']=f"{srt_list[i-1]['startraw']} --> {srt_list[i-1]['endraw']}"
            #Path("test-2.json").write_text(json.dumps(srt_list,indent=4,ensure_ascii=False),encoding='utf-8')
            if not config.settings.get('merge_short_sub',True):
                return srt_list
                
            # 合并过短的字幕到邻近字幕, 第一个和最后一个字幕不合并
            post_srt_raws=[]
            min_speech=max(500,int(float(config.settings.get('min_speech_duration_ms',1000))))
            print(f'{min_speech=}')
            for idx,it in enumerate(srt_list):
                if idx==0 or idx==len(srt_list)-1 or it['end_time']-it['start_time']>=min_speech:
                    post_srt_raws.append(it)
                else:
                    # 小于1s
                    prev_diff=it['start_time']-post_srt_raws[-1]['end_time']
                    next_diff=srt_list[idx+1]['start_time']-it['end_time']
                    # 距离前个更近
                    config.logger.warning(f'字幕时长小于{min_speech=}，需要合并,{prev_diff=},{next_diff}，{it=}')
                    if prev_diff<next_diff:
                        config.logger.warning(f'\t合并进前面字幕')
                        post_srt_raws[-1]['end_time']=it['end_time']
                        post_srt_raws[-1]['endraw'] = tools.ms_to_time_string(ms=it['end_time'])
                        post_srt_raws[-1]['time'] = f"{post_srt_raws[-1]['startraw']} --> {post_srt_raws[-1]['endraw']}"
                        post_srt_raws[-1]['text']+=' '+it['text']
                    else:
                        config.logger.warning(f'\t合并进后面字幕')
                        srt_list[idx+1]['text']=it['text']+' '+srt_list[idx+1]['text']
                        srt_list[idx+1]['start_time']=it['start_time']
                        srt_list[idx+1]['startraw'] = tools.ms_to_time_string(ms=it['start_time'])
                        srt_list[idx+1]['time'] = f"{srt_list[idx+1]['startraw']} --> {srt_list[idx+1]['endraw']}"
            #Path("test-3.json").write_text(json.dumps(post_srt_raws,indent=4,ensure_ascii=False),encoding='utf-8')
            return post_srt_raws
        except RetryError as e:
            raise e.last_attempt.exception()
        except Exception as e:
            logs(str(e), level="except")
            raise

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


    def cut_audio(self):
        from pydub import AudioSegment
        import time
        dir_name = f"{config.TEMP_DIR}/clip_{time.time()}"
        Path(dir_name).mkdir(parents=True, exist_ok=True)
        data = []
        speech_chunks = self.get_speech_timestamp(self.audio_file)
        speech_len=len(speech_chunks)
        audio = AudioSegment.from_wav(self.audio_file)
        # 对大于30s的强制拆分，防止某些识别引擎不支持该时长而报错
        check_1=[]
        for i,it in enumerate(speech_chunks):
            diff=it[1]-it[0]
            if diff<30000:
                check_1.append(it)                    
            else:
                # 超过30s，一分为二
                off=diff//2
                check_1.append([it[0],it[0]+off])
                check_1.append([it[0]+off,it[1]])
                config.logger.warning(f'cut_audio 超过30s需要拆分，{diff=}')
        speech_chunks=check_1

        for i,it in enumerate(speech_chunks):
            start_ms, end_ms = it[0], it[1]
            chunk = audio[start_ms:end_ms]
            file_name = f"{dir_name}/audio_{i}.wav"
            chunk.export(file_name, format="wav")
            data.append({"line":i+1,"text":"","start_time": start_ms, "end_time": end_ms, "file": file_name})

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
        if min_speech_duration_ms is None: min_speech_duration_ms = int(config.settings.get('min_speech_duration_ms', 1000))
        if max_speech_duration_ms is None: max_speech_duration_ms = float(config.settings.get('max_speech_duration_s', 6)) * 1000
        if min_silent_duration_ms is None: min_silent_duration_ms = int(config.settings.get('min_silence_duration_ms', 500))
        print(f'{min_speech_duration_ms=},{max_speech_duration_ms=},{min_silent_duration_ms=}')
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
                sub_data = data[s * hop_size : e * hop_size]
                # 使用减半的静音阈值重新检测，同时带上最大时长限制
                sub_segs = self._detect_raw_segments(sub_data, threshold, tighter_min_sil_frames, max_speech_frames=max_frames_limit)
                
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
        speech_len=len(segments_ms)
        if speech_len<=1:
            return segments_ms
            
        # 对于小于1s的片段重新合并到邻近
        check_1=[]
        min_speech_duration_ms=min_speech_duration_ms or 1000
        print(f'合并前\n{segments_ms=}')
        for i,it in enumerate(segments_ms):
            diff=it[1]-it[0]
            if diff>=min_speech_duration_ms:
                check_1.append(it)                    
            else:
                # 距离前面空隙
                prev_diff=it[0]-check_1[-1][1] if len(check_1)>0 else None
                # 距离下个空隙
                next_diff=segments_ms[i+1][0]-it[1] if i<speech_len-1 else None
                config.logger.warning(f'get_speech_timestamp 时长小于 {min_speech_duration_ms}ms 需要合并,{diff=},{prev_diff=},{next_diff=}')
                if prev_diff is None and next_diff is not None:
                    # 插入后边
                    segments_ms[i+1][0]=it[0]
                elif prev_diff is not None and next_diff is None:
                    # 前面延长
                    check_1[-1][1]=it[1]
                elif prev_diff is not None and next_diff is not None:
                    if prev_diff<next_diff:
                        check_1[-1][1]=it[1]
                    else:
                        segments_ms[i+1][0]=it[0]
                else:
                    check_1.append(it)
        print(f'合并后\n{check_1=}')
        return check_1
            
    # True 退出
    def _exit(self) -> bool:
        if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
            return True
        return False
