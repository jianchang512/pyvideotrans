# 将普通文本转为合法的srt字符串
import copy
import os,json,re
import math
from collections import deque
from datetime import timedelta
from videotrans.configure import config
from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
from typing import List, Dict

def clean_text_for_srtdict(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'[^\w\s,.?!;:"\'%，。！？；：“”‘’、\-\u4e00-\u9fff]', '', text,flags=re.I | re.S)

    text = re.sub(r'\s+([，；。！？])', r'\1', text,flags=re.I | re.S)
    text = re.sub(r'\s+([,;:.!?])', r'\1', text,flags=re.I | re.S)
    text = re.sub(r'([,;:.!?])(?=[A-Za-z0-9])', r'\1 ', text,flags=re.I | re.S)
    text = re.sub(r'\s+', ' ', text,flags=re.I | re.S)
    text = text.strip()
    return text


def process_text_to_srt_str(input_text: str):
    if is_srt_string(input_text):
        return input_text

    # 将文本按换行符切割成列表
    text_lines = [line.strip() for line in input_text.replace("\n", "").splitlines() if line.strip()]

    # 分割大于50个字符的行
    text_str_list = []
    for line in text_lines:
        if len(line) > 50:
            # 按标点符号分割为多个字符串
            split_lines = re.split(r'[,.，。]', line)
            text_str_list.extend([l.strip() for l in split_lines if l.strip()])
        else:
            text_str_list.append(line)
    # 创建字幕字典对象列表
    dict_list = []
    start_time_in_seconds = 0  # 初始时间，单位秒

    for i, text in enumerate(text_str_list, start=1):
        # 计算开始时间和结束时间（每次增加1s）
        start_time = ms_to_time_string(seconds=start_time_in_seconds)
        end_time = ms_to_time_string(seconds=start_time_in_seconds + 1)
        start_time_in_seconds += 1

        # 创建字幕字典对象
        srt = f"{i}\n{start_time} --> {end_time}\n{text}"
        dict_list.append(srt)

    return "\n\n".join(dict_list)


# 判断是否是srt字符串
def is_srt_string(input_text):
    input_text = input_text.strip()
    if not input_text:
        return False

    # 将文本按换行符切割成列表
    text_lines = input_text.replace("\n", "").splitlines()
    if len(text_lines) < 3:
        return False

    # 正则表达式：第一行应为1到2个纯数字
    first_line_pattern = r'^\d{1,2}$'

    # 正则表达式：第二行符合时间格式
    second_line_pattern = r'^\s*?\d{1,2}:\d{1,2}:\d{1,2}(\W\d+)?\s*-->\s*\d{1,2}:\d{1,2}:\d{1,2}(\W\d+)?\s*$'

    # 如果前两行符合条件，返回原字符串
    if not re.match(first_line_pattern, text_lines[0].strip()) or not re.match(second_line_pattern,
                                                                               text_lines[1].strip()):
        return False
    return True


# 删除翻译结果的特殊字符
def cleartext(text: str, remove_start_end=True):
    res_text = text.replace('&#39;', "").replace('&quot;', '').replace("\u200b", " ").strip()
    # 删掉连续的多个标点符号，只保留一个
    res_text = re.sub(r'([，。！？,.?]\s?){2,}', ',', res_text,flags=re.I | re.S)
    return res_text


def ms_to_time_string(*, ms=0, seconds=None, sepflag=','):
    # 计算小时、分钟、秒和毫秒
    if seconds is None:
        td = timedelta(milliseconds=ms)
    else:
        td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000

    return f"{hours:02}:{minutes:02}:{seconds:02}{sepflag}{milliseconds:03}"


# 将不规范的 时:分:秒,|.毫秒格式为  aa:bb:cc,ddd形式
# eg  001:01:2,4500  01:54,14 等做处理
def format_time(s_time="", separate=','):
    if not s_time.strip():
        return f'00:00:00{separate}000'
    hou, min, sec, ms = 0, 0, 0, 0

    tmp = s_time.strip().split(':')
    if len(tmp) >= 3:
        hou, min, sec = tmp[-3].strip(), tmp[-2].strip(), tmp[-1].strip()
    elif len(tmp) == 2:
        min, sec = tmp[0].strip(), tmp[1].strip()
    elif len(tmp) == 1:
        sec = tmp[0].strip()

    if re.search(r',|\.', str(sec)):
        t = re.split(r',|\.', str(sec))
        sec = t[0].strip()
        ms = t[1].strip()
    else:
        ms = 0
    hou = f'{int(hou):02}'[-2:]
    min = f'{int(min):02}'[-2:]
    sec = f'{int(sec):02}'
    ms = f'{int(ms):03}'[-3:]
    return f"{hou}:{min}:{sec}{separate}{ms}"


def srt_str_to_listdict(srt_string):
    """解析 SRT 字幕字符串，更精确地处理数字行和时间行之间的关系"""
    srt_list = []
    time_pattern = r'\s?(\d+):(\d+):(\d+)([,.]\d+)?\s*?-{1,2}>\s*?(\d+):(\d+):(\d+)([,.]\d+)?\n?'
    lines = srt_string.splitlines()
    i = 0

    while i < len(lines):
        time_match = re.match(time_pattern, lines[i].strip())
        if time_match:
            # 解析时间戳
            start_time_groups = time_match.groups()[0:4]
            end_time_groups = time_match.groups()[4:8]

            def parse_time(time_groups):
                h, m, s, ms = time_groups
                ms = ms.replace(',', '').replace('.', '') if ms else "0"
                try:
                    return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)
                except (ValueError, TypeError):
                    return None

            start_time = parse_time(start_time_groups)
            end_time = parse_time(end_time_groups)

            if start_time is None or end_time is None:
                i += 1
                continue

            i += 1
            text_lines = []
            while i < len(lines):
                current_line = lines[i].strip()
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""  # 获取下一行，如果没有则为空字符串

                if re.match(time_pattern, next_line):  # 判断下一行是否为时间行
                    if re.fullmatch(r'\d+', current_line):  # 如果当前行为纯数字，则跳过
                        i += 1
                        break
                    else:
                        if current_line:
                            text_lines.append(current_line)
                        i += 1
                        break

                if current_line:
                    text_lines.append(current_line)
                    i += 1
                else:
                    i += 1

            text = ('\n'.join(text_lines)).strip()
            text = re.sub(r'</?[a-zA-Z]+>', '', text.replace("\r", '').strip(),flags=re.I | re.S)
            text = re.sub(r'\n{2,}', '\n', text,flags=re.I | re.S).strip()
            it = {
                "line": len(srt_list) + 1,  # 字幕索引，转换为整数
                "start_time": int(start_time),
                "end_time": int(end_time),  # 起始和结束时间
                "text": text if text else "",  # 字幕文本
            }
            it['startraw'] = ms_to_time_string(ms=it['start_time'])
            it['endraw'] = ms_to_time_string(ms=it['end_time'])
            it["time"] = f"{it['startraw']} --> {it['endraw']}"
            srt_list.append(it)


        else:
            i += 1  # 跳过非时间行

    return srt_list


# 将字符串或者字幕文件内容，格式化为有效字幕数组对象
# 格式化为有效的srt格式
def format_srt(content):
    result = []
    try:
        result = srt_str_to_listdict(content)
    except Exception as e:
        result = srt_str_to_listdict(process_text_to_srt_str(content))
    return result


# 将srt文件或合法srt字符串转为字典对象
def get_subtitle_from_srt(srtfile, *, is_file=True):
    def _readfile(file):
        content = ""
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
        except UnicodeDecodeError as e:
            try:
                with open(file, 'r', encoding='gbk') as f:
                    content = f.read().strip()
            except UnicodeDecodeError as e:
                logger.exception(e, exc_info=True)
                raise
        except BaseException:
            raise
        return content

    if is_file:
        content = _readfile(srtfile)
    else:
        content = srtfile.strip()

    if len(content) < 1:
        raise RuntimeError(f"The srt subtitles were not read. The file may be empty or the format does not conform to the SRT specification\n:{srtfile=}\n{content=}")
    result = format_srt(copy.copy(content))

    # txt 文件转为一条字幕
    if len(result) < 1:
        result = [
            {"line": 1,
             "start_time":0,
             "end_time":2000,
             "startraw":"00:00:00,000",
             "endraw":"00:00:02,000",
             "time": "00:00:00,000 --> 00:00:02,000",
             "text": "\n".join(content)}
        ]
    return result



# 从 字幕 对象中获取 srt 字幕串
def get_srt_from_list(srt_list):
    txt = ""
    line = 0
    # it中可能含有完整时间戳 it['time']   00:00:01,123 --> 00:00:12,345
    # 开始和结束时间戳  it['startraw']=00:00:01,123  it['endraw']=00:00:12,345
    # 开始和结束毫秒数值  it['start_time']=126 it['end_time']=678
    for it in srt_list:
        if not it.get('text','').strip():
            continue
        line += 1
        if "startraw" not in it:
            # 存在完整开始和结束时间戳字符串 时:分:秒,毫秒 --> 时:分:秒,毫秒
            if 'time' in it:
                startraw, endraw = it['time'].strip().split(" --> ")
                startraw = format_time(startraw.strip().replace('.', ','), ',')
                endraw = format_time(endraw.strip().replace('.', ','), ',')
            elif 'start_time' in it and 'end_time' in it:
                # 存在开始结束毫秒数值
                startraw = ms_to_time_string(ms=it['start_time'])
                endraw = ms_to_time_string(ms=it['end_time'])
            else:
                raise Exception(
                    tr("There is no time/startraw/start_time in the subtitle in any valid timestamp form."))
        else:
            # 存在单独开始和结束  时:分:秒,毫秒 字符串
            startraw = it['startraw']
            endraw = it['endraw']

        txt += f"{line}\n{startraw} --> {endraw}\n{it['text']}\n\n"
    return txt


def set_ass_font(srtfile: str) -> str:
    """
    将 JSON_FILE 中的样式覆盖到指定 ASS 文件的 [V4+ Styles] 区域，并保存回原文件。
    
    Args:
        ass_file_path: ASS 文件的完整绝对路径（字符串）
    
    Returns:
        ass_file_path: 传入的 ASS 文件路径（无论成功或失败都返回）
    
    行为：
        - 读取 JSON_FILE 获取最新样式
        - 读取 ass_file_path 内容
        - 替换 [V4+ Styles] 区块（保留 Format 行，替换 Style 行）
        - 若 JSON_FILE 不存在或解析失败，静默打印原因
        - 若 ASS 文件不存在或写入失败，静默打印原因
        - 最后始终返回 ass_file_path
    """
    
    from . import help_ffmpeg

    if not os.path.exists(srtfile) or os.path.getsize(srtfile) == 0:
        return os.path.basename(srtfile)

    # 将 text 中的\n替换为\N
    srt_str=""    
    for it in get_subtitle_from_srt(srtfile,is_file=True):
        t=re.sub(r'\n|\\n',r'\\N',it['text'])
        srt_str+=f'{it["line"]}\n{it["startraw"]} --> {it["endraw"]}\n{t}\n\n' 
    edit_srt=srtfile[:-4]+'-edit.srt'
    with open(edit_srt,'w',encoding='utf-8') as f:
        f.write(srt_str.strip())
    ass_file_path = f'{srtfile[:-3]}ass'
    help_ffmpeg.runffmpeg(['-y', '-i', edit_srt, ass_file_path])

    # 1. 验证 ASS 文件是否存在
    if not os.path.exists(ass_file_path):
        logger.warning(f"[export_style] 错误：ASS 文件不存在: {ass_file_path}")
        return ass_file_path

    # 2. 读取 JSON 样式
    JSON_FILE=f'{ROOT_DIR}/videotrans/ass.json'
    if not os.path.exists(JSON_FILE):
        logger.debug(f"[export_style] 警告：JSON 配置文件不存在: {JSON_FILE}，跳过样式替换")
        return ass_file_path

    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            style = json.load(f)
    except Exception as e:
        logger.exception(f"[export_style] 错误：无法读取或解析 JSON 文件 {JSON_FILE}: {e}",exc_info=True)
        return ass_file_path

    # 3. 构建新的 Style 行
    try:
        new_style_line = (
            f"Style: {style.get('Name', 'Default')},"
            f"{style.get('Fontname', 'Arial')},"
            f"{style.get('Fontsize', 16)},"
            f"{style.get('PrimaryColour', '&H00FFFFFF&')},"
            f"{style.get('SecondaryColour', '&H00FFFFFF&')},"
            f"{style.get('OutlineColour', '&H00000000&')},"
            f"{style.get('BackColour', '&H00000000&')},"
            f"{style.get('Bold', 0)},"
            f"{style.get('Italic', 0)},"
            f"{style.get('Underline', 0)},"
            f"{style.get('StrikeOut', 0)},"
            f"{style.get('ScaleX', 100)},"
            f"{style.get('ScaleY', 100)},"
            f"{style.get('Spacing', 0)},"
            f"{style.get('Angle', 0)},"
            f"{style.get('BorderStyle', 1)},"
            f"{style.get('Outline', 1)},"
            f"{style.get('Shadow', 0)},"
            f"{style.get('Alignment', 2)},"
            f"{style.get('MarginL', 10)},"
            f"{style.get('MarginR', 10)},"
            f"{style.get('MarginV', 10)},"
            f"{style.get('Encoding', 1)}\n"
        )
    except Exception as e:
        logger.exception(f"[export_style] 错误：构建 Style 行失败: {e}",exc_info=True)
        return ass_file_path

    # 4. 读取 ASS 文件内容
    try:
        with open(ass_file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
    except Exception as e:
        logger.exception(f"[export_style] 错误：无法读取 ASS 文件: {e}",exc_info=True)
        return ass_file_path

    # 5. 正则替换 [V4+ Styles] 区块
    # 匹配 [V4+ Styles] 开始，到下一个 [ 或文件结尾，中间包含 Format 和 Style 行
    pattern = r'(^\[V4\+ Styles\]\s*\r?\n' \
              r'Format:[^\r\n]*\r?\n' \
              r'(?:Style:[^\r\n]*\r?\n)*)' \
              r'(?=\[|$)'

    def replacer(match):
        format_line = None
        for line in match.group(0).splitlines():
            if line.strip().startswith("Format:"):
                format_line = line.strip() + "\n"
                break
        if not format_line:
            format_line = "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        
        return f"[V4+ Styles]\n{format_line}{new_style_line}"

    try:
        new_content, count = re.subn(pattern, replacer, content, flags=re.MULTILINE)
    except Exception as e:
        logger.exception(f"[export_style] 错误：正则替换失败: {e}",exc_info=True)
        return ass_file_path

    # 6. 写回文件
    try:
        with open(ass_file_path, 'w', encoding='utf-8-sig', newline='') as f:
            f.write(new_content)
    except Exception as e:
        logger.exception(f"[export_style] 错误：无法写入 ASS 文件: {e}",exc_info=True)


    return ass_file_path


# 简单换行，不保留换行符，用于视频翻译字幕嵌入
def simple_wrap(text,maxlen=15,language="en"):
    # 标点和空格列表
    flag = [
        ",", ".", "?", "!", ";",
        "，", "。", "？", "；", "！", " "
    ]
    text=re.sub(r"\r?(\n|\\n)",' ',text,flags=re.I).strip()
    _len=len(text)
    if _len<maxlen+4:
        return text
    #如果是中日韩粤语等无需空格的语言
    text_lilst=[]
    current_text=""
    offset=2 if language[:2] in ['zh','ja','ko','yue'] else 8
    maxlen=max(3,maxlen)
    offset=min(offset,maxlen//2)

    i=0
    while i <_len:
        current_text=current_text.lstrip()
        if i>=_len-offset:
            # 最后不足4个字符，无需区分都给最后一行
            current_text+=text[i:]
            # print(f'最后不足4个字符')
            break
        if len(current_text)<maxlen-offset:
            current_text+=text[i]
            i+=1
            # print('正常追加')
            continue
        #判断 i+1,i+2,i+3,i+4 是否符合标点，
        if maxlen-offset<=len(current_text)<=maxlen and text[i] in flag:
            # 当前是标点，可以换行
            current_text+=text[i]
            # print(f'在 maxlen-offset 和 maxlen 之间换行 {text[i]=}')
            i+=1
            text_lilst.append(current_text)
            current_text=''
            continue
        # 再判断后续4个是否符合换行条件
        raw_i=i
        for next_i in range(1,offset+1):
            if text[i+next_i] in flag:
                pos_i=i+next_i+1
                current_text+=text[i:pos_i]
                # print(f'在后边+offset处换号{next_i=},{pos_i=},{text[i:pos_i]=}')
                raw_i=pos_i

                text_lilst.append(current_text)
                current_text=''
                break
        if raw_i!=i:
            i=raw_i
            continue
        # 没有找到合适标点换行，强制换行
        current_text+=text[i]
        if len(current_text)>=maxlen:
            # print(f'offset+4处也没找到合适的,强制该处断行,{len(current_text)=} {text[i]=}')
            text_lilst.append(current_text)
            current_text=''
        i+=1

    if current_text and len(current_text)<maxlen/3:
        text_lilst[-1]+=current_text
    elif current_text:
        text_lilst.append(current_text)
    # print(f'{maxlen=},{offset=}')
    return "\n".join(text_lilst)

def textwrap(text, maxlen=15):
    """
    0. 如果text长度小于maxlen则直接返回。
    1. text预先移除所有换行符。
    2. 达到maxlen处，如果当前字符是标点，则在此分组。否则向后查找最多4个字符，
       在找到的第一个标点处分组。如果都未找到，则在maxlen处硬分割。
    3. 如果分组数大于1，且最后一组长度小于3，则将最后一组合并到前一组。
    4. 最后将所有分组使用换行符连接后返回。

    Args:
      text: 需要处理的输入字符串。
      maxlen: 每组的目标最大长度，默认为 15。

    Returns:
      处理过的、用换行符连接的字符串。
    """
    # 标点和空格列表
    flag = [
        ",", ".", "?", "!", ";",
        "，", "。", "？", "；", "！", " "
    ]

    # 1. 移除所有换行符
    text_string = text.strip() #replace('\n', ' ').replace('\r', ' ').strip()

    # 0. 如果文本长度小于等于 maxlen，直接返回
    if len(text_string) <= maxlen:
        return text_string

    groups = []
    # 保留原始换行
    for text in re.split(r'\n|\\n',text_string):
        text=text.strip()
        if not text:
            continue
        cursor = 0
        text_len = len(text)
        if text_len<=maxlen:
            groups.append(text)
            continue

        while cursor < text_len:
            # 如果剩余文本不足 maxlen，则全部作为最后一组
            if text_len - cursor <= maxlen:
                groups.append(text[cursor:])
                break

            # 2. 智能分组逻辑
            break_point = -1

            # 确定查找标点的范围，从 maxlen 位置开始，向后最多看4个字符
            # 例如 maxlen=15, cursor=0, 则查找索引为 15, 16, 17 的字符
            search_range = range(max(cursor + maxlen-3,0), min(cursor + maxlen + 2, text_len))

            found_flag = False
            for i in search_range:
                if text[i] in flag:
                    # 找到标点，断点设置为标点之后
                    break_point = i + 1
                    found_flag = True
                    break

            # 如果在查找范围内没有找到标点，则在 maxlen 处硬分割
            if not found_flag:
                break_point = cursor + maxlen

            groups.append(text[cursor:break_point])
            cursor = break_point

    # 3. 如果分组大于1，并且最后一组长度小于3，则合并
    if len(groups) > 1 and len(groups[-1]) < 3:
        groups[-2] += groups[-1]
        groups.pop()

    return ("\n".join(groups)).strip()
