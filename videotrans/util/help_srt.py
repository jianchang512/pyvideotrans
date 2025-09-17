# 将普通文本转为合法的srt字符串
import copy
import os
import re
from datetime import timedelta


def process_text_to_srt_str(input_text: str):
    if is_srt_string(input_text):
        return input_text

    # 将文本按换行符切割成列表
    text_lines = [line.strip() for line in input_text.replace("\r", "").splitlines() if line.strip()]

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
    text_lines = input_text.replace("\r", "").splitlines()
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
    res_text = text.replace('&#39;', "'").replace('&quot;', '"').replace("\u200b", " ").strip()
    # 删掉连续的多个标点符号，只保留一个
    res_text = re.sub(r'([，。！？,.?]\s?){2,}', ',', res_text)
    if not res_text or not remove_start_end:
        return res_text
    if res_text[-1] in ['，', ',']:
        res_text = res_text[:-1]
    if res_text and res_text[0] in ['，', ',']:
        res_text = res_text[1:]
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

    time_string = f"{hours}:{minutes}:{seconds},{milliseconds}"
    return format_time(time_string, f'{sepflag}')


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
            text = re.sub(r'</?[a-zA-Z]+>', '', text.replace("\r", '').strip())
            text = re.sub(r'\n{2,}', '\n', text).strip()
            if text and text[0] in ['-']:
                text = text[1:]
            if text and len(text) > 0 and text[-1] in ['-', ']']:
                text = text[:-1]
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
        except Exception as e:
            try:
                with open(file, 'r', encoding='gbk') as f:
                    content = f.read().strip()
            except Exception as e:
                from videotrans.configure import config
                config.logger.exception(e, exc_info=True)
        return content

    if is_file:
        content = _readfile(srtfile)
    else:
        content = srtfile.strip()

    if len(content) < 1:
        raise Exception(f"srt is empty:{srtfile=},{content=}")
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
    from videotrans.configure import config
    txt = ""
    line = 0
    # it中可能含有完整时间戳 it['time']   00:00:01,123 --> 00:00:12,345
    # 开始和结束时间戳  it['startraw']=00:00:01,123  it['endraw']=00:00:12,345
    # 开始和结束毫秒数值  it['start_time']=126 it['end_time']=678
    for it in srt_list:
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
                    f'字幕中不存在 time/startraw/start_time 任何有效时间戳形式' if config.defaulelang == 'zh' else 'There is no time/startraw/start_time in the subtitle in any valid timestamp form.')
        else:
            # 存在单独开始和结束  时:分:秒,毫秒 字符串
            startraw = it['startraw']
            endraw = it['endraw']

        txt += f"{line}\n{startraw} --> {endraw}\n{it['text']}\n\n"
    return txt


def set_ass_font(srtfile=None):
    from . import help_ffmpeg
    from videotrans.configure import config
    if not os.path.exists(srtfile) or os.path.getsize(srtfile) == 0:
        return os.path.basename(srtfile)
    help_ffmpeg.runffmpeg(['-y', '-i', srtfile, f'{srtfile}.ass'])
    assfile = f'{srtfile}.ass'

    with open(assfile, 'r', encoding='utf-8') as f:
        ass_str = f.readlines()

    for i, it in enumerate(ass_str):
        if it.find('Style: ') == 0:
            ass_str[
                i] = 'Style: Default,{fontname},{fontsize},{fontcolor},{fontcolor},{fontbordercolor},{backgroundcolor},0,0,0,0,100,100,0,0,{borderstyle},{outline},{shadow},{subtitle_position},{marginL},{marginR},{marginV},1'.format(
                fontname=config.settings['fontname'],
                fontsize=config.settings['fontsize'],
                fontcolor=config.settings['fontcolor'],
                fontbordercolor=config.settings['fontbordercolor'],
                backgroundcolor=config.settings['backgroundcolor'],
                borderstyle=int(config.settings.get('borderStyle', 1)),  # 1轮廓风格，3背景色块风格
                outline=config.settings.get('outline', 1),
                shadow=config.settings.get('shadow', 1),
                subtitle_position=int(config.settings.get('subtitle_position', 2)),
                marginL=int(config.settings.get('marginL', 10)),
                marginR=int(config.settings.get('marginR', 10)),
                marginV=int(config.settings.get('marginV', 10))
            )
        elif it.find('Dialogue: ') == 0:
            ass_str[i] = it.replace('  ', '\\N')

    with open(assfile, 'w', encoding='utf-8') as f:
        f.write("".join(ass_str))
    return assfile

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
    text = text.replace('\n', '').replace('\r', '')

    # 0. 如果文本长度小于等于 maxlen，直接返回
    if len(text) <= maxlen:
        return text

    groups = []
    cursor = 0
    text_len = len(text)

    while cursor < text_len:
        # 如果剩余文本不足 maxlen，则全部作为最后一组
        if text_len - cursor <= maxlen:
            groups.append(text[cursor:])
            break

        # 2. 智能分组逻辑
        break_point = -1

        # 确定查找标点的范围，从 maxlen 位置开始，向后最多看4个字符
        # 例如 maxlen=15, cursor=0, 则查找索引为 15, 16, 17, 18, 19 的字符
        search_range = range(cursor + maxlen, min(cursor + maxlen + 5, text_len))

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

    return "\n".join(groups)
