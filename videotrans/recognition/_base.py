import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from tenacity import RetryError

from videotrans.configure import config
from videotrans.configure._base import BaseCon
from videotrans.configure._except import SpeechToTextError
from videotrans.util import tools


@dataclass
class BaseRecogn(BaseCon):
    detect_language: Optional[str] = None
    audio_file: Optional[str] = None
    cache_folder: Optional[str] = None
    model_name: Optional[str] = None
    inst: Optional[Any] = None
    uuid: Optional[str] = None
    is_cuda: Optional[bool] = None
    target_code: Optional[str] = None
    subtitle_type: int = 0

    has_done: bool = field(default=False, init=False)
    error: str = field(default='', init=False)
    api_url: str = field(default='', init=False)
    proxies: Optional = field(default=None, init=False)

    device: str = field(init=False)
    flag: List[str] = field(init=False)
    raws: List = field(default_factory=list, init=False)
    join_word_flag: str = field(init=False)
    jianfan: bool = field(init=False)
    maxlen: int = field(init=False)




    def __post_init__(self):
        super().__init__()
        self.device = 'cuda' if self.is_cuda else 'cpu'
        # 断句标志
        self.flag = [
            ",", ".", "?", "!", ";",
            "，", "。", "？", "；", "！"
        ]
        # 连接字符 中日韩粤语 直接连接，无需空格，其他语言空格连接
        self.join_word_flag = " "

        if self.detect_language and self.detect_language[:2].lower() in ['zh', 'ja', 'ko']:
            self.maxlen = int(float(config.settings.get('cjk_len', 20)))
            self.jianfan = True if self.detect_language[:2] == 'zh' and config.settings.get('zh_hant_s') else False
        else:
            self.maxlen = int(float(config.settings.get('other_len', 60)))
            self.jianfan = False

        if not tools.vail_file(self.audio_file):
            raise RuntimeError(f'No {self.audio_file}')

    # run->_exec
    def run(self) -> Union[List[Dict], None]:
        Path(config.TEMP_HOME).mkdir(parents=True, exist_ok=True)
        self._signal(text="")
        try:
            if self.detect_language[:2].lower() in ['zh', 'ja', 'ko', 'yu']:
                self.flag.append(" ")
                self.join_word_flag = ""
            return self._exec()
        except RetryError as e:
            raise e.last_attempt.exception()
        except Exception as e:
            config.logger.exception(e, exc_info=True)
            raise
        finally:
            if self.shound_del:
                self._set_proxy(type='del')

    def _exec(self) -> Union[List[Dict], None]:
        pass

    def re_segment_sentences(self, words, langcode=None):

        try:
            from videotrans.translator._chatgpt import ChatGPT
            ob = ChatGPT()
            if self.inst and self.inst.status_text:
                self.inst.status_text = "正在重新断句..." if config.defaulelang == 'zh' else "Re-segmenting..."
            return ob.llm_segment(words, self.inst, config.settings.get('llm_ai_type', 'openai'))
        except json.decoder.JSONDecodeError as e:
            self.inst.status_text = "使用LLM重新断句失败,所用模型可能不支持输出JSON格式" if config.defaulelang == 'zh' else "Re-segmenting Error"
            config.logger.error(f"重新断句失败[JSONDecodeError]，已恢复原样 {e}")
            raise
        except Exception as e:
            self.inst.status_text = "使用LLM重新断句失败" if config.defaulelang == 'zh' else "Re-segmenting Error"
            config.logger.error(f"重新断句失败[except]，已恢复原样 {e}")
            raise


    def get_srtlist(self, raws):
        import zhconv
        jianfan = config.settings.get('zh_hant_s')
        
        if not config.settings.get('rephrase_local',False):
            for i in list(raws):
                if len(i['words']) < 1:
                    continue
                tmp = {
                    'text': zhconv.convert(i['text'], 'zh-hans') if jianfan and self.detect_language[:2] == 'zh' else i[
                        'text'],
                    'start_time': int(i['words'][0]['start'] * 1000),
                    'end_time': int(i['words'][-1]['end'] * 1000)
                }
                tmp['startraw'] = tools.ms_to_time_string(ms=tmp['start_time'])
                tmp['endraw'] = tools.ms_to_time_string(ms=tmp['end_time'])
                tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
                self.raws.append(tmp)
            return True
        if jianfan:
            self.flag.append(' ')
        all_words=[]
        for it in list(raws):
            if len(it['words'])>0:
                all_words+=it['words']
        
        tmp=None
        # 允许的最长语句时长
        max_ms=int(config.settings.get('max_speech_duration_s', 8))*1000
        # 允许的最短语句时长
        min_ms=int(config.settings['min_speech_duration_ms'])
        # 分隔句子的最小静音片段，大于则视为断句点
        min_silence=int(config.settings['min_silence_duration_ms'])
        all_len=len(all_words)
        for i,w in enumerate(all_words):
            word_text=zhconv.convert(w['word'], 'zh-hans') if jianfan and self.detect_language[:2] == 'zh' else w['word']
            if not tmp:
                tmp={
                    'text': word_text,
                    'start_time': int(w['start'] * 1000),
                    'end_time': int(w['end'] * 1000)
                }
                continue
            # 虽然句子时长小于 min_ms 应该继续，但若是当前单词和tmp结束时间差距过大(大于2*min_silence)，也应强制断句
            if w['start']*1000-tmp['end_time']>=2*min_silence:
                tmp['startraw'] = tools.ms_to_time_string(ms=tmp['start_time'])
                tmp['endraw'] = tools.ms_to_time_string(ms=tmp['end_time'])
                tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
                tmp['text']=tmp['text'] + (word_text[0] if word_text[0] in self.flag else '')
                self.raws.append(tmp)
                tmp={
                    'text': word_text[1:] if word_text[0] in self.flag else  word_text,
                    'start_time': int(w['start'] * 1000),
                    'end_time': int(w['end'] * 1000)
                }
                continue
                
            # 当前句子时长如果小于 min_ms,继续插入
            tmp_diff_ms=tmp['end_time']-tmp['start_time']
            if tmp_diff_ms<min_ms or word_text[-1] in self.flag:
                tmp['end_time']=int(w['end']*1000)
                tmp['text']+=word_text
                continue
            
            # 符合以下条件则为断句之处
            # 0.若是当前单词和tmp结束时间差距过大(大于2*min_silence)，则无论是否达到最小语句时长也强制断句
            # 1.如果大于等于 min_ms 并且恰好当前末尾或下一个开头有标点 is_flag
            # 2.虽然没有标点，但是当前单词与 tmp 中间距大于等于 min_silence
            # 3.当前语句时长已大于1.5倍的 max_ms 则强制断句
            is_flag=tmp['text'][-1] in self.flag or word_text[0] in self.flag
            # 当前单词和 tmp 结束之间的差距
            current_diff=w['start']*1000-tmp['end_time']
            new_min_silence=min_silence
            # 如果已经大于 max_ms，但没有遇到标点，此时尝试使用 0.3倍的更小的min_silence分隔句子
            if not is_flag and tmp_diff_ms>max_ms:
                new_min_silence=0.3*min_silence
            if is_flag  or (current_diff >= new_min_silence) or tmp_diff_ms>=1.5*max_ms:
                tmp['startraw'] = tools.ms_to_time_string(ms=tmp['start_time'])
                tmp['endraw'] = tools.ms_to_time_string(ms=tmp['end_time'])
                tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
                tmp['text']=tmp['text'] + (word_text[0] if word_text[0] in self.flag else '')
                self.raws.append(tmp)
                tmp={
                    'text': word_text[1:] if word_text[0] in self.flag else  word_text,
                    'start_time': int(w['start'] * 1000),
                    'end_time': int(w['end'] * 1000)
                }
                continue
            
            tmp['text'] += word_text
            tmp['end_time'] = int(w['end'] * 1000)
        if tmp:
            tmp['startraw'] = tools.ms_to_time_string(ms=tmp['start_time'])
            tmp['endraw'] = tools.ms_to_time_string(ms=tmp['end_time'])
            tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"
            tmp['text']=tmp['text'].strip()
            self.raws.append(tmp)
        
        # 再次检测，将过短的行合并给上一行
        new_raws=[]
        for i,it in enumerate(self.raws):
            if i>0 and it['end_time']-it['start_time']<min_ms:
                new_raws[-1]['text']+=it['text']
                new_raws[-1]['end_time']=it['end_time']
                new_raws[-1]['endraw']=tools.ms_to_time_string(ms=it['end_time'])
                new_raws[-1]['time'] = f"{new_raws[-1]['startraw']} --> {new_raws[-1]['endraw']}"
            else:
                it['line']=len(new_raws)+1
                it['text']=it['text'].strip()
                new_raws.append(it)
        self.raws=new_raws
        
    # True 退出
    def _exit(self) -> bool:
        if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
            return True
        return False
