import json
import os
import re
from pathlib import Path
from typing import List, Dict, Union

import zhconv

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
        for i,segment in enumerate(data):
            for j,word_info in enumerate(segment["words"]):
                if self.jianfan:
                    segment['words'][j]['word']=zhconv.convert(word_info['word'], 'zh-hans')
                if self.detect_language[:2] in ['zh','ja','ko']:
                    segment['words'][j]['word']=word_info['word'].replace(' ',',')
            data[i]=segment

        for i,segment in enumerate(data):
            if "words" not in segment:
                continue

            text = "".join([word_info["word"] for word_info in segment["words"]])


            sentences = nltk.sent_tokenize(text)  # 使用 nltk 分句
            punctuated_text = ""
            for sentence in sentences:
                if self.detect_language[:2] in ['zh','ja','ko']:
                    sentence=sentence.strip().replace(' ',',')
                if sentence[-1] in [',', '?', '!', '，', '。', '？', '！']:
                    punctuated_text += sentence + " "
                else:
                    punctuated_text += sentence + (". " if self.detect_language[:2] not in ['zh','ja','ko'] else ',')
            punctuated_text = punctuated_text.strip()

            # 将标点符号插入到对应的 word 中
            word_index = 0
            punc_index = 0
            new_words = []
            for word_info in segment["words"]:
                tmp=word_info
                word = word_info["word"]
                while punc_index < len(punctuated_text) and punctuated_text[punc_index] in word:
                    punc_index += 1
                if punc_index < len(punctuated_text) and punctuated_text[punc_index] in [',', '.', '?', '!', '，', '。',
                                                                                         '？', '！']:
                    if punctuated_text[punc_index] not in word:
                        tmp={
                            "word": word + punctuated_text[punc_index],
                            "start": word_info["start"],
                            "end": word_info["end"]}

                        punc_index += 1
                tmp['word'] = re.sub(r"(?<!\d)\.(?!\d)", ",", tmp['word'])
                new_words.append(tmp)

            segment["words"] = new_words
            segment["text"] = punctuated_text
            data[i]=segment

        # print(f'\n\n###################################{data=}')
        return data

    def re_segment_sentences(self, data):
        with open(config.ROOT_DIR+"/test.srt", "w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False))
        """
        根据字级别信息重新划分句子，考虑 word 中可能包含多个字符的情况，并优化断句逻辑。

        Args:
            data: openai-whisper 返回的字幕数据，包含字级别信息。

        Returns:
            重新划分后的字幕数据，格式与输入相同。
        """
        flags=r'[,?!，。？！]|(\. )'
        flags_list=[',','.','!','?','，','。','！','？']
        if self.detect_language[:2] in ['zh', 'ja', 'ko']:
            maxlen =int(config.settings['cjk_len'])
            flags=r'[,?!，。？！]|(\. )'
        else:
            maxlen = int(config.settings['other_len'])
        shound_rephase=False
        for segment in data:
            if segment['words'][0]['end']-segment['words'][0]['start']>float(config.settings.get('overall_maxsecs',12))*1000:
                shound_rephase=True
                break
            if len(segment['text'])>=2.8*maxlen:
                shound_rephase=True
                break

        new_data = []
        if not config.settings['rephrase'] or not shound_rephase:
            for segment in data:
                tmp = {
                    "line": len(new_data) + 1,
                    "start_time": segment['words'][0]['start'],
                    "end_time": segment['words'][-1]['end'],
                    "text": tools.cleartext(segment['text']),
                }
                if self.jianfan:
                    tmp['text'] = zhconv.convert(tmp['text'], 'zh-hans')
                tmp["startraw"]=tools.ms_to_time_string(ms=tmp["start_time"])
                tmp["endraw"]=tools.ms_to_time_string(ms=tmp["end_time"])
                tmp['time'] = f'{tmp["startraw"]} --> {tmp["endraw"]}'
                new_data.append(tmp)
            return new_data

        try:
            data = self.add_punctuation_to_words(data)
        except Exception as e:
            config.logger.exception(e)
            print('\n\n使用nltk分句失败')

        sentence = ""
        sentence_start = data[0]["words"][0]['start']
        sentence_end = 0
        data_len=len(data)
        start_flag_word_info=None

        for seg_i,segment in enumerate(data):
            current_len=len(segment["words"])
            for i, word_info in enumerate(segment["words"]):
                word = word_info["word"]
                if len(word.strip())<1 or word.strip() in flags_list:
                    continue
                next_start=word_info['end']
                next_word=""
                if i+1 < current_len:
                    next_start= segment["words"][i + 1]["start"]
                    next_word=segment["words"][i + 1]["word"]
                elif i+1 == current_len and seg_i+1<data_len:
                    next_start=data[seg_i+1]['words'][0]['start']
                    next_word=data[seg_i+1]['words'][0]['word']
                elif i+1 == current_len and seg_i+1>=data_len:
                    next_start=data[-1]['words'][-1]['end']
                    next_word=data[-1]['words'][-1]['word']

                sentence += ('' if not start_flag_word_info else start_flag_word_info['word'])
                # 开头是标点符号
                if word.strip()[0] in flags_list:
                    if len(sentence)>=0.5*maxlen:
                        # 肯定不是第一个
                        tmp = {
                            "line": len(new_data) + 1,
                            "start_time": sentence_start,
                            "end_time": start_flag_word_info['end'] if start_flag_word_info else sentence_end,
                            "text": tools.cleartext(sentence),
                        }
                        tmp["startraw"] = tools.ms_to_time_string(ms=tmp["start_time"])
                        tmp["endraw"] = tools.ms_to_time_string(ms=tmp["end_time"])
                        tmp['time'] = f'{tmp["startraw"]} --> {tmp["endraw"]}'
                        new_data.append(tmp)
                        sentence_start=word_info['start']
                        sentence_end=word_info['end']
                        sentence=''
                    start_flag_word_info=word_info
                    continue

                start_flag_word_info=None
                end = word_info["end"]
                sentence_end = end
                sentence+=word

                is_insert=False
                # 判断如果下个字符存在符号，且下个字符长度小于0.2*maxlen，则不插入
                if next_word and len(sentence.strip()) < 1.2*maxlen and re.search(flags,next_word) and len(next_word)<0.2*maxlen:
                    continue

                if next_start >= end+1000:
                    is_insert=True
                elif next_start>=end+200 and len(sentence.strip())>0.1*maxlen:
                    is_insert=True
                elif next_start> end and re.search(flags, word) and len(sentence.strip())>maxlen*0.2:
                    is_insert=True

                if not is_insert and re.search(flags, word) and len(sentence.strip())>=0.5*maxlen:
                    is_insert=True

                if not is_insert:
                    if self.subtitle_type>0 and len(sentence.strip())>=maxlen*1.8:
                        is_insert=True
                    elif  self.subtitle_type==0 and len(sentence.strip())>maxlen*2:
                        is_insert=True

                if not is_insert:
                    continue

                tmp = {
                    "line": len(new_data) + 1,
                    "start_time": sentence_start,
                    "end_time": sentence_end,
                    "text": tools.cleartext(sentence),
                }
                tmp["startraw"]=tools.ms_to_time_string(ms=tmp["start_time"])
                tmp["endraw"]=tools.ms_to_time_string(ms=tmp["end_time"])
                tmp['time'] = f'{tmp["startraw"]} --> {tmp["endraw"]}'
                new_data.append(tmp)

                sentence = ""
                sentence_start = next_start
        if start_flag_word_info:
            sentence_end=start_flag_word_info['end'] if start_flag_word_info['end'] >sentence_end else sentence_end
            sentence+=start_flag_word_info['word']
        # 处理最后一句
        if sentence:
            if sentence_end - sentence_start > 0:
                tmp = {
                    "line": len(new_data) + 1,
                    "start_time": sentence_start,
                    "end_time": sentence_end,
                    "text": tools.cleartext(sentence),
                }
                tmp["startraw"]=tools.ms_to_time_string(ms=tmp["start_time"])
                tmp["endraw"]=tools.ms_to_time_string(ms=tmp["end_time"])
                tmp['time'] = f'{tmp["startraw"]} --> {tmp["endraw"]}'
                new_data.append(tmp)
        return new_data

    # True 退出
    def _exit(self) -> bool:
        if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
            return True
        return False
