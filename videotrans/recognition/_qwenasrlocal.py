# zh_recogn 识别
import json
from dataclasses import dataclass
from typing import List, Dict, Union

from gradio_client import Client, handle_file

from pathlib import Path
import re,time

from videotrans.configure import config
from videotrans.configure.config import tr, params, settings, app_cfg, logger, defaulelang, ROOT_DIR, TEMP_DIR
from videotrans.configure._except import  StopRetry

from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools
from videotrans.process import qwen3asr_fun


@dataclass
class QwenasrlocalRecogn(BaseRecogn):
    def __post_init__(self):
        super().__post_init__()


    def _download(self):
        if defaulelang == 'zh':
            tools.check_and_down_ms(f'Qwen/Qwen3-ASR-{self.model_name}',callback=self._process_callback,local_dir=f'{ROOT_DIR}/models/models--Qwen--Qwen3-ASR-{self.model_name}')
            
            #tools.check_and_down_ms('Qwen/Qwen3-ForcedAligner-0.6B',callback=self._process_callback,local_dir=f'{ROOT_DIR}/models/models--Qwen--Qwen3-ForcedAligner-0.6B')
        else:
            tools.check_and_down_hf(model_id=f'Qwen3-ASR-{self.model_name}',repo_id=f'Qwen/Qwen3-ASR-{self.model_name}',local_dir=f'{ROOT_DIR}/models/models--Qwen--Qwen3-ASR-{self.model_name}',callback=self._process_callback)
            
            #tools.check_and_down_hf(model_id='Qwen3-ForcedAligner-0.6B',repo_id='Qwen/Qwen3-ForcedAligner-0.6B',local_dir=f'{ROOT_DIR}/models/models--Qwen--Qwen3-ForcedAligner-0.6B',callback=self._process_callback)


    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():
            return

        logs_file = f'{TEMP_DIR}/{self.uuid}/qwen3tts-{time.time()}.log'
        title="Qwen3-ASR"
        cut_audio_list_file = f'{TEMP_DIR}/{self.uuid}/cut_audio_list_{time.time()}.json'
        Path(cut_audio_list_file).write_text(json.dumps(self.cut_audio()),encoding='utf-8')
        kwargs = {     
            "cut_audio_list":   cut_audio_list_file,
            "logs_file": logs_file,
            "is_cuda": self.is_cuda,
            "audio_file":self.audio_file,
            "model_name":self.model_name
        }
        jsdata=self._new_process(callback=qwen3asr_fun,title=title,is_cuda=self.is_cuda,kwargs=kwargs)
        #print(f'{jsdata=}')
        logger.debug(f'Qwen-asr返回的字词时间戳数据:{jsdata=}')

        return jsdata#self.segmentation_asr_data(jsdata)
        
    
    def segmentation_asr_data(self,asr_data, 
                                min_duration=1.0, 
                                max_pref_duration=6.0, 
                                max_hard_duration=8.0, 
                                silence_threshold=0.4):
        """
        将ASR字词级数据重组为1-6秒的句子。
        
        Args:
            asr_data (list): ASR原始json列表
            min_duration (float): 最小句子时长(秒)，尽量不切分比这短的
            max_pref_duration (float): 期望最大时长(秒)，超过这个长度会倾向于切分
            max_hard_duration (float): 绝对最大时长(秒)，不得超过
            silence_threshold (float): 词与词之间超过多少秒视为静音断句点

        Returns:
            list: 格式化后的句子字典列表
        """
        if not asr_data:
            return []

        # 1. 定义多语言标点符号正则 (包括中文、英文、日文等常见标点)
        # 覆盖范围：,.?;!: 以及对应的全角符号
        punc_pattern = re.compile(r'[。.?？!！;；:：,，、\u3002\uff0c\uff1f\uff01]')
        
        # 2. 判断字符是否为CJK (中日韩) 用于决定拼接是否加空格
        def is_cjk(char):
            if not char: return False
            code = ord(char[0])
            # CJK Unified Ideographs scope roughly
            return 0x4E00 <= code <= 0x9FFF or \
                   0x3040 <= code <= 0x309F or \
                   0x30A0 <= code <= 0x30FF

        segments = []
        current_buffer = []
        
        def flush_buffer(buffer):
            """将当前缓存的词列表合并为一个句子字典"""
            if not buffer:
                return None
                
            start_ms = int(buffer[0]['start_time'] * 1000)
            end_ms = int(buffer[-1]['end_time'] * 1000)
            
            # 智能拼接文本
            text_parts = []
            for i, token in enumerate(buffer):
                word = token['text']
                if i == 0:
                    text_parts.append(word)
                else:
                    prev_word = buffer[i-1]['text']
                    # 如果前一个词结尾和当前词开头都是CJK字符，则直接拼接，否则加空格
                    # 注意：这里取prev_word[-1]和word[0]来判断
                    if prev_word and word and is_cjk(prev_word[-1]) and is_cjk(word[0]):
                        text_parts.append(word)
                    else:
                        # 对于非CJK语言（如英文），或者中英混排，加空格
                        # 特殊情况：如果当前词仅仅是标点符号，通常不需要前置空格(取决于ASR格式，这里简化处理)
                        if punc_pattern.match(word) and len(word) == 1:
                            text_parts.append(word)
                        else:
                            text_parts.append(" " + word) # 默认加空格
                            
            # 清理可能产生的多余空格 (例如中文里夹杂的空格)
            full_text = "".join(text_parts).strip()
            
            endraw=tools.ms_to_time_string(ms=end_ms)
            startraw=tools.ms_to_time_string(ms=start_ms)
            
            return {
                "start_time": start_ms,
                "end_time": end_ms,
                "endraw":endraw,
                "startraw":startraw,
                "time":f"{startraw} -> {endraw}",
                "text": full_text
            }

        # 3. 遍历数据进行切分
        for i, token in enumerate(asr_data):
            # 获取当前token信息
            token_text = token.get('text', '')
            token_start = token.get('start_time', 0.0)
            token_end = token.get('end_time', 0.0)
            
            # 计算与上一个词的静音间隙
            silence_gap = 0.0
            if i > 0:
                silence_gap = token_start - asr_data[i-1]['end_time']
            
            # 即使 buffer 为空，我们也先把它放进去，再判断是否要在此处结束
            # 但为了逻辑清晰，我们先判断是否要“结算”之前的 buffer
            
            should_split = False
            
            if current_buffer:
                buf_start = current_buffer[0]['start_time']
                current_duration = token_end - buf_start # 加上当前词后的总时长
                prev_duration = current_buffer[-1]['end_time'] - buf_start # 加当前词之前的时长
                
                has_punc = bool(punc_pattern.search(current_buffer[-1]['text']))
                is_long_silence = silence_gap >= silence_threshold
                
                # --- 断句决策逻辑 ---
                
                # 1. 硬限制：加上当前词会超过 8s，必须在当前词之前切断
                if current_duration > max_hard_duration:
                    should_split = True
                
                # 2. 理想区间断句 (1s - 6s)：如果有标点 或 有长静音
                elif prev_duration >= min_duration:
                    if has_punc:
                        should_split = True
                    elif is_long_silence:
                        should_split = True
                    # 3. 超过期望最大时长 (6s)：开始寻找任何断句机会（哪怕没有标点）
                    # 这里我们利用静音作为弱分割点，只要有微弱停顿就切
                    elif prev_duration >= max_pref_duration:
                        should_split = True
                
            if should_split:
                seg = flush_buffer(current_buffer)
                if seg: segments.append(seg)
                self._signal(text=seg.get('text','')+"\n",type='subtitle')
                current_buffer = []

            current_buffer.append(token)

        # 4. 处理剩余的 buffer
        if current_buffer:
            seg = flush_buffer(current_buffer)
            if seg: segments.append(seg)
        return segments
