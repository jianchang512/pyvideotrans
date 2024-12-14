import copy
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Union

import torch
import zhconv

from videotrans.configure import config
from videotrans.configure._base import BaseCon

from videotrans.util import tools


class BaseRecogn(BaseCon):

    def __init__(self, detect_language=None, audio_file=None, cache_folder=None,
                 model_name=None, inst=None, uuid=None, is_cuda=None,target_code=None,subtitle_type=0):
        super().__init__()
        # 需要判断当前是主界面任务还是单独任务，用于确定使用哪个字幕编辑区
        self.detect_language = detect_language
        self.audio_file = audio_file
        self.cache_folder = cache_folder
        self.model_name = model_name
        self.inst = inst
        self.uuid = uuid
        self.is_cuda = is_cuda
        self.subtitle_type=subtitle_type
        self.has_done = False
        self.error = ''
        self.device="cuda" if  torch.cuda.is_available() else 'cpu'


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
            self.maxlen = int(float(config.settings.get('cjk_len',20)))
            self.jianfan = True if self.detect_language[:2] == 'zh' and config.settings['zh_hant_s'] else False
        else:
            self.maxlen = int(float(config.settings.get('other_len',60)))
        
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
            if re.search(r'cudaErrorNoKernelImageForDevice', msg, re.I) is not None:
                msg=f'请升级显卡驱动并安装CUDA 12.x，如果已是该版本，可能你的显卡太旧不兼容pytorch2.5，请取消CUDA加速:{msg}' if config.defaulelang=='zh' else f'Please upgrade your graphics card driver and install CUDA 12.x, or cancel CUDA acceleration:{msg}'
            elif re.search(r'cub[a-zA-Z0-9_.-]+?\.dll', msg, re.I | re.M) is not None:
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

    def re_segment_sentences(self,words,langcode):
        if self.inst and self.inst.status_text:
            self.inst.status_text="正在重新断句..." if config.defaulelang=='zh' else "Re-segmenting..."
        import zhconv
        # 删掉标点和不含有文字的word
        new_words = []
        pat = re.compile(r'[\"\'\[\]()_]')
        jianfan=config.settings.get('zh_hant_s')
        overall_maxsecs=int(config.settings.get('overall_maxsecs',15))
        if overall_maxsecs>=1000:
            overall_maxsecs=overall_maxsecs/1000

        for i, it in enumerate(words):
            it['word'] = pat.sub('', it['word']).strip()
            if not it['word']:
                continue
            it['word']=zhconv.convert(it['word'], 'zh-hans') if jianfan and  langcode=='zh' else it['word']
            new_words.append(it)
        text = "".join([w["word"] for w in new_words])
        text=text.strip()
        #print(f'text1={text}')
        copy_words = copy.deepcopy(new_words)    
        flag_list = [
            '，', 
            '。',
            '？', 
            '！',
            '；', 
            '、', 
            
            ',', 
            '?', 
            '. ', 
            '!', 
            ';',
            
        ]

        
        if langcode in ['zh','en']:

            try:
                self._set_proxy(type='del')
                from funasr import AutoModel
                model = AutoModel(model="ct-punc", 
                    model_revision="v2.0.4",
                    local_dir=config.ROOT_DIR + "/models",
                    disable_update=True,
                    disable_log=True,
                    disable_progress_bar=True,
                    hub='ms',
                    device=self.device)
                res = model.generate(input=text)
                text=res[0]['text'].strip()       

                # 记录每个标点符号在原text中应该插入的位置
                flags = {}
                pos_index = -1
                for i in range(len(text)):
                    if text[i] not in flag_list:
                        pos_index += 1
                    else:
                        flags[str(pos_index)] = text[i]

                # 复制一份words，将标点插入
                pos_start = -1
                flags_index = list(flags.keys())
                
                for w_index, it in enumerate(new_words):
                    if len(flags_index) < 1:
                        new_words[w_index] = it
                        break
                    f0 = int(flags_index[0])
                    if pos_start + len(it['word']) < f0:
                        pos_start += len(it['word'])
                        continue
                    # 当前应该插入的标点位置 f0大于 pos_start 并且小于 pos_start+长度，即位置存在于当前word
                    # word中可能是1-多个字符
                    if f0 > pos_start and f0 <= pos_start + len(it['word']):
                        if len(it['word']) == 1:
                            copy_words[w_index]['word'] += flags[str(f0)]
                            pos_start += len(it['word'])
                            flags_index.pop(0)
                        elif len(it['word']) > 1:
                            for j in range(f0 - pos_start):
                                if pos_start + j + 1 == f0:
                                    copy_words[w_index]['word'] += flags[str(f0)]
                                    pos_start += len(it['word'])
                                    flags_index.pop(0)
                                    break
                        new_words[w_index] = it
            except Exception as e:
                config.logger.exception(e, exc_info=True)
            finally:
                self._set_proxy(type='set')
            
        # 根据标点符号断句
        

        raws = []
        last_tmp = None
        length = int(config.settings.get('cjk_len' if langcode in ['zh','ja','ko'] else 'other_len' ))
        
        join_flag=''  if langcode in ['zh','ja','ko'] else ' '
        for i, w in enumerate(new_words):
            #config.logger.info(new_words)
            if not last_tmp:
                last_tmp = {
                    "line": 1 + len(raws),
                    "start_time": int(w['start'] * 1000),
                    "end_time": int(w['end'] * 1000),
                    "text": w['word'],
                }
                continue
            last_diff=w['start']*1000-last_tmp['end_time']
            last_duration=last_tmp['end_time']- last_tmp['start_time']
            #config.logger.info(f'\n{last_tmp=},\n{last_diff=},{last_duration=}')
            if last_duration<1000:
                last_tmp['text'] += join_flag +w['word']
                last_tmp['end_time'] = int(w['end'] * 1000)
                continue
                
            if (w['word'][-1] in flag_list and last_duration>=2000)  or (langcode in ['zh','ja','ko'] and  w['word'][-1]==' ' and last_duration>=2000):
                last_tmp['text'] +=join_flag + w['word']
                last_tmp['end_time'] = int(w['end'] * 1000)
                last_tmp['startraw']=tools.ms_to_time_string(ms=last_tmp["start_time"])
                last_tmp['endraw']=tools.ms_to_time_string(ms=last_tmp["end_time"])
                last_tmp['time'] = f"{last_tmp['startraw']} --> {last_tmp['endraw']}"
                raws.append(last_tmp)
                last_tmp = None
            
                
            elif last_diff>=500 or (last_duration>2000 and last_diff>=50) or (len(last_tmp['text']) > length and last_diff>0) or (langcode in ['zh','ja','ko'] and  w['word'][0]==' ' and last_duration>=2000) or last_duration >= overall_maxsecs*1000:
                last_tmp['startraw']=tools.ms_to_time_string(ms=last_tmp["start_time"])
                last_tmp['endraw']=tools.ms_to_time_string(ms=last_tmp["end_time"])
                last_tmp['time'] = f"{last_tmp['startraw']} --> {last_tmp['endraw']}"
                raws.append(last_tmp)
                
                last_tmp = {
                    "line": 1 + len(raws),
                    "start_time": int(w['start'] * 1000),
                    "end_time": int(w['end'] * 1000),
                    "text": w['word'],
                }
            else:
                last_tmp['text'] +=join_flag + w['word']
                last_tmp['end_time'] = int(w['end'] * 1000)
        if last_tmp:
            last_tmp['startraw'] = tools.ms_to_time_string(ms=last_tmp["start_time"])
            last_tmp['endraw'] = tools.ms_to_time_string(ms=last_tmp["end_time"])
            last_tmp['time'] = f"{last_tmp['startraw']} --> {last_tmp['endraw']}"
            raws.append(last_tmp)
        return raws

    # True 退出
    def _exit(self) -> bool:
        if config.exit_soft or (config.current_status != 'ing' and config.box_recogn != 'ing'):
            return True
        return False
