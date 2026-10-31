# -*- coding: utf-8 -*-
import os, json, re
from datetime import timedelta
from functools import lru_cache
from typing import List, Union

from videotrans.configure.config import ROOT_DIR, tr, logger
from videotrans.task.taskcfg import SrtItem


@lru_cache
def process_text_to_srt_str(input_text: str) -> str:
    if is_srt_string(input_text):
        return input_text
    text_lines = [line.strip() for line in input_text.splitlines() if line.strip()]
    text_str_list = []
    for line in text_lines:
        if len(line) > 50:
            split_lines = re.split(r'(?<=[,.，。])', line)
            text_str_list.extend([l.strip() for l in split_lines if l.strip()])
        else:
            text_str_list.append(line)
    dict_list = []
    start_time_in_seconds = 0
    for i, text in enumerate(text_str_list, start=1):
        start_time = ms_to_time_string(seconds=start_time_in_seconds)
        end_time = ms_to_time_string(seconds=start_time_in_seconds + 1)
        start_time_in_seconds += 1
        dict_list.append(f"{i}\n{start_time} --> {end_time}\n{text}")
    return "\n\n".join(dict_list)


@lru_cache
def is_srt_string(input_text: str) -> bool:
    input_text = input_text.strip()
    if not input_text:
        return False
    text_lines = input_text.splitlines()
    if len(text_lines) < 3:
        return False
    first_line_pattern = r'^\d{1,2}$'
    second_line_pattern = r'^\s*?\d{1,2}:\d{1,2}:\d{1,2}(\W\d+)?\s*-->\s*\d{1,2}:\d{1,2}:\d{1,2}(\W\d+)?\s*$'
    if not re.match(first_line_pattern, text_lines[0].strip()) or not re.match(second_line_pattern,
                                                                                text_lines[1].strip()):
        return False
    return True


@lru_cache
def cleartext(text: str) -> str:
    res_text = text.replace('&#39;', "").replace('&quot;', '').replace("\u200b", " ").strip()
    res_text = re.sub(r'([，。！？,.?][^\S\n]?){2,}', ',', res_text, flags=re.I | re.S)
    return res_text


def delete_punc(text):
    pattern = r'''[,?/;:，。？、：；！!]+|(?<!\d)\.|\.(?!\d)'''
    res = re.sub(pattern, ' ', text)
    return re.sub(r'\s+', ' ', res).strip()


@lru_cache
def ms_to_time_string(*, ms: Union[int, float] = 0, seconds: Union[int, None] = None, sepflag: str = ',') -> str:
    if seconds is None:
        td = timedelta(milliseconds=ms)
    else:
        td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000
    return f"{hours:02}:{minutes:02}:{seconds:02}{sepflag}{milliseconds:03}"


@lru_cache
def format_time(s_time="", separate=',') -> str:
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
    ms = f'{int(str(ms).ljust(3, "0")[:3]):03}'
    return f"{hou}:{min}:{sec}{separate}{ms}"


def srt_str_to_listdict(srt_string: str) -> List[SrtItem]:
    srt_list = []
    time_pattern = r'\s?(\d+):(\d+):(\d+)([,.]\d+)?\s*?-{1,2}>\s*?(\d+):(\d+):(\d+)([,.]\d+)?\n?'
    lines = srt_string.splitlines()
    i = 0

    while i < len(lines):
        time_match = re.match(time_pattern, lines[i].strip())
        if time_match:
            start_time_groups = time_match.groups()[0:4]
            end_time_groups = time_match.groups()[4:8]

            def parse_time(time_groups):
                h, m, s, ms = time_groups
                # the fraction is a decimal part of the second: ",5" is 500 ms
                ms = ms[1:].ljust(3, '0')[:3] if ms else "0"
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
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""

                if re.match(time_pattern, next_line):
                    if re.fullmatch(r'\d+', current_line):
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
            text = re.sub(r'</?[a-zA-Z]+>', '', text.replace("\r", '').strip(), flags=re.I | re.S)
            text = re.sub(r'\n{2,}', '\n', text, flags=re.I | re.S).strip()
            _srtitem = SrtItem(
                line=len(srt_list) + 1,
                start_time=int(start_time),
                end_time=int(end_time),
                text=text if text else "",
            )
            _srtitem['startraw'] = ms_to_time_string(ms=_srtitem['start_time'])
            _srtitem['endraw'] = ms_to_time_string(ms=_srtitem['end_time'])
            _srtitem['time'] = f"{_srtitem['startraw']} --> {_srtitem['endraw']}"
            srt_list.append(_srtitem)
        else:
            i += 1

    return srt_list


def get_subtitle_from_srt(srtfile, *, is_file=True) -> List[SrtItem]:
    def _readfile(file):
        content = ""
        try:
            with open(file, 'r', encoding='utf-8-sig') as f:
                content = f.read().strip()
        except UnicodeDecodeError:
            try:
                with open(file, 'r', encoding='gbk') as f:
                    content = f.read().strip()
            except UnicodeDecodeError as e:
                logger.exception(e, exc_info=True)
                raise
        except BaseException:
            raise
        return content

    content = _readfile(srtfile) if is_file else srtfile.strip()

    if len(content) < 1:
        raise RuntimeError(
            f"The srt subtitles were not read. The file may be empty or the format does not conform to the SRT specification\n:{srtfile=}\n{content=}")

    try:
        result = srt_str_to_listdict(content)
    except Exception:
        result = srt_str_to_listdict(process_text_to_srt_str(content))

    if len(result) < 1:
        result = [
            SrtItem(
                line=1,
                start_time=0,
                startraw="00:00:00,000",
                end_time=2000,
                endraw="00:00:02,000",
                time="00:00:00,000 --> 00:00:02,000",
                text=content
            )
        ]
    return result


def get_srt_from_list(srt_list: List[SrtItem]) -> str:
    txt = ""
    line = 0
    for it in srt_list:
        line += 1
        if "startraw" not in it or not it['startraw']:
            _time_split=it['time'].strip().split(" --> ") if 'time' in it else []
            if len(_time_split)==2:
                startraw, endraw =_time_split[0],_time_split[1] 
                startraw = format_time(startraw.strip().replace('.', ','), ',')
                endraw = format_time(endraw.strip().replace('.', ','), ',')
            elif 'start_time' in it and 'end_time' in it:
                startraw = ms_to_time_string(ms=it['start_time'])
                endraw = ms_to_time_string(ms=it['end_time'])
            else:
                raise Exception(
                    tr("There is no time/startraw/start_time in the subtitle in any valid timestamp form."))
        else:
            startraw = it['startraw']
            endraw = it['endraw']

        txt += f"{line}\n{startraw} --> {endraw}\n{it['text']}\n\n"
    return txt



def ass_to_srt(src_ass_file, dst_srt_file, get_speaker=False):
    """将 ASS 字幕转为 SRT 字幕

    :param src_ass_file: 源 .ass 文件路径
    :param dst_srt_file: 输出 .srt 文件路径
    :param get_speaker: 是否提取说话人，若为 True 且存在说话人，则格式为 [说话人]字幕文本
    """

    def ass_time_to_srt_time(ass_time):
        """ASS时间戳转SRT时间戳

        ASS: H:MM:SS.cs (例: 0:01:05.12)
        SRT: HH:MM:SS,mmm (例: 00:01:05,120)
        """
        parts = ass_time.strip().split(":")
        h = int(parts[0])
        m = int(parts[1])
        s_parts = parts[2].split(".")
        s = int(s_parts[0])

        # 处理小数部分（ASS 通常为 2 位厘秒，SRT 为 3 位毫秒）
        cs = s_parts[1] if len(s_parts) > 1 else "0"
        cs = (cs + "00")[:2]  # 补齐或截断至2位厘秒
        ms = int(cs) * 10

        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    events = []
    in_events_section = False
    format_cols = []

    # 1. 解析 ASS 文件
    with open(src_ass_file, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # 检测 [Events] 区块
            if line.lower() == "[events]":
                in_events_section = True
                continue

            if in_events_section:
                # 如果遇到下一个区块，结束解析
                if line.startswith("[") and line.endswith("]"):
                    break

                # 获取字段列名结构
                if line.startswith("Format:"):
                    format_cols = [
                        col.strip().lower()
                        for col in line[len("Format:") :].split(",")
                    ]
                    continue

                # 解析每条字幕
                if line.startswith("Dialogue:"):
                    if not format_cols:
                        continue

                    # Text 字段本身可能包含逗号，因此按列数限制 split 切割次数
                    content = line[len("Dialogue:") :].strip()
                    values = content.split(",", len(format_cols) - 1)

                    if len(values) < len(format_cols):
                        continue

                    row = dict(zip(format_cols, values))

                    start = ass_time_to_srt_time(row.get("start", "0:00:00.00"))
                    end = ass_time_to_srt_time(row.get("end", "0:00:00.00"))
                    speaker = row.get("name", "").strip()
                    text = row.get("text", "")

                    # 去除 ASS 特效代码 (如 {\an8}, {\pos(100,200)} 等)
                    text = re.sub(r"\{.*?\}", "", text)
                    # 处理 ASS 换行符与硬空格
                    text = (
                        text.replace(r"\N", "\n")
                        .replace(r"\n", "\n")
                        .replace(r"\h", " ")
                    )
                    text = text.strip()

                    # 如果启用了 get_speaker 且有说话人名字，拼接到字幕前面
                    if get_speaker and speaker:
                        text = f"[{speaker}]{text}"

                    if text:  # 忽略纯绘图或空白字幕
                        events.append({"start": start, "end": end, "text": text})

    # 2. 按照起始时间重新排序，确保时间轴单调递增
    events.sort(key=lambda x: x["start"])

    # 3. 输出为 SRT 格式文件
    with open(dst_srt_file, "w", encoding="utf-8") as f:
        for index, event in enumerate(events, 1):
            f.write(f"{index}\n")
            f.write(f"{event['start']} --> {event['end']}\n")
            f.write(f"{event['text']}\n\n")