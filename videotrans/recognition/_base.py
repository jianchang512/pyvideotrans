import json
import os
import re
from pathlib import Path
from typing import List, Dict, Union

from videotrans.configure import config
from videotrans.configure._base import BaseCon

from videotrans.util import tools


class BaseRecogn(BaseCon):

    def __init__(self, detect_language=None, audio_file=None, cache_folder=None,
                 model_name=None, inst=None, uuid=None, is_cuda=None,subtitle_type=0):
        super().__init__()
        # 需要判断当前是主界面任务还是单独任务，用于确定使用哪个字幕编辑区
        self.detect_language = detect_language
        self.audio_file = audio_file
        self.cache_folder = cache_folder
        self.model_name = model_name
        self.inst = inst
        self.uuid = uuid
        self.is_cuda = is_cuda
        self.has_done = False
        self.error = ''
        self.subtitle_type=subtitle_type


        self.api_url = ''
        self.proxies = None

        self.flag = [
            ",",
            
            ".",
            "?",
            "!",
            ";",
           
            "，",
            "。",
            "？",
            "；",      
            "！"
        ]
        
        self.join_word_flag = " "
        
        self.jianfan=False
        if self.detect_language[:2].lower() in ['zh', 'ja', 'ko']:
            self.maxlen = int(config.settings['cjk_len'])
            self.jianfan = True if self.detect_language[:2] == 'zh' and config.settings['zh_hant_s'] else False
        else:
            self.maxlen = int(config.settings['other_len'])
        
        if not tools.vail_file(self.audio_file):
            raise Exception(f'[error]not exists {self.audio_file}')

    # 出错时发送停止信号
    def run(self) -> Union[List[Dict], None]:
        self._signal(text="")
        try:
            if self.detect_language[:2].lower() in ['zh', 'ja', 'ko']:
                self.flag.append(" ")
                self.join_word_flag = ""
            return self._exec()
        except Exception as e:
            config.logger.exception(e, exc_info=True)
            msg = f'{str(e)}'
            if re.search(r'cub[a-zA-Z0-9_.-]+?\.dll', msg, re.I | re.M) is not None:
                msg = f'【缺少cuBLAS.dll】请点击菜单栏-帮助/支持-下载cublasxx.dll,或者切换为openai模型 {msg} ' if config.defaulelang == 'zh' else f'[missing cublasxx.dll] Open menubar Help&Support->Download cuBLASxx.dll or use openai model {msg}'
            elif re.search(r'out\s+?of.*?memory', msg, re.I):
                msg = f'显存不足，请使用较小模型，比如 tiny/base/small {msg}' if config.defaulelang == 'zh' else f'Insufficient video memory, use a smaller model such as tiny/base/small {msg}'
            elif re.search(r'cudnn', msg, re.I):
                msg = f'cuDNN错误，请尝试升级显卡驱动，重新安装CUDA12.x和cuDNN9 {msg}' if config.defaulelang == 'zh' else f'cuDNN error, please try upgrading the graphics card driver and reinstalling CUDA12.x and cuDNN9 {msg}'
            self._signal(text=msg, type="error")
            raise
        finally:
            if self.shound_del:
                self._set_proxy(type='del')

    def _exec(self) -> Union[List[Dict], None]:
        pass

    def add_punctuation_to_words(self, data):
        import nltk, os
        # 指定 nltk 数据存放路径
        nltk.data.path.append(config.ROOT_DIR + "/models")

        # 下载 punkt_tab 资源到指定路径
        if not os.path.exists(config.ROOT_DIR + "/models/tokenizers/punkt_tab"):
            nltk.download('punkt_tab', download_dir=config.ROOT_DIR + "/models")

        """
        在字级别信息中插入标点符号。

        Args:
            data: openai-whisper 返回的字幕数据，包含字级别信息。

        Returns:
            添加标点符号后的字幕数据，格式与输入相同。
        """

        for segment in data:
            if "words" not in segment:
                continue

            text = "".join([word_info["word"] for word_info in segment["words"]])
            sentences = nltk.sent_tokenize(text)  # 使用 nltk 分句
            punctuated_text = ""
            for sentence in sentences:
                if sentence[-1] in [',', '?', '!', '，', '。', '？', '！']:
                    punctuated_text += sentence + " "
                else:
                    punctuated_text += sentence + ". "
            punctuated_text = punctuated_text.strip()

            # 将标点符号插入到对应的 word 中
            word_index = 0
            punc_index = 0
            new_words = []
            for word_info in segment["words"]:
                word = word_info["word"]
                while punc_index < len(punctuated_text) and punctuated_text[punc_index] in word:
                    punc_index += 1
                if punc_index < len(punctuated_text) and punctuated_text[punc_index] in [',', '.', '?', '!', '，', '。',
                                                                                         '？', '！']:
                    if punctuated_text[punc_index] not in word:
                        new_words.append({"word": word + punctuated_text[punc_index], "start": word_info["start"],
                                          "end": word_info["end"]})
                        punc_index += 1
                    else:
                        new_words.append(word_info)
                else:
                    new_words.append(word_info)

            segment["words"] = new_words
            segment["text"] = punctuated_text

        return data

    def _process_sentence(self,sentence):
        if self.jianfan:
            import zhconv
            sentence = zhconv.convert(sentence, 'zh-hans')
        if sentence[-1] in ['.', '。', ',', '，']:
            sentence = sentence[:-1]
        if sentence[0] in ['.', '。', ',', '，']:
            sentence = sentence[1:]
        return sentence.strip()

    def re_segment_sentences(self, data):
        """
        根据字级别信息重新划分句子，考虑 word 中可能包含多个字符的情况，并优化断句逻辑。

        Args:
            data: openai-whisper 返回的字幕数据，包含字级别信息。

        Returns:
            重新划分后的字幕数据，格式与输入相同。
        """
        new_data = []
        if not config.settings['rephrase']:
            for segment in data:
                tmp = {
                    "line": len(new_data) + 1,
                    "start_time": segment['words'][0]['start'],
                    "end_time": segment['words'][-1]['end'],
                    "text": self._process_sentence(segment['text']),
                }
                tmp['time'] = f'{tools.ms_to_time_string(ms=tmp["start_time"])} --> {tools.ms_to_time_string(ms=tmp["end_time"])}'
                new_data.append(tmp)
            return new_data
        try:
            data = self.add_punctuation_to_words(data)
        except Exception as e:
            config.logger.exception(e)
            print('使用nltk分句失败')

        sentence = ""
        sentence_start = data[0]["words"][0]['start']
        sentence_end = 0
        flags=r'[,?!，。？！]|(\. )'
        if self.detect_language[:2] in ['zh', 'ja', 'ko']:
            maxlen =config.settings['cjk_len']
            flags=r'[,?!，。？！]|(\. )|\s| '
        else:
            maxlen = config.settings['other_len']

        data_len=len(data)
        for seg_i,segment in enumerate(data):
            current_len=len(segment["words"])
            for i, word_info in enumerate(segment["words"]):
                word = word_info["word"]
                start = word_info["start"]
                end = word_info["end"]

                word = re.sub(r"(?<!\d)\.(?!\d)", ",", word)
                sentence += word
                sentence_end = end

                is_insert=False
                next_start= segment["words"][i + 1]["start"] if  i+1 < current_len else end
                if i+1 >= current_len and seg_i+1<data_len:
                    next_start=data[seg_i+1]['words'][0]['start']

                if next_start >= end+2000:
                    is_insert=True
                elif re.search(flags, word) and next_start > end+50 and len(sentence.strip())>maxlen/3:
                    is_insert=True
                elif re.search(flags, word) and len(sentence.strip())>=maxlen*0.8:
                    is_insert=True
                elif self.subtitle_type>0 and sentence_end-sentence_start>int(config.settings.get('overall_maxsecs',6))*1000*1.3:
                    is_insert=True
                elif self.subtitle_type==0 and sentence_end-sentence_start>10000:
                    is_insert=True


                if not is_insert:
                    continue


                tmp = {
                    "line": len(new_data) + 1,
                    "start_time": sentence_start,
                    "end_time": sentence_end,
                    "text": self._process_sentence(sentence),
                }
                tmp['time'] = f'{tools.ms_to_time_string(ms=tmp["start_time"])} --> {tools.ms_to_time_string(ms=tmp["end_time"])}'
                new_data.append(tmp)

                sentence = ""
                sentence_start = next_start

        # 处理最后一句
        if sentence:
            if sentence_end - sentence_start > 0:
                tmp = {
                    "line": len(new_data) + 1,
                    "start_time": sentence_start,
                    "end_time": sentence_end,
                    "text": self._process_sentence(sentence),
                }
                tmp['time'] = f'{tools.ms_to_time_string(ms=tmp["start_time"])} --> {tools.ms_to_time_string(ms=tmp["end_time"])}'
                new_data.append(tmp)

        return new_data

    # True 退出
    def _exit(self) -> bool:
        if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
            return True
        return False
