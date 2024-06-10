import os
import time
import re
import webbrowser
from pathlib import Path
import pandas as pd
# ref: https://github.com/PaddlePaddle/PaddleSpeech/tree/develop/paddlespeech/t2s/frontend/zh_normalization
from .zh_normalization import TextNormalizer
from .cfg import SPEAKER_DIR

def openweb(url):
    time.sleep(3)
    webbrowser.open(url)

def get_parameter(request, param, default, cast_type):
    #  先request.args 后request.form 然后转换cast_type=int|float类型。
    for method in [request.args.get, request.form.get]:
        value = method(param, "").strip()
        if value:
            try:
                return cast_type(value)
            except ValueError:
                break  # args转换失败，退出尝试form
    return default  # 失败，返回默认值。


# 数字转为英文读法
def num_to_english(num):
    
    num_str = str(num)
    # English representations for numbers 0-9
    english_digits = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    units = ["", "ten", "hundred", "thousand"]
    big_units = ["", "thousand", "million", "billion", "trillion"]
    result = ""
    need_and = False  # Indicates whether 'and' needs to be added
    part = []  # Stores each group of 4 digits
    is_first_part = True  # Indicates if it is the first part for not adding 'and' at the beginning
    
    # Split the number into 3-digit groups
    while num_str:
        part.append(num_str[-3:])
        num_str = num_str[:-3]
    
    part.reverse()
    
    for i, p in enumerate(part):
        p_str = ""
        digit_len = len(p)
        if int(p) == 0 and i < len(part) - 1:
            continue
        
        hundreds_digit = int(p) // 100 if digit_len == 3 else None
        tens_digit = int(p) % 100 if digit_len >= 2 else int(p[0] if digit_len == 1 else p[1])
        
        # Process hundreds
        if hundreds_digit is not None and hundreds_digit != 0:
            p_str += english_digits[hundreds_digit] + " hundred"
            if tens_digit != 0:
                p_str += " and "
        
        # Process tens and ones
        if 10 < tens_digit < 20:  # Teens exception
            teen_map = {
                11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen",
                16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen"
            }
            p_str += teen_map[tens_digit]
        else:
            tens_map = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
            tens_val = tens_digit // 10
            ones_val = tens_digit % 10
            if tens_val >= 2:
                p_str += tens_map[tens_val] + (" " + english_digits[ones_val] if ones_val != 0 else "")
            elif tens_digit != 0 and tens_val < 2:  # When tens_digit is in [1, 9]
                p_str += english_digits[tens_digit]
        
        if p_str and not is_first_part and need_and:
            result += " and "
        result += p_str
        if i < len(part) - 1 and int(p) != 0:
            result += " " + big_units[len(part) - i - 1] + ", "
        
        is_first_part = False
        if int(p) != 0:
            need_and = True
    
    return result.capitalize()


def get_lang(text):
    # 定义中文标点符号的模式
    chinese_punctuation = "[。？！，、；：‘’“”（）《》【】…—\u3000]"
    # 使用正则表达式替换所有中文标点为""
    cleaned_text = re.sub(chinese_punctuation, "", text)
    # 使用正则表达式来匹配中文字符范围
    return "zh" if re.search('[\u4e00-\u9fff]', cleaned_text) is not None else "en"

def fraction_to_words(match):
    numerator, denominator = match.groups()
    # 这里只是把数字直接拼接成了英文分数的形式, 实际上应该使用某种方式将数字转换为英文单词
    # 例如: "1/2" -> "one half", 这里仅为展示目的而直接返回了 "numerator/denominator"
    return numerator + " over " + denominator



# 数字转为英文读法
def num2text(text):
    numtext=[' zero ',' one ',' two ',' three ',' four ',' five ',' six ',' seven ',' eight ',' nine ']
    point=' point '
    text = re.sub(r'(\d)\,(\d)', r'\1\2', text)
    text = re.sub(r'(\d+)\s*\+', r'\1 plus ', text)
    text = re.sub(r'(\d+)\s*\-', r'\1 minus ', text)
    text = re.sub(r'(\d+)\s*[\*x]', r'\1 times ', text)
    text = re.sub(r'((?:\d+\.)?\d+)\s*/\s*(\d+)', fraction_to_words, text)

    # 取出数字 number_list= [('1000200030004000.123', '1000200030004000', '123'), ('23425', '23425', '')]
    number_list=re.findall('((\d+)(?:\.(\d+))?%?)',text)
    if len(number_list)>0:            
        #dc= ('1000200030004000.123', '1000200030004000', '123','')
        for m,dc in enumerate(number_list):
            if len(dc[1])>16:
                continue
            int_text= num_to_english(dc[1])
            if len(dc)>2 and dc[2]:
                int_text+=point+"".join([numtext[int(i)] for i in dc[2]])
            if dc[0][-1]=='%':
                int_text=f' the pronunciation of  {int_text}'
            text=text.replace(dc[0],int_text)

        
    return text.replace('1',' one ').replace('2',' two ').replace('3',' three ').replace('4',' four ').replace('5',' five ').replace('6',' six ').replace('7','seven').replace('8',' eight ').replace('9',' nine ').replace('0',' zero ').replace('=',' equals ')



# 中英文数字转换为文字，特殊符号处理
def split_text(text_list):
    
    tx = TextNormalizer()
    
    result=[]
    for i,text in enumerate(text_list):
        tmp="".join(tx.normalize(text)) if get_lang(text)=='zh' else num2text(text)
        #tmp=num2text(text)
        if len(tmp)>200:
            tmp_res=split_text_by_punctuation(tmp)
            result=result+tmp_res
        else:
            result.append(tmp)
    print(f'{result=},len={len(result)}')
    return result

# 切分长行 200 150
def split_text_by_punctuation(text):
    # 定义长度限制
    min_length = 150
    punctuation_marks = "。？！，、；：”’》」』）】…—"
    english_punctuation = ".?!,:;)}…"
    
    # 结果列表
    result = []
    # 起始位置
    pos = 0
    
    # 遍历文本中的每个字符
    text_length=len(text)
    for i, char in enumerate(text):
        if char in punctuation_marks or char in english_punctuation:
            if  char=='.' and i< text_length-1 and re.match(r'\d',text[i+1]):
                continue
            # 当遇到标点时，判断当前分段长度是否超过120
            if i - pos > min_length:
                # 如果长度超过120，将当前分段添加到结果列表中
                result.append(text[pos:i+1])
                # 更新起始位置到当前标点的下一个字符
                pos = i+1
    #print(f'{pos=},{len(text)=}')
    
    # 如果剩余文本长度超过120或没有更多标点符号可以进行分割，将剩余的文本作为一个分段添加到结果列表
    if pos < len(text):
        result.append(text[pos:])
    
    return result


# 获取../static/wavs目录中的所有文件和目录并清理wav
def ClearWav(directory):
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

    if not files:
        return False, "wavs目录内无wav文件"

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
                print(f"已删除文件: {file_path}")
            elif os.path.isdir(file_path):
                print(f"跳过文件夹: {file_path}")
        except Exception as e:
            print(f"文件删除错误 {file_path}, 报错信息: {e}")
            return False, str(e)
    return True, "所有wav文件已被删除."
    
# 保存音色    
# 参考 https://github.com/craii/ChatTTS_WebUI/blob/main/utils.py
def save_speaker(name, tensor):   
    try:
        df = pd.DataFrame({"speaker": [float(i) for i in tensor]})
        df.to_csv(f"{SPEAKER_DIR}/{name}.csv", index=False, header=False)
    except Exception as e:
        print(e)
        
        
# 加载音色
# 参考 https://github.com/craii/ChatTTS_WebUI/blob/main/utils.py
def load_speaker(name):
    speaker_path = f"{SPEAKER_DIR}/{name}.csv"
    if not os.path.exists(speaker_path):
        return None
    try:
        import torch
        d_s = pd.read_csv(speaker_path, header=None).iloc[:, 0]
        tensor = torch.tensor(d_s.values)
    except Exception as e:
        print(e)
        return None
    return tensor


# 判断是否可以连接外网
def is_network():
    try:
        import requests
        requests.head('https://baidu.com')
    except Exception:
        return False
    else:
        return True
    return False
