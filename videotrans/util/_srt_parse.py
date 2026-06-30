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
    res_text = re.sub(r'([，。！？,.?]\s?){2,}', ',', res_text, flags=re.I | re.S)
    return res_text


def delete_punc(text):
    pattern = r'[,?/;\':，。？、：；！!""''"()（）]+|(?<!\d)\.|\.(?!\d)'
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
    ms = f'{int(ms):03}'[-3:]
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
                text="\n".join(content)
            )
        ]
    return result


def get_srt_from_list(srt_list: List[SrtItem]) -> str:
    txt = ""
    line = 0
    for it in srt_list:
        line += 1
        if "startraw" not in it or not it['startraw']:
            if 'time' in it:
                startraw, endraw = it['time'].strip().split(" --> ")
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
