import json, re
from videotrans.task.taskcfg import SrtItem
from typing import List, Dict, Any

from ._utils import _write_log

no_space_langs = {'zh', 'ja', 'th', 'yue', 'ko', 'km'}
end_punc = set('.?!。？！\n')
comma_punc = set(',;:，；：、')


# --- 辅助函数：将毫秒转换为 SRT 标准时间格式 HH:MM:SS,mmm ---
def format_srt_time(ms_time):
    ms_time = int(ms_time)
    seconds, milliseconds = divmod(ms_time, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def _remove_unwanted_characters(text: str) -> str:
    # 保留中文、日文、韩文、英文、数字和常见符号，去除其他字符
    allowed_characters = re.compile(r'<\|\w+\|>')
    return re.sub(allowed_characters, '', text)


"""
针对二次识别后 whisper 返回的字级时间戳
texts=[
{
    "text": 句子,
    "start": 开始秒,
    "end": 结束秒,
    "words": [{'word': 单词或单个字, 'start': 开始秒, 'end': 结束秒}...]
},
....
max_speech_ms=允许的最长时长ms
min_speech_ms=最短时长ms
language=语言代码，zh,ja,en等
"""


def _resegment2(texts: List[Dict[str, Any]], language: str, max_speech_ms: int, min_speech_ms: int, logs_file=None) -> \
List[Any]:
    if not texts:
        return []
    use_space = language.lower() not in no_space_langs
    _write_log(logs_file, json.dumps({"type": "logs", "text": f'Secondary Resegment:start'}))
    # --- 展平并标准化字词数据 (转为毫秒) ---
    all_words = []
    for item in texts:
        for w in item.get('words', []):
            word_text = str(w.get('word', ''))
            if not word_text:
                continue
            start_ms = int(round(float(w['start']) * 1000))
            end_ms = int(round(float(w['end']) * 1000))
            all_words.append({
                'word': word_text,
                'start_ms': start_ms,
                'end_ms': max(start_ms, end_ms)
            })

    if not all_words:
        return []

    raw_chunks = []
    cur_chunk = []
    _rc=int(max_speech_ms*0.3)

    for i, word in enumerate(all_words):
        if not word['word'].strip():continue
        if not cur_chunk:
            cur_chunk.append(word)
            continue

        prev_word = cur_chunk[-1]

        # 停顿与时长计算 (ms)
        gap_ms = max(0, word['start_ms'] - prev_word['end_ms'])
        cur_start = cur_chunk[0]['start_ms']
        cur_duration = prev_word['end_ms'] - cur_start
        new_duration = word['end_ms'] - cur_start

        # 标点判定
        prev_text = prev_word['word'].rstrip()
        has_end_punc = any(prev_text.endswith(p) for p in end_punc)
        has_comma_punc = any(prev_text.endswith(p) for p in comma_punc)

        split = False

        # 规则 A: 超过最大允许时长，强制在此切分 (Hard limit)
        # 明显的较长静音停顿 (>= 600ms)，属于天然断句点
        if new_duration >= (max_speech_ms+_rc) or gap_ms>=400:
            split = True
        # 规则 C: 达到最短时长要求后的断句优化 (优先按静音/标点)
        elif gap_ms >= 100 or has_end_punc or has_comma_punc:  # 遇到标点
            split = True
        elif not use_space and word['word'][0]==" ":
            split = True

        # 中日韩最后一个是空格，应在此分割并将当前词插入 raw_chunks
        if not split and not use_space and word['word'][-1]==" ":
            cur_chunk.append(word)
            raw_chunks.append(cur_chunk)
            cur_chunk=[]
            continue

        if split:
            raw_chunks.append(cur_chunk)
            cur_chunk = [word]
        else:
            cur_chunk.append(word)

    if cur_chunk:
        raw_chunks.append(cur_chunk)

    # --- 组装文本与生成 SrtItem ---
    def concat_words(words_list: List[Dict[str, Any]]) -> str:
        # 判断原始字是否自带空格（如 Whisper 英文词通常自带前导空格）
        has_leading_space = any(w['word'].startswith(' ') for w in words_list)
        if not use_space or has_leading_space:
            return "".join(w['word'] for w in words_list).strip()
        return " ".join(w['word'].strip() for w in words_list if w['word'].strip()).strip()

    srt_output = []
    for idx, chunk in enumerate(raw_chunks):
        start_ms = int(chunk[0]['start_ms'])
        end_ms = int(chunk[-1]['end_ms'])
        text = concat_words(chunk)

        start_raw = format_srt_time(start_ms)
        end_raw = format_srt_time(end_ms)
        # print(f'regsegment2: {(end_ms-start_ms)/1000.0}s')

        srt_output.append(SrtItem(**{
            "line": idx + 1,
            "text": text,
            "start_time": start_ms,
            "end_time": end_ms,
            "startraw": start_raw,
            "endraw": end_raw,
            "time": f"{start_raw} --> {end_raw}"
        }))
    return srt_output


"""
针对 whisper 模型返回的字级时间戳数据，根据静音和标点重新断句
"""


def _resegment(texts, language, max_speech_ms, min_speech_ms, logs_file=None) -> List[SrtItem]:
    if not texts: return []
    _write_log(logs_file, json.dumps({"type": "logs", "text": f'Resegment:start'}))
    # 最长可能句子: max_speech_ms + _rc + min_speech_ms
    # 最短句子: min_speech_ms
    _rc = 1500  # 超过 max_speech_ms + _rc ，强制分割
    _min_words = 1  # 大于该数量的词，才考虑分割

    # 东方中日韩等语言通常无需空格，其他字母系语言需空格
    use_space = language.lower() not in no_space_langs

    def has_punc(text, punc_set):
        if not text:
            return False
        return text[-1] in punc_set

    def build_text(chunk_words):
        if use_space:
            text_str = " ".join(chunk_words)
            # 修复字母语言由于空格连接导致的标点前导空格问题 (如 "Hello , world" -> "Hello, world")
            text_str = re.sub(r'\s+([.,?!:;])', r'\1', text_str)
        else:
            text_str = "".join(chunk_words)
        return text_str.strip()

    final_segments = []
    _block = 100 / len(texts)
    for seg_idx, segment in enumerate(texts):
        seg_start_ms = float(segment.get('start', 0)) * 1000
        seg_end_ms = float(segment.get('end', 0)) * 1000
        seg_duration = seg_end_ms - seg_start_ms
        words = segment.get('words', [])
        _c_percent = seg_idx * _block
        _write_log(logs_file, json.dumps({"type": "logs", "text": f'Resegment:{_c_percent:.2f}%'}))

        # 时间符合最大最小值，
        if min_speech_ms <= seg_duration <= (max_speech_ms + _rc):
            final_segments.append({
                'text': segment.get('text', '').strip(),
                'start': seg_start_ms,
                'end': seg_end_ms
            })
            continue
        # 前面一个句子太短， 强制和当前句子合并
        if final_segments and final_segments[-1]['end'] - final_segments[-1]['start'] < min_speech_ms:
            final_segments[-1]['text'] += (" " if use_space else "") + segment.get('text', '').strip()
            final_segments[-1]['end'] = seg_end_ms
            continue

        # 2. 如果该句话超长，则必须进入其内部使用 words 进行重新局部切分
        current_chunk = []
        chunk_start_ms = None
        prev_word_end_ms = None
        prev_word_text = ""

        for w_idx, w in enumerate(words):
            _c_percent += w_idx * (_block / len(words))
            _write_log(logs_file, json.dumps({"type": "logs", "text": f'Resegment:{_c_percent:.2f}%'}))
            w_text = w.get('word', '').strip()
            if not w_text:
                continue

            w_start_ms = float(w.get('start', 0)) * 1000
            w_end_ms = float(w.get('end', 0)) * 1000

            if chunk_start_ms is None:
                chunk_start_ms = w_start_ms

            # 预测：如果把当前词加入，当前子句的时长会是多少？
            future_duration = w_end_ms - chunk_start_ms

            # --- 判定是否需要切断 ---
            should_split = False

            # 强制切断：如果不切，加上这个词就会直接超时 (确保绝对 <= max_speech_ms)
            if future_duration >= (max_speech_ms + _rc) and len(current_chunk) > 0:
                should_split = True
            else:
                # 弹性切断：在不超时的前提下，寻找标点或明显的语音停顿
                pause_ms = w_start_ms - prev_word_end_ms if prev_word_end_ms is not None else 0
                current_duration = prev_word_end_ms - chunk_start_ms if prev_word_end_ms else 0

                # 至少个单词
                if len(current_chunk) >= _min_words and current_duration >= min_speech_ms:
                    # 遇到强标点结束
                    if has_punc(prev_word_text, end_punc):
                        should_split = True
                    # 遇到明显的长静音停顿 (>= 400ms)
                    elif pause_ms >= 400:
                        should_split = True
                    # 遇到短停顿 (>= 200ms) 且伴随逗号等弱标点
                    elif has_punc(prev_word_text, comma_punc) and pause_ms >= 200:
                        should_split = True
                    # 为了防止有些长句既没标点也没大停顿，如果时长已经过半，遇到个中等停顿(>=100ms)也果断切
                    elif current_duration > max(min_speech_ms, max_speech_ms * 0.5) and pause_ms >= 100:
                        should_split = True

            if should_split:
                # 结算当前子句
                _tmp = {
                    'text': build_text(current_chunk),
                    'start': chunk_start_ms,
                    'end': prev_word_end_ms
                }
                final_segments.append(_tmp)
                # 将当前词作为下一个新子句的开头
                current_chunk = [w_text]
                chunk_start_ms = w_start_ms
            else:
                # 不切断，把词吸纳进当前子句
                current_chunk.append(w_text)

            prev_word_end_ms = w_end_ms
            prev_word_text = w_text

        # 遍历完该句的所有 words 后，将残存的词组收尾
        # 是最后一个了，并且小于 min_speech_ms,则合并
        if current_chunk and seg_idx == len(texts) - 1 and prev_word_end_ms - chunk_start_ms < min_speech_ms:
            final_segments[-1]['end'] = prev_word_end_ms
            final_segments[-1]['text'] += (" " if use_space else "") + build_text(current_chunk)
        elif current_chunk:
            final_segments.append({
                'text': build_text(current_chunk),
                'start': chunk_start_ms,
                'end': prev_word_end_ms
            })

    _merged = []
    _len = len(final_segments)
    for idx, seg in enumerate(final_segments):
        _duration = seg['end'] - seg['start']
        # 第一个直接 append 或 当前大于最小，直接 append
        if not _merged or _duration >= min_speech_ms:
            _merged.append(seg)
            continue

        _last_duration = _merged[-1]['end'] - _merged[-1]['start']

        # _merged的最后一个超长时，并且当前不是final_segments最后一个时，直接插入
        if _last_duration >= max_speech_ms and idx < _len - 1:
            _merged.append(seg)
            continue

        # 其他情况合并进前面
        _merged[-1]['text'] += (' ' if use_space else '') + seg['text']
        _merged[-1]['end'] = seg['end']

    # 输出
    srt_output = []
    for idx, seg in enumerate(_merged):
        start_ms = int(seg['start'])
        end_ms = int(seg['end'])

        start_raw = format_srt_time(start_ms)
        end_raw = format_srt_time(end_ms)
        print(f'regsegment:{(end_ms-start_ms)/1000.0}s')

        srt_output.append(SrtItem(**{
            "line": idx + 1,
            "text": seg['text'],
            "start_time": start_ms,
            "end_time": end_ms,
            "startraw": start_raw,
            "endraw": end_raw,
            "time": f"{start_raw} --> {end_raw}"
        }))
    _write_log(logs_file, json.dumps({"type": "logs", "text": f'Resegment:ended'}))
    return srt_output
