# zh_recogn 识别
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union

import requests

from videotrans.configure import config
from videotrans.configure._except import NO_RETRY_EXCEPT, StopRetry
from videotrans.configure.config import tr
from videotrans.recognition._base import BaseRecogn
from videotrans.util import tools

"""
            请求发送：以二进制形式发送键名为 audio 的wav格式音频数据，采样率为16k、通道为1
            requests.post(api_url, files={"audio": open(audio_file, 'rb')},data={"language":2位语言代码})

            失败时返回
            res={
                "code":1,
                "msg":"错误原因"
            }

            成功时返回
            res={
                "code":0,
                "data":[
                    {
                        "text":"字幕文字",
                        "time":'00:00:01,000 --> 00:00:06,500'
                    },
                    {
                        "text":"字幕文字",
                        "time":'00:00:06,900 --> 00:00:12,200'
                    },
                ]
            }
"""
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type, before_log, after_log
import logging

RETRY_NUMS = 2
RETRY_DELAY = 10


@dataclass
class APIRecogn(BaseRecogn):

    def __post_init__(self):
        super().__post_init__()
        api_url = config.params.get('recognapi_url', '').strip().rstrip('/').lower()

        if not api_url.startswith('http'):
            api_url = f'http://{api_url}'

        if config.params.get('recognapi_key'):
            if '?' in api_url:
                api_url += f'&sk={config.params.get("recognapi_key", "")}'
            else:
                api_url += f'?sk={config.params.get("recognapi_key", "")}'

        self.api_url = api_url
        self._add_internal_host_noproxy(self.api_url)

    def _exec(self) -> Union[List[Dict], None]:
        if self._exit():  return
        if re.search(r'api\.gladia\.io', self.api_url, re.I):
            return self._whisperzero()
        if 'vibevoice-asr' in config.params.get('recognapi_key', ''):
            return self._vibevoice_asr()
        with open(self.audio_file, 'rb') as f:
            chunk = f.read()
        files = {"audio": chunk}
        self._signal(
            text=tr("Recognition may take a while, please be patient"))

        res = requests.post(f"{self.api_url}", data={"language": self.detect_language}, files=files, timeout=600)
        res.raise_for_status()
        content_type = res.headers.get('Content-Type')
        if 'application/json' in content_type:
            res = res.json()
            if "code" not in res or res['code'] != 0:
                raise RuntimeError(f'{res["msg"]}')
            if "data" not in res or len(res['data']) < 1:
                raise RuntimeError(f'识别出错{res=}')
            self._signal(
                text=tools.get_srt_from_list(res['data']),
                type='replace_subtitle'
            )
            return res['data']
        return tools.get_subtitle_from_srt(res.text, is_file=False)

    def _whisperzero(self):
        api_key = config.params.get("recognapi_key")
        if not api_key:
            raise StopRetry(tr("api key must be filled in"))
        # 上传 self.audio_file
        with open(self.audio_file, "rb") as f:
            audio_file = f.read()
        files = {
            "audio": (self.audio_file, audio_file, "audio/wav")  # Content-Type 音频类型，有些API需要特别指定
        }

        response = requests.post("https://api.gladia.io/v2/upload", files=files, headers={
            "x-gladia-key": api_key
        })
        response.raise_for_status()
        audio_url = response.json()['audio_url']

        payload = {
            "detect_language": True if not self.detect_language or self.detect_language == 'auto' else False,
            "enable_code_switching": False,
            "language": "" if not self.detect_language or self.detect_language == 'auto' else self.detect_language[:2],
            "subtitles": True,
            "subtitles_config": {
                "formats": ["srt"],
                "minimum_duration": 1,
                "maximum_duration": 15.5,
                "maximum_characters_per_row": 80,
                "maximum_rows_per_caption": 2,
                "style": "default"
            },
            "sentences": True,
            "punctuation_enhanced": True,
            "audio_url": audio_url
        }

        response = requests.request("POST", 'https://api.gladia.io/v2/pre-recorded', json=payload, headers={
            "x-gladia-key": api_key,
            "Content-Type": "application/json"
        })
        response.raise_for_status()
        id = response.json()['id']

        # 获取结果
        while 1:
            if config.exit_soft: return
            time.sleep(1)
            response = requests.get(f"https://api.gladia.io/v2/pre-recorded/{id}", headers={"x-gladia-key": api_key})
            response.raise_for_status()
            d = response.json()
            if d['status'] == 'error':
                config.logger.warning(d)
                raise StopRetry(f"Error:{d['error_code']}")
            if d['status'] == 'done':
                config.logger.info(d)
                sens = d['result']['transcription']['subtitles'][0]['subtitles']
                raws = tools.get_subtitle_from_srt(sens, is_file=False)
                if self.detect_language and self.detect_language[:2] in ['zh', 'ja', 'ko']:
                    for i, it in enumerate(raws):
                        text = re.sub(r'\s+', '', it['text'], flags=re.I | re.S)
                        raws[i]['text'] = text
                return raws

    def _vibevoice_asr(self):
        from gradio_client import Client, handle_file
        from pydub import AudioSegment
        import re
        import ast
        import os
        import math
        import json
        from pathlib import Path

        # 定义切片时长 (60分钟 = 60 * 60 * 1000 毫秒)
        CHUNK_DURATION_MS = 60 * 60 * 1000

        # 初始化客户端
        client = Client(self.api_url,httpx_kwargs={"timeout":7200})

        # 内部函数：处理单个片段的返回结果
        def _process_chunk_result(raw_text, time_offset_ms, start_line_index):
            # 1. 使用正则表达式找到列表部分
            match = re.search(r'(\[\{.*?\}\])', raw_text, re.DOTALL)
            chunk_raws = []
            chunk_speaker_raw_list = []  # 仅收集当前片段的原始说话人标记

            if not match:
                # 如果某个片段没识别出内容（可能是静音），返回空而不是报错
                config.logger.warning(f"No subtitles found in chunk starting at {time_offset_ms}ms")
                return [], []

            list_str = match.group(1)
            config.logger.debug(f'match.group(1)={list_str}')
            list_str=re.sub(r'^.*?\[\{','[{',list_str,flags=re.S)
            list_str=re.sub(r'\}\].*$','}]',list_str,flags=re.S)
            list_str=re.sub(r"\n?\n", '',list_str)
            config.logger.debug(f're.sub after:{list_str=}')
            segments=None
            try:
                segments=json.loads(list_str)
            except json.JSONDecodeError:
                try:
                    segments = ast.literal_eval(list_str)
                except (ValueError, SyntaxError):
                    context = {
                        "null": None, 
                        "true": True, 
                        "false": False,
                        "__builtins__": None
                    }
                    segments = eval(list_str, context)
            except Exception as e:
                config.logger.error(f"AST eval failed: {e}")
            if not segments:
                return [],[]

            # 2. 遍历结果并加上时间偏移
            for i, seg in enumerate(segments):
                # 计算加上偏移量后的毫秒数
                seg_start_ms = int(float(seg['Start']) * 1000) + time_offset_ms
                seg_end_ms = int(float(seg['End']) * 1000) + time_offset_ms

                tmp = {
                    "line": start_line_index + i + 1,  # 累加行号
                    "text": seg['Content'],
                    "start_time": seg_start_ms,
                    "end_time": seg_end_ms,
                }
                # [Noise]之类无有效信息
                if re.match(r'^\[[a-zA-Z0-9\s]+\]$',seg['Content'].strip()):
                    continue
                
                # 假设 tools 是你类外部或全局可访问的工具
                tmp['startraw'] = tools.ms_to_time_string(ms=tmp['start_time'])
                tmp['endraw'] = tools.ms_to_time_string(ms=tmp['end_time'])
                tmp['time'] = f"{tmp['startraw']} --> {tmp['endraw']}"

                chunk_raws.append(tmp)

                # 收集原始说话人信息 (例如 "Speaker 1")
                sp = seg.get("Speaker", '-')
                chunk_speaker_raw_list.append(sp)

            return chunk_raws, chunk_speaker_raw_list

        # self.audio_file 是 wav 路径
        audio = AudioSegment.from_wav(self.audio_file)
        total_duration = len(audio)

        final_raws = []
        all_speaker_raw_list = []  # 存储所有片段原本的说话人标记
        current_line = 0

        for i, start_ms in enumerate(range(0, total_duration, CHUNK_DURATION_MS)):
            end_ms = min(start_ms + CHUNK_DURATION_MS, total_duration)

            # 切割音频
            chunk_audio = audio[start_ms:end_ms]

            # 保存临时文件
            temp_chunk_path = os.path.join(self.cache_folder, f"temp_chunk_{i}.wav")
            chunk_audio.export(temp_chunk_path, format="wav")

            try:
                result = client.predict(
                    audio_input=handle_file(temp_chunk_path),
                    audio_path_input=None,
                    start_time_input=None,
                    end_time_input=None,
                    max_new_tokens=65536,
                    temperature=0,
                    top_p=1,
                    do_sample=False,
                    repetition_penalty=1,
                    context_info="",
                    api_name="/transcribe_audio"
                )

                # 处理返回结果，传入当前的 start_ms 作为时间偏移量
                config.logger.debug(f'vibevoice-asr:{result[0]=}')
                chunk_data, chunk_spk = _process_chunk_result(
                    result[0],
                    time_offset_ms=start_ms,
                    start_line_index=current_line
                )

                final_raws.extend(chunk_data)
                all_speaker_raw_list.extend(chunk_spk)
                current_line += len(chunk_data)

            except Exception as e:
                config.logger.exception(f"Error processing chunk {i}: {e}")
            finally:
                # 清理临时文件
                if os.path.exists(temp_chunk_path):
                    os.remove(temp_chunk_path)
        if not final_raws:
            raise RuntimeError(f'VibeVoice:{self.api_url} not return data:{result[0]}')
        # 统一处理说话人逻辑 (合并后的重排序)
        # 这里是将所有片段的说话人混在一起处理。
        # 警告：VibeVoice 是分段处理的，Chunk1 的 spk0 和 Chunk2 的 spk0 可能不是同一个人。

        final_speaker_list = []
        unique_speakers = []

        # 提取不重复的说话人列表保持顺序
        for sp in all_speaker_raw_list:
            if sp not in unique_speakers:
                unique_speakers.append(sp)

        if unique_speakers:
            try:
                # 生成最终的 spk0, spk1... 映射
                for sp in all_speaker_raw_list:
                    if sp == '-':
                        # 如果没有识别出，暂定为最后一个新编号
                        final_speaker_list.append(f'spk{len(unique_speakers)}')
                    else:
                        final_speaker_list.append(f'spk{unique_speakers.index(sp)}')

                # 写入最终的 speaker.json
                if final_speaker_list:
                    Path(f'{self.cache_folder}/speaker.json').write_text(json.dumps(final_speaker_list), encoding='utf-8')
            except Exception as e:
                config.logger.exception(f'说话人重排序出错，忽略{e}', exc_info=True)

        return final_raws
