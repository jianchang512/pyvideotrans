import json

import whisper
from faster_whisper import WhisperModel,BatchedInferencePipeline
'''
model = WhisperModel(
            './models/models--Systran--faster-whisper-tiny',
            device='cpu',
        )
segments, info=model.transcribe(
            '60.wav',
            vad_filter=True,
            word_timestamps=True,
            #without_timestamps=False,
            language="zh",
        )

print(f'{info.language=}')
srts=[]
texts=[]
for segment in segments:
    texts.append({
        "text":segment.text,
        "start":segment.start,
        "end":segment.end,
        "words":[{ 'word': it.word, 'start': it.start,'end': it.end}for it in segment.words]
    })


#print(json.dumps(texts,indent=4,ensure_ascii=False))
'''

model = whisper.load_model(
            'tiny',
            device='cpu',
            download_root="./models"
        )
segments = model.transcribe(
                '60.wav',
                language='zh',
                #clip_timestamps=speech_timestamps_flat,
                word_timestamps=True,
            )

print(segments['language'])

texts=[]
for segment in segments['segments']:
    texts.append({
        "text":segment['text'],
        "start":segment['start'],
        "end":segment['end'],
        "words":[{ 'word': it['word'], 'start': it['start'],'end': it['end']}for it in segment['words']]
    })
for it in texts:
    print(f'{it["start"]}-{it["end"]} {it["text"]}')


import re

import re

def resegment_fun(texts, language, max_speech_ms):
    """
    仅针对过长的 Whisper 识别结果重新断句，并格式化为 SRT 字幕格式。
    保留 Whisper 原本正常的短句，不对其进行全局拉平。
    """

    # --- 辅助函数：将毫秒转换为 SRT 标准时间格式 HH:MM:SS,mmm ---
    def format_srt_time(ms_time):
        ms_time = int(ms_time)
        seconds, milliseconds = divmod(ms_time, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    # --- 语言连接规则与标点判定 ---
    # 东方中日韩等语言通常无需空格，其他字母系语言需空格
    no_space_langs = {'zh', 'ja', 'th', 'yue', 'ko'}
    use_space = language.lower() not in no_space_langs

    end_punc = set('.?!。？！\n')
    comma_punc = set(',;:，；：、')

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

    # --- 核心逻辑 ---
    final_segments = []

    for segment in texts:
        seg_start_ms = float(segment.get('start', 0)) * 1000
        seg_end_ms = float(segment.get('end', 0)) * 1000
        seg_duration = seg_end_ms - seg_start_ms
        words = segment.get('words', [])

        # 1. 如果该句话时长未超过 max_speech_ms，或者没有 words 数据可供细分
        # 直接原样保留该句，不破坏 Whisper 原有断句结构
        if seg_duration <= max_speech_ms or not words:
            final_segments.append({
                'text': segment.get('text', '').strip(),
                'start': seg_start_ms,
                'end': seg_end_ms
            })
            continue

        # 2. 如果该句话超长，则必须进入其内部使用 words 进行重新局部切分
        current_chunk = []
        chunk_start_ms = None
        prev_word_end_ms = None
        prev_word_text = ""

        for w in words:
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
            if future_duration > max_speech_ms and len(current_chunk) > 0:
                should_split = True
            else:
                # 弹性切断：在不超时的前提下，寻找标点或明显的语音停顿
                pause_ms = w_start_ms - prev_word_end_ms if prev_word_end_ms is not None else 0
                current_duration = prev_word_end_ms - chunk_start_ms if prev_word_end_ms else 0

                if len(current_chunk) > 0:
                    # 遇到强标点结束
                    if has_punc(prev_word_text, end_punc):
                        should_split = True
                    # 遇到明显的长静音停顿 (>= 800ms)
                    elif pause_ms >= 800:
                        should_split = True
                    # 遇到短停顿 (>= 300ms) 且伴随逗号等弱标点
                    elif has_punc(prev_word_text, comma_punc) and pause_ms >= 300:
                        should_split = True
                    # 为了防止有些长句既没标点也没大停顿，如果时长已经过半，遇到个中等停顿(>=400ms)也果断切
                    elif current_duration > (max_speech_ms * 0.5) and pause_ms >= 400:
                        should_split = True

            if should_split:
                # 结算当前子句
                final_segments.append({
                    'text': build_text(current_chunk),
                    'start': chunk_start_ms,
                    'end': prev_word_end_ms
                })
                # 将当前词作为下一个新子句的开头
                current_chunk = [w_text]
                chunk_start_ms = w_start_ms
            else:
                # 不切断，把词吸纳进当前子句
                current_chunk.append(w_text)

            prev_word_end_ms = w_end_ms
            prev_word_text = w_text

        # 遍历完该句的所有 words 后，将残存的词组收尾
        if current_chunk:
            final_segments.append({
                'text': build_text(current_chunk),
                'start': chunk_start_ms,
                'end': prev_word_end_ms
            })

    # --- 3. 组装输出：封装为指定的 SRT 字典列表格式 ---
    srt_output = []
    for idx, seg in enumerate(final_segments):
        start_ms = int(seg['start'])
        end_ms = int(seg['end'])

        start_raw = format_srt_time(start_ms)
        end_raw = format_srt_time(end_ms)

        srt_output.append({
            "line": idx + 1,
            "text": seg['text'],
            "start_time": start_ms,
            "end_time": end_ms,
            "startraw": start_raw,
            "endraw": end_raw,
            "time": f"{start_raw} --> {end_raw}"
        })

    return srt_output
ends=resegment_fun(texts,'zh',5000)
for it in ends:
    print(f'{it["time"]} {it["text"]}')


print(segments['language'])