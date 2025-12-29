# 将普通文本转为合法的srt字符串
import copy
import os,json,re
import math
from collections import deque
from datetime import timedelta
from videotrans.configure.config import logs

"""
srt_autofix_module.py
Subtitle auto-fix module — single-file, entry signature preserved.

NEW FEATURES:
- min_duration_ms：分句最小时长
- max_duration_ms：分句最大时长
"""

import re
from typing import List, Dict
import os



CJK_RE = re.compile(r'[\u4e00-\u9fff]')


def is_cjk_text(text: str) -> bool:
    return bool(CJK_RE.search(text))


def weighted_len(text: str, cjk_weight: float = 1.25) -> float:
    cjk_count = sum(1 for ch in text if CJK_RE.match(ch))
    other_count = len(text) - cjk_count
    return cjk_count * cjk_weight + other_count


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


# -----------------------------------------------------
# Text splitting helpers
# -----------------------------------------------------
def split_by_punctuation_levels(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []

    strong = re.split(r'(?<=[。！？!?])\s*', text)
    strong = [s for s in strong if s.strip()]
    if len(strong) > 1:
        return strong

    weak = re.split(r'[;；,:，]\s*', text)
    weak = [s for s in weak if s.strip()]
    return weak if weak else [text]


def split_chinese_connectors(text: str) -> List[str]:
    connectors = [
        "然后", "但是", "不过", "然而", "因为", "所以", "比如", "例如", "如果", "而且",
        # 转折
        "可是", "只是", "尽管", "虽然", "即便", "反之", "这是","那么",
        # 因果/目的
        "因此", "因而", "由于", "既然", "从而", "于是", "为了", "由此可见",
        # 递进/并列
        "此外", "另外", "并且", "甚至", "况且", "再加上", "与此同时",
        # 时间/顺序
        "首先", "其次", "最后", "接着", "随后", "目前", "刚才", "后来", "起初", "当时","最近",
        # 假设/条件
        "只要", "只有", "除非",  "假如", "万一", "倘若",
        # 总结/解释
        "总之", "总而言之", "综上所述", "也就是说", "换句话说", "其实", "事实上", "显然",
        # 语气/副词
        "难道", "莫非", "反正", "也许", "居然", "竟然", "果然", "原来", "幸好",
        # 代词
        "大家", "我们", "他们"
    ]
    pattern = "(" + "|".join(map(re.escape, connectors)) + ")"
    parts = re.split(pattern, text)
    out = []
    buf = ""
    i = 0
    while i < len(parts):
        p = parts[i]
        if p in connectors:
            if buf:
                out.append(buf)
            buf = p
            i += 1
            if i < len(parts):
                buf += parts[i]
            out.append(buf)
            buf = ""
        else:
            if not buf:
                buf = p
            else:
                buf += p
            out.append(buf)
            buf = ""
        i += 1
    return [o.strip() for o in out if o.strip()] or [text]


def merge_short_frags(chunks: List[str], min_len_weight: float) -> List[str]:
    if len(chunks) <= 1:
        return chunks

    out = []
    i = 0
    while i < len(chunks):
        cur = chunks[i]

        if weighted_len(cur) < min_len_weight and i + 1 < len(chunks):
            merged = (cur + " " + chunks[i+1]).strip()
            out.append(merged)
            i += 2
        else:
            out.append(cur)
            i += 1
    return out


def hard_cut_cjk_text(text: str, target_weight: float = 28.0) -> List[str]:
    if weighted_len(text) <= target_weight:
        return [text]

    frags = []
    buf = ""
    cur = 0
    for ch in text:
        w = 1.25 if CJK_RE.match(ch) else 1
        if cur + w > target_weight and buf:
            frags.append(buf)
            buf = ch
            cur = w
        else:
            buf += ch
            cur += w
    if buf:
        frags.append(buf)

    return merge_short_frags(frags, min_len_weight=10)


def hard_cut_non_cjk_text(text: str, max_chars: int = 46) -> List[str]:
    words = text.split()
    frags = []
    buf = []
    for w in words:
        tmp = " ".join(buf + [w])
        if len(tmp) > max_chars and buf:
            frags.append(" ".join(buf))
            buf = [w]
        else:
            buf += [w]
    if buf:
        frags.append(" ".join(buf))

    return merge_short_frags(frags, min_len_weight=10)


# -----------------------------------------------------
# Duration distribution
# -----------------------------------------------------
def enforce_duration_range(pieces: List[Dict], min_ms: int, max_ms: int) -> List[Dict]:
    """Ensure each piece duration is within [min_ms, max_ms]."""

    # 1) merge too short pieces upward
    merged = []
    buf = None
    for p in pieces:
        dur = p["end_time"] - p["start_time"]
        if dur >= min_ms:
            if buf:
                merged.append(buf)
                buf = None
            merged.append(p)
        else:
            # merge with next later
            if buf is None:
                buf = p
            else:
                # expand buf
                buf = {
                    "start_time": buf["start_time"],
                    "end_time": p["end_time"],
                    "text": buf["text"] + " " + p["text"]
                }
    if buf:
        merged.append(buf)

    # 2) split pieces > max_ms
    final = []
    for m in merged:
        s = m["start_time"]
        e = m["end_time"]
        dur = e - s
        text = m["text"]

        if dur <= max_ms:
            final.append(m)
        else:
            # too long, need hard cut
            if is_cjk_text(text):
                frags = hard_cut_cjk_text(text, target_weight=28)
            else:
                frags = hard_cut_non_cjk_text(text)

            total_weight = sum(weighted_len(f) for f in frags)
            cur = s
            acc = 0

            for i, f in enumerate(frags):
                if i == len(frags) - 1:
                    ndur = e - cur
                else:
                    ndur = max(min_ms, int(dur * weighted_len(f) / total_weight))
                    acc += ndur

                final.append({
                    "start_time": cur,
                    "end_time": cur + ndur,
                    "text": f
                })
                cur += ndur

    return final


# -----------------------------------------------------
# reorder & format
# -----------------------------------------------------
def reorder_and_format(final_list: List[Dict]) -> List[Dict]:
    final_list = sorted(final_list, key=lambda x: x["start_time"])

    out = []
    prev_end = None
    for item in final_list:
        s = int(item["start_time"])
        e = int(item["end_time"])
        t = item.get("text", "").strip()
        if not t:
            continue

        if prev_end is not None and s < prev_end:
            s = prev_end
        if e <= s:
            e = s

        out.append({
            "line": len(out) + 1,
            "start_time": s,
            "end_time": e,
            "text": t,
            "startraw": ms_to_time_string(ms=s),
            "endraw": ms_to_time_string(ms=e),
            "time": f"{ms_to_time_string(ms=s)} --> {ms_to_time_string(ms=e)}"
        })
        prev_end = e
    return out


# -----------------------------------------------------
# Entry function (signature preserved)
# -----------------------------------------------------
def auto_fix_srtdict(
    srt_dict_list: List[Dict],
    language: str = "zh",
    use_jieba: bool = True,
    min_duration_ms: int = 600
) -> List[Dict]:
    from videotrans.configure import config
    import jieba
    is_cjk_lang = language.lower() in ["zh", "ja", "ko", "cmn", "yue"]

    max_duration_ms=int(float(config.settings.get("max_speech_duration_s",5))*1000)

    # 1. Clean input
    cleaned = []
    for x in srt_dict_list:
        st = int(x.get("start_time", 0))
        et = int(x.get("end_time", st + 100))
        if et <= st:
            et = st + 100

        text = clean_text_for_srtdict(x.get("text", "") or "")
        if not text:
            continue

        cleaned.append({
            "start_time": st,
            "end_time": et,
            "text": text
        })

    if not cleaned:
        return []

    cleaned.sort(key=lambda x: x["start_time"])

    # 2. Merge extremely close blocks
    merged = []
    buf = cleaned[0]
    for nxt in cleaned[1:]:
        if nxt["start_time"] - buf["end_time"] <= 80:
            buf = {
                "start_time": buf["start_time"],
                "end_time": nxt["end_time"],
                "text": buf["text"] + " " + nxt["text"]
            }
        else:
            merged.append(buf)
            buf = nxt
    merged.append(buf)

    # 3. Split blocks
    pieces = []
    for block in merged:
        st, et, text = block["start_time"], block["end_time"], block["text"]
        dur = et - st

        # short enough
        if dur <= max_duration_ms and weighted_len(text) <= (30 if is_cjk_lang else 60):
            pieces.append(block)
            continue

        # punctuation
        parts = split_by_punctuation_levels(text)
        if len(parts) > 1:
            parts = merge_short_frags(parts, min_len_weight=8)
            weight = sum(weighted_len(p) for p in parts)
            cur = st
            for i, p in enumerate(parts):
                if i == len(parts) - 1:
                    ndur = et - cur
                else:
                    ndur = max(min_duration_ms, int(dur * weighted_len(p) / weight))

                pieces.append({
                    "start_time": cur,
                    "end_time": cur + ndur,
                    "text": p
                })
                cur += ndur
            continue

        # CJK
        if is_cjk_text(text):
            # jieba optional
            if use_jieba:
                ws = list(jieba.cut(text))
                frags = []
                buf = ""
                for w in ws:
                    if weighted_len(buf + w) > 28 and buf:
                        frags.append(buf)
                        buf = w
                    else:
                        buf += w
                if buf:
                    frags.append(buf)

                frags = merge_short_frags(frags, min_len_weight=8)
                if len(frags) > 1:
                    weight = sum(weighted_len(f) for f in frags)
                    cur = st
                    for i, f in enumerate(frags):
                        if i == len(frags) - 1:
                            ndur = et - cur
                        else:
                            ndur = max(min_duration_ms, int(dur * weighted_len(f) / weight))
                        pieces.append({
                            "start_time": cur,
                            "end_time": cur + ndur,
                            "text": f
                        })
                        cur += ndur
                    continue

            # connectors
            conn = split_chinese_connectors(text)
            conn = merge_short_frags(conn, min_len_weight=8)
            if len(conn) > 1:
                weight = sum(weighted_len(f) for f in conn)
                cur = st
                for i, f in enumerate(conn):
                    if i == len(conn) - 1:
                        ndur = et - cur
                    else:
                        ndur = max(min_duration_ms, int(dur * weighted_len(f) / weight))
                    pieces.append({
                        "start_time": cur,
                        "end_time": cur + ndur,
                        "text": f
                    })
                    cur += ndur
                continue

            # hard cut
            frags = hard_cut_cjk_text(text)
            if len(frags) > 1:
                weight = sum(weighted_len(f) for f in frags)
                cur = st
                for i, f in enumerate(frags):
                    if i == len(frags) - 1:
                        ndur = et - cur
                    else:
                        ndur = max(min_duration_ms, int(dur * weighted_len(f) / weight))
                    pieces.append({
                        "start_time": cur,
                        "end_time": cur + ndur,
                        "text": f
                    })
                    cur += ndur
                continue

            pieces.append(block)
            continue

        # Non-CJK
        frags = hard_cut_non_cjk_text(text)
        if len(frags) > 1:
            weight = sum(len(f) for f in frags)
            cur = st
            for i, f in enumerate(frags):
                if i == len(frags) - 1:
                    ndur = et - cur
                else:
                    ndur = max(min_duration_ms, int(dur * len(f) / weight))
                pieces.append({
                    "start_time": cur,
                    "end_time": cur + ndur,
                    "text": f
                })
                cur += ndur
            continue

        pieces.append(block)

    # 4. enforce min/max duration
    pieces = enforce_duration_range(pieces, min_duration_ms, max_duration_ms)

    # 5. Final reorder + formatting
    return reorder_and_format(pieces)


# -----------------------------------------------------


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
                from videotrans.configure import config
                logs(e, level="except")
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
    from videotrans.configure._config_loader import tr
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
    from videotrans.configure import config
    if not os.path.exists(srtfile) or os.path.getsize(srtfile) == 0:
        return os.path.basename(srtfile)

    # 将 text 中的\n替换为\N
    srt_ass_str=""    
    for it in get_subtitle_from_srt(srtfile,is_file=True):
        t=re.sub(r'\n|\\n',r'\\N',it['text'])
        srt_ass_str+=f'{it["line"]}\n{it["startraw"]} --> {it["endraw"]}\n{t}\n\n' 
    with open(srtfile+".srt",'w',encoding='utf-8') as f:
        f.write(srt_ass_str.strip())
    help_ffmpeg.runffmpeg(['-y', '-i', srtfile+".srt", f'{srtfile}.ass'])
    ass_file_path = f'{srtfile}.ass'

    # 1. 验证 ASS 文件是否存在
    if not os.path.exists(ass_file_path):
        logs(f"[export_style] 错误：ASS 文件不存在: {ass_file_path}")
        return ass_file_path

    # 2. 读取 JSON 样式
    JSON_FILE=f'{config.ROOT_DIR}/videotrans/ass.json'
    if not os.path.exists(JSON_FILE):
        logs(f"[export_style] 警告：JSON 配置文件不存在: {JSON_FILE}，跳过样式替换")
        return ass_file_path

    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            style = json.load(f)
    except Exception as e:
        logs(f"[export_style] 错误：无法读取或解析 JSON 文件 {JSON_FILE}: {e}")
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
        logs(f"[export_style] 错误：构建 Style 行失败: {e}")
        return ass_file_path

    # 4. 读取 ASS 文件内容
    try:
        with open(ass_file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
    except Exception as e:
        logs(f"[export_style] 错误：无法读取 ASS 文件: {e}")
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
        logs(f"[export_style] 错误：正则替换失败: {e}")
        return ass_file_path

    # 6. 写回文件
    try:
        with open(ass_file_path, 'w', encoding='utf-8-sig', newline='') as f:
            f.write(new_content)
        logs(f"[export_style] 成功：样式已更新到 {ass_file_path}")
    except Exception as e:
        logs(f"[export_style] 错误：无法写入 ASS 文件: {e}")

    return ass_file_path


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
