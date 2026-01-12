import difflib
import datetime
from faster_whisper import WhisperModel

def ms_to_srt_time(seconds):
    """将秒数转换为 SRT 格式 00:00:00,000"""
    if seconds is None:
        return "00:00:00,000"
    td = datetime.timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int(td.microseconds / 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def generate_aligned_srt_with_whisper(audio_file, target_text, model_size="tiny", device="cpu", compute_type="float32"):
    """
    使用 faster-whisper 获取时间轴，强制对齐到给定的纯文本中，生成 SRT。

    Args:
        audio_file (str): 音频文件路径
        target_text (str): 正确的纯文本内容（包含标点）
        model_size (str): whisper 模型大小 (base, small, medium, large-v3)
        device (str): 运行设备 'cuda' 或 'cpu'
        compute_type (str): 'float16' or 'int8'

    Returns:
        str: 生成的 SRT 字符串
    """

    print(f"1. 正在加载 Whisper 模型 ({model_size})...")
    try:
        model = WhisperModel("./models/models--Systran--faster-whisper-tiny", device=device, compute_type=compute_type)
    except Exception:
        print("警告: CUDA不可用或显存不足，自动切换回 CPU (速度较慢)...")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

    print("2. 正在识别音频以获取时间戳...")
    # 关键：开启 word_timestamps=True
    segments, info = model.transcribe(audio_file, word_timestamps=True, language="zh")

    # --- 第一步：提取 Whisper 结果为“字符-时间”序列 ---
    whisper_chars = [] # 存 {'char': '字', 'start': 0.1, 'end': 0.2}

    for segment in segments:
        for word in segment.words:
            # Whisper 的 word 可能是 "我们"，我们需要拆成 '我', '们' 并平分时间
            w_text = word.word.strip()
            if not w_text: continue

            duration = word.end - word.start
            char_duration = duration / len(w_text)

            for i, char in enumerate(w_text):
                whisper_chars.append({
                    'char': char,
                    'start': word.start + (i * char_duration),
                    'end': word.start + ((i + 1) * char_duration)
                })

    print(f"   Whisper 识别到 {len(whisper_chars)} 个字符。")

    # --- 第二步：准备目标文本序列 ---
    # 我们构建一个列表，保留原始文本的结构（包含标点），但用于对比时只看汉字/字母
    target_chars_map = []

    # 常见标点，用于断句
    punctuations = set(['，', '。', '？', '！', '；', '：', ',', '.', '?', '!', ';', ':'])

    comparison_target = [] # 纯净文本，用于和 Whisper 结果 diff

    for i, char in enumerate(target_text):
        is_punc = char in punctuations or char.strip() == ""
        entry = {
            'original_char': char,
            'is_punc': is_punc,
            'start': None,
            'end': None,
            'idx': i
        }
        target_chars_map.append(entry)

        if not is_punc:
            comparison_target.append(char)

    # --- 第三步：序列匹配 (核心逻辑) ---
    print("3. 正在执行文本强制对齐...")

    # 提取 Whisper 的纯字符文本用于对比
    comparison_whisper = [x['char'] for x in whisper_chars]

    # 使用 difflib 寻找最长公共子序列
    matcher = difflib.SequenceMatcher(None, comparison_target, comparison_whisper)

    # 用于记录 target 中哪些非标点字符被赋值了时间
    matched_indices = []

    # 遍历匹配块
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            # 这一段文本完全匹配，直接把 Whisper 的时间赋给 Target
            for k in range(i2 - i1):
                target_idx = -1
                # 找到 comparison_target[i1+k] 在 target_chars_map 中的位置
                #这比较麻烦，我们需要一个映射：comparison_target index -> target_chars_map index
                pass

    # 优化映射逻辑：
    # 建立 comparison_target 索引 -> target_chars_map 索引的映射
    comp_to_orig_map = []
    for idx, item in enumerate(target_chars_map):
        if not item['is_punc']:
            comp_to_orig_map.append(idx)

    # 重新遍历 opcodes 进行赋值
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            count = i2 - i1
            for k in range(count):
                # 原始文本的索引
                orig_idx = comp_to_orig_map[i1 + k]
                # Whisper 的索引
                whisper_idx = j1 + k

                target_chars_map[orig_idx]['start'] = whisper_chars[whisper_idx]['start']
                target_chars_map[orig_idx]['end'] = whisper_chars[whisper_idx]['end']
                matched_indices.append(orig_idx)

    # --- 第四步：时间插值 (填补未匹配的空洞) ---
    # 如果 Target 有字没匹配上 Whisper (tag != 'equal')，它的时间是 None
    # 我们需要根据前后已知的时间进行线性插值

    # 提取所有非标点项的索引
    non_punc_indices = [i for i, x in enumerate(target_chars_map) if not x['is_punc']]

    for i in range(len(non_punc_indices)):
        curr_real_idx = non_punc_indices[i]
        curr_item = target_chars_map[curr_real_idx]

        if curr_item['start'] is None:
            # 向前找最近的有时间的字
            prev_time = 0.0
            if i > 0:
                prev_real_idx = non_punc_indices[i-1]
                prev_end = target_chars_map[prev_real_idx]['end']
                if prev_end is not None:
                    prev_time = prev_end

            # 向后找最近的有时间的字
            next_time = None
            dist = 0
            for j in range(i + 1, len(non_punc_indices)):
                next_real_idx = non_punc_indices[j]
                if target_chars_map[next_real_idx]['start'] is not None:
                    next_time = target_chars_map[next_real_idx]['start']
                    dist = j - i
                    break

            if next_time is not None:
                # 线性插值
                duration_per_char = (next_time - prev_time) / (dist + 1)
                curr_item['start'] = prev_time
                curr_item['end'] = prev_time + duration_per_char
                # 更新 prev_time 以便下一次循环使用（虽然逻辑上这里只填当前的）
            else:
                # 后面没有匹配的字了（比如最后几个字没识别到），简单推算
                curr_item['start'] = prev_time
                curr_item['end'] = prev_time + 0.2 # 假设每个字0.2秒

    print("4. 正在生成 SRT 字幕...")

    # --- 第五步：按照标点符号断句并生成 SRT ---
    srt_parts = []
    srt_index = 1

    sentence_buffer = []
    line_start_time = None
    line_end_time = 0.0

    MAX_CHARS = 25 # 一行最多字数

    for idx, item in enumerate(target_chars_map):
        char = item['original_char']
        is_punc = item['is_punc']
        start = item['start']
        end = item['end']

        # 如果是空白字符且不是标点，跳过
        if char.strip() == "" and not is_punc:
            continue

        # 如果是字的开始
        if not is_punc and start is not None:
            if len(sentence_buffer) == 0:
                line_start_time = start
            line_end_time = end

        sentence_buffer.append(char)

        # 判断断句条件
        should_break = False
        if is_punc:
            should_break = True # 遇到标点强制换行
        elif len(sentence_buffer) >= MAX_CHARS:
            should_break = True # 字数超限换行
        elif idx == len(target_chars_map) - 1:
            should_break = True # 文本结束

        if should_break and sentence_buffer:
            # 过滤掉只有标点的行，或者没有时间的行
            text_line = "".join(sentence_buffer).strip()
            if text_line and line_start_time is not None:
                srt_parts.append(f"{srt_index}")
                srt_parts.append(f"{ms_to_srt_time(line_start_time)} --> {ms_to_srt_time(line_end_time)}")
                srt_parts.append(text_line)
                srt_parts.append("") # 空行

                srt_index += 1

            # 重置
            sentence_buffer = []
            line_start_time = None

    return "\n".join(srt_parts)

# ================= 使用示例 =================
if __name__ == "__main__":

    # 1. 你的音频文件
    wav_file = "./20.wav"

    # 2. 你的准确文本
    text_content = "古老星系中发现了有机分子，我们离第三类接触还有多远?韦博正式展开拍摄任务已经届满周年,最近也传来了许多过去难以拍摄到的照片。六月初，天文学家在《自然》期刊上发表了这张照片，在蓝色核心外，环绕着一圈橘黄色的光芒，这是一个星系规模的甜甜圈。"

    if 1: # 切换为True以执行
        try:
            srt_output = generate_aligned_srt_with_whisper(
                audio_file=wav_file,
                target_text=text_content,
                model_size="base" # 测试时用 base/small 速度快，正式用 medium/large-v3
            )

            print("-" * 30)
            print(srt_output)

            # 保存到文件
            with open("aligned_whisper.srt", "w", encoding="utf-8") as f:
                f.write(srt_output)

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"发生错误: {e}")
exit()
# taken from https://huggingface.co/pyannote/speaker-diarization-3.1 - see for more details
# instantiate the pipeline
import os,torch
from videotrans.configure import config
os.environ['HF_ENDPOINT']="https://hf-mirror.com"
from transformers import pipeline

class PunctuationRestorer:
    def __init__(self):
        # 初始化模型，建议在程序启动时执行一次，不要每次调用函数都重新加载
        print("正在加载标点模型，请稍候...")
        self.pipe = pipeline(
            "token-classification",
            model="oliverguhr/fullstop-punctuation-multilang-large",
            aggregation_strategy="none"  # 必须设为none，我们需要获取每个token的标签
        )
        print('加载完毕')


    def restore_punctuation(self, input_dict):
        """
        输入格式: { "key1": "sentence one", "key2": "sentence two" }
        输出格式: { "key1": "Sentence one.", "key2": "Sentence two." }
        """
        result_dict = {}

        for key, text in input_dict.items():
            if not text or not isinstance(text, str):
                result_dict[key] = text
                continue

            # 调用模型进行预测
            # distinct_colors=False 只是为了防止某些版本报warning，不影响逻辑
            predictions = self.pipe(text)

            # --- 核心还原逻辑 ---
            reconstructed_text = ""

            for item in predictions:
                print(f'{item=}')
                word = item['word']
                entity = item['entity']

                # 1. 处理 Token 本身
                # XLM-RoBERTa 的 token 通常包含前导空格（表示单词开头）
                # pipeline 输出时可能会保留特殊的 " " (U+2581) 字符，也可能转为普通空格
                # 我们将其统一替换为普通空格以防万一
                word = word.replace(' ', ' ')

                # 2. 处理标点标签
                # 该模型的标签含义： '0' 表示无标点，其他如 '.' ',' '?' 等表示该 token 后紧跟的标点
                punctuation = ""
                if entity != '0':
                    punctuation = entity

                # 3. 拼接到结果中
                reconstructed_text += word + punctuation

            # 4. 后处理
            # 去除首尾空格，并确保首字母大写（可选，视需求而定，这里仅做去空格）
            final_sentence = reconstructed_text.strip()

            # 可选：简单的首字母大写修正
            if final_sentence:
                final_sentence = final_sentence[0].upper() + final_sentence[1:]

            result_dict[key] = final_sentence

        return result_dict

# ================= 使用示例 =================

# 1. 初始化（只做一次）
restorer = PunctuationRestorer()

# 2. 准备数据
data = {
    "id_01": "hello world how are you today i am fine",
    "id_02": "das ist ein test text ohne satzzeichen",
    "id_03": "my name is clara and i live in berkeley california"
}

# 3. 执行处理
processed_data = restorer.restore_punctuation(data)

for i,it in processed_data.items():
    processed_data[i]=it.replace("▁",' ')

print(processed_data)
exit()
import pyannote.audio
torch.serialization.add_safe_globals([
    torch.torch_version.TorchVersion,
    pyannote.audio.core.task.Specifications,
    pyannote.audio.core.task.Problem,
    pyannote.audio.core.task.Resolution
])
from pyannote.audio import Pipeline
pipeline = Pipeline.from_pretrained(
  "Revai/reverb-diarization-v1",
  use_auth_token="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")

# run the pipeline on an audio file
diarization = pipeline("eng.wav")
for turn, _, speaker in diarization.itertracks(yield_label=True):
    print(f'{speaker=}')




exit()
#!/usr/bin/env python3

"""
This script shows how to add punctuations to text using sherpa-onnx Python API.

Please download the model from
https://github.com/k2-fsa/sherpa-onnx/releases/tag/punctuation-models

The following is an example

wget https://github.com/k2-fsa/sherpa-onnx/releases/download/punctuation-models/sherpa-onnx-punct-ct-transformer-zh-en-vocab272727-2024-04-12.tar.bz2
tar xvf sherpa-onnx-punct-ct-transformer-zh-en-vocab272727-2024-04-12.tar.bz2
rm sherpa-onnx-punct-ct-transformer-zh-en-vocab272727-2024-04-12.tar.bz2
"""

from pathlib import Path

import sherpa_onnx


def main():
    model = "./models/puntc/model.onnx"
    if not Path(model).is_file():
        raise ValueError(f"{model} does not exist")
    config = sherpa_onnx.OfflinePunctuationConfig(
        model=sherpa_onnx.OfflinePunctuationModelConfig(ct_transformer=model),
    )

    punct = sherpa_onnx.OfflinePunctuation(config)

    text_list = [
            'Mark how are you feeling about China ', 
    'Still extremely bullish ', 
    'I find some of the perspectives today quite bizarre from investors ', 
    "I thought we'd back out lined it perfectly ", 
     "Look  we're never going to get the big stimulus menu RSE ", 
    
    '在五老星系中發現了有幾分子零第三類接觸還有多人啊微波真是展開拍攝任務已經近滿周年最近也傳過來許多過去難以拍攝到的照片6月初天威學家在自然期看上發表了正常照片在藍色核心外'

    ]
    for text in text_list:
        text_with_punct = punct.add_punctuation(text)
        print("----------")
        print(f"input: {text}")
        print(f"output: {text_with_punct}")

    print("----------")


if __name__ == "__main__":
    main()

exit()
import os
os.environ['HTTPS_PROXY']='http://127.0.0.1:10808'
##
import sys
import requests
import tempfile
import zipfile
import shutil
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, 
                               QProgressBar, QLabel, QMessageBox, QHBoxLayout, 
                               QFrame, QScrollArea)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont
import platform
from PySide6.QtGui import QFontDatabase
from videotrans.configure import config
MODEL_DIR=f'{config.ROOT_DIR}/models/'

# ==========================================
# 0. 语言配置区域
# ==========================================

CN_LANGDICT = {
    "app_title": "模型下载",
    "header_title": "可在此手动下载所需模型",
    "header_tips": "大文件下载请耐心等待",
    
    # 分区标题
    "section_tts": "TTS & 翻译模型 (Zip解压)",
    "section_openai": "openai-whisper渠道所需模型(单文件)",
    "section_faster": "faster-whisper渠道所需模型(多文件)",

    # 按钮与状态
    "btn_start": "开始下载",
    "btn_redownload": "重新下载",
    "btn_download_model": "下载模型",
    "btn_stop": "停止 ⏹",
    "btn_stopping": "停止中...",
    
    "status_not_downloaded": "未下载",
    "status_installed": "✔ 已下载",
    "status_connecting": "连接中: {}...",
    "status_downloading": "下载中: {} ({})", # 文件名, 进度
    "status_extracting": "正在解压...",
    "status_cancelled": "已取消",
    "status_failed": "❌ 失败",
    "status_success": "✔ 完成",
    "status_multi_progress": "文件 [{}/{}]", # 第几个/共几个
    
    "msg_success_title": "成功",
    "msg_error_title": "下载出错了",
    "msg_install_success": "全部处理完成",
    "msg_user_stopped": "用户已停止下载",
    "msg_task_finished": "[{}] 下载部署完成！",
    "msg_task_failed": "模型 [{}] 下载失败:\n{}",
    
    "err_no_py7zr": "需要解压.7z文件但未安装 py7zr",
    "err_format": "文件格式错误",
    
    
    "task_m2m":"m2m100翻译模型(1.0G)",
    "task_realtime":"实时语音识别模型(0.9G)",
    "task_piper":"Piper-TTS模型(6.4G)",
    "task_vits":"VITS-cnen模型(540M)",
    
    "xiazaishibai_shoudong":"下载失败，请手动打开以下网址\n[{}]\n将.json/.txt/.bin 等文件下载到目录\n[{}] "
}

EN_LANGDICT = {
    "app_title": "Models Downloader",
    "header_title": "Manually download the required model here.",
    "header_tips": "Please wait patiently while the large file download continues.",
    
    "section_tts": "TTS & Translation(Archive)",
    "section_openai": "openai-whisper(Single File)",
    "section_faster": "faster-whisper(Multi-Files)",

    "btn_start": "Download",
    "btn_redownload": "Redownload",
    "btn_download_model": "Download",
    "btn_stop": "Stop ⏹",
    "btn_stopping": "Stopping...",
    
    "status_not_downloaded": "Not Downloaded",
    "status_installed": "✔ Installed",
    "status_connecting": "Connecting: {}...",
    "status_downloading": "Downloading: {} ({})",
    "status_extracting": "Extracting...",
    "status_cancelled": "Cancelled",
    "status_failed": "❌ Failed",
    "status_success": "✔ Done",
    "status_multi_progress": "File [{}/{}]",
    
    "msg_success_title": "Success",
    "msg_error_title": "Download Error",
    "msg_install_success": "All Done",
    "msg_user_stopped": "User Stopped",
    "msg_task_finished": "[{}] Finished!",
    "msg_task_failed": "[{}] model download Failed:\n{}",
    
    "err_no_py7zr": "py7zr not installed for .7z files",
    "err_format": "File format error",
    
    "task_m2m":"m2m100 translation model(1.0G)",
    "task_realtime":"Realtime STT model(0.9G)",
    "task_piper":"Piper-TTS model(6.4G)",
    "task_vits":"VITS-cnen model(540M)",
    
    "xiazaishibai_shoudong":"Download failed. Please manually open the following URL\n[{}]\n and download the .json/.txt/.bin files to the following directory\n[{}]"
}

LANG_CODE = 'cn' 
TRANS = CN_LANGDICT if LANG_CODE.lower() == 'cn' else EN_LANGDICT

# ==========================================
# 1. 核心逻辑
# ==========================================
try:
    import py7zr
    HAS_7Z = True
except ImportError:
    HAS_7Z = False

class DownloadWorker(QThread):
    progress_signal = Signal(int)       
    status_signal = Signal(str)         
    finished_signal = Signal(bool, str) 

    def __init__(self, task_data):
        super().__init__()
        self.task = task_data

    def get_filename_from_url(self, url):
        """解析URL获取纯净文件名 (去除 ?query)"""
        parsed = urlparse(url)
        return os.path.basename(parsed.path)

    def run(self):
        try:
            # 1. 解析任务类型
            target_dir = Path(self.task["dir"])
            target_dir.mkdir(parents=True, exist_ok=True)

            urls_to_process = [] # List of (url, save_path, is_archive)

            # 情况 A: Faster Whisper (多个 URL)
            if "urls" in self.task:
                # 判断能否联通 huggingface.co，如果不能，则使用镜像 hf-mirror.com 替换
                hf_mirror=False
                if 'huggingface.co' in self.task['urls'][0]:
                    try:
                        self.status_signal.emit(f"check huggingface.co ...")
                        requests.head('https://huggingface.co',timeout=10)
                        print('可以使用 huggingface.co')
                    except Exception:
                        print(f'无法联通 huggingface.co, 使用镜像 hf-mirror.com 替换')
                        self.status_signal.emit(f"use hf-mirror.com")
                        hf_mirror=True
                for url in self.task["urls"]:
                    if hf_mirror:
                        url=url.replace('https://huggingface.co','https://hf-mirror.com')
                    fname = self.get_filename_from_url(url)
                    # Faster Whisper 的文件直接保存到 target_dir
                    urls_to_process.append({
                        "url": url,
                        "path": target_dir / fname,
                        "extract": False
                    })
            
            # 情况 B: 单个 URL (VITS/OpenAI 等)
            elif "url" in self.task:
                url = self.task["url"]
                fname = self.get_filename_from_url(url)
                
                is_archive = fname.lower().endswith(('.zip', '.7z'))
                
                # 如果是压缩包，暂存到临时文件，否则直接保存到目标
                if is_archive:
                    # 压缩包逻辑：保存路径不重要，重要的是解压逻辑
                    urls_to_process.append({
                        "url": url, 
                        "path": None, # 临时处理
                        "extract": True,
                        "fname": fname
                    })
                else:
                    # 单文件逻辑 (OpenAI pt): 直接保存
                    urls_to_process.append({
                        "url": url,
                        "path": target_dir / fname,
                        "extract": False
                    })

            total_files = len(urls_to_process)
            
            # 2. 开始遍历下载
            for index, item in enumerate(urls_to_process):
                if self.isInterruptionRequested(): raise UserWarning(TRANS["msg_user_stopped"])

                url = item["url"]
                display_name = item.get("fname", item["path"].name if item["path"] else "Archive")
                
                # 更新大状态
                prefix_status = ""
                if total_files > 1:
                    prefix_status = TRANS["status_multi_progress"].format(index + 1, total_files) + " "

                self.status_signal.emit(f"{prefix_status}{TRANS['status_connecting'].format(display_name)}")

                # --- 下载过程 ---
                with requests.get(url, stream=True, timeout=60) as response:
                    response.raise_for_status()
                    total_length = response.headers.get('content-length')
                    
                    # 决定写入目标：如果是需要解压的，写入临时文件；否则直接写入目标文件
                    if item["extract"]:
                        dest_file_obj = tempfile.TemporaryFile() # 内存/临时磁盘，自动删除
                    else:
                        dest_file_obj = open(item["path"], 'wb')

                    try:
                        if total_length is None:
                            dest_file_obj.write(response.content)
                        else:
                            total_length = int(total_length)
                            downloaded = 0
                            for chunk in response.iter_content(chunk_size=8192):
                                if self.isInterruptionRequested(): raise UserWarning(TRANS["msg_user_stopped"])
                                if chunk:
                                    dest_file_obj.write(chunk)
                                    downloaded += len(chunk)
                                    
                                    # 计算进度
                                    # 单文件进度 0-100
                                    file_percent = (downloaded / total_length)
                                    
                                    # 总进度： (当前文件索引 + 当前文件进度) / 总文件数 * 100
                                    # 如果是解压任务，预留 20% 给解压过程
                                    if item["extract"]:
                                        current_p = (index + file_percent * 0.8) / total_files * 100
                                    else:
                                        current_p = (index + file_percent) / total_files * 100
                                    
                                    self.progress_signal.emit(int(current_p))
                    finally:
                        if not item["extract"]:
                            dest_file_obj.close() # 关闭实体文件句柄

                    # --- 解压过程 (如果需要) ---
                    if item["extract"]:
                        self.status_signal.emit(TRANS["status_extracting"])
                        dest_file_obj.seek(0) # 回到文件头
                        
                        fname = item["fname"]
                        if fname.endswith('.7z'):
                            if not HAS_7Z: raise ImportError(TRANS["err_no_py7zr"])
                            if not py7zr.is_7zfile(dest_file_obj): raise Exception(TRANS["err_format"])
                            with py7zr.SevenZipFile(dest_file_obj, 'r') as z:
                                z.extractall(path=target_dir)
                        else:
                            with zipfile.ZipFile(dest_file_obj) as zf:
                                zf.extractall(path=target_dir)
                        
                        # 解压完成，补齐进度
                        self.progress_signal.emit(int((index + 1) / total_files * 100))
                        dest_file_obj.close() # 显式关闭触发删除

            if not self.isInterruptionRequested():
                self.progress_signal.emit(100)
                self.finished_signal.emit(True, TRANS["msg_install_success"])

        except UserWarning:
            self.finished_signal.emit(False, "STOPPED")
        except Exception as e:
            msg=str(e)
            if 'hf-mirror.com' in urls_to_process[0]['url'] or 'huggingface.co' in urls_to_process[0]['url']:
                downurl=urls_to_process[0]['url'].split('/resolve/main')[0]+"/tree/main"
                msg=f'{TRANS["xiazaishibai_shoudong"].format(downurl,self.task["dir"])}\n\n{msg}'
            self.finished_signal.emit(False, msg)

# ==========================================
# 2. 任务组件
# ==========================================
class TaskWidget(QFrame):
    def __init__(self, task_info):
        super().__init__()
        self.task = task_info
        self.worker = None
        self.setFrameShape(QFrame.StyledPanel)
        # 稍微调整样式，使其在列表中紧凑一些
        self.setStyleSheet(".TaskWidget { background-color: #ffffff; border-radius: 6px; border: 1px solid #e0e0e0; margin-bottom: 2px; }")
        
        self.init_ui()
        self.check_status()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # 第一行
        header_layout = QHBoxLayout()
        self.title_label = QLabel(self.task["name"])
        font = QFont() 
        font.setBold(True)
        font.setPointSize(10)
        self.title_label.setFont(font)

        
        self.status_label = QLabel(TRANS["status_not_downloaded"])
        self.status_label.setStyleSheet("color: #999; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        header_layout.addWidget(self.title_label, 1) # 权重1
        header_layout.addWidget(self.status_label, 0)
        
        # 第二行：进度条
        self.pbar = QProgressBar()
        self.pbar.setVisible(False)
        self.pbar.setStyleSheet("QProgressBar { height: 6px; border-radius: 3px; background: #eee; } QProgressBar::chunk { background: #0078d7; border-radius: 3px; }")

        # 第三行：按钮
        self.action_btn = QPushButton(TRANS["btn_start"])
        self.action_btn.setCursor(Qt.PointingHandCursor)
        self.action_btn.clicked.connect(self.toggle_download)
        self.style_btn_normal()

        self.layout.addLayout(header_layout)
        self.layout.addWidget(self.pbar)
        self.layout.addWidget(self.action_btn)

    def check_status(self):
        path = Path(self.task["check"])
        if path.exists():
            self.status_label.setText(TRANS["status_installed"])
            self.status_label.setStyleSheet("color: green;")
            self.action_btn.setText(TRANS["btn_redownload"])
        else:
            self.status_label.setText(TRANS["status_not_downloaded"])
            self.action_btn.setText(TRANS["btn_download_model"])

    def toggle_download(self):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.action_btn.setEnabled(False)
            self.action_btn.setText(TRANS["btn_stopping"])
        else:
            self.start_download()

    def start_download(self):
        self.pbar.setValue(0)
        self.pbar.setVisible(True)
        self.style_btn_stop()
        self.status_label.setStyleSheet("color: #0078d7;")
        
        self.worker = DownloadWorker(self.task)
        self.worker.progress_signal.connect(self.pbar.setValue)
        self.worker.status_signal.connect(self.status_label.setText)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, success, msg):
        # 【关键修复】: 必须先等待线程安全退出，才能清理引用
        if self.worker:
            self.worker.wait() # 阻塞等待线程 run 方法完全返回
            self.worker = None
            
        self.style_btn_normal()
        
        if success:
            self.status_label.setText(TRANS["status_success"])
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.pbar.setVisible(False)
            self.check_status()
            
        elif msg == "STOPPED":
            self.status_label.setText(TRANS["status_cancelled"])
            self.status_label.setStyleSheet("color: #999;")
            self.pbar.setVisible(False)
            self.check_status()
        else:
            self.status_label.setText(TRANS["status_failed"])
            self.status_label.setStyleSheet("color: red;")
            self.pbar.setVisible(False)
            QMessageBox.critical(self, TRANS["msg_error_title"], TRANS["msg_task_failed"].format(self.task['name'], msg))

    def style_btn_normal(self):
        self.action_btn.setEnabled(True)
        # 稍微缩小一点按钮高度
        self.action_btn.setFixedHeight(30)
        self.action_btn.setStyleSheet("""
            QPushButton { background-color: #0078d7; color: white; border-radius: 4px; border: none; }
            QPushButton:hover { background-color: #0063b1; }
        """)
        # 文字由 check_status 决定

    def style_btn_stop(self):
        self.action_btn.setText(TRANS["btn_stop"])
        self.action_btn.setStyleSheet("""
            QPushButton { background-color: #e81123; color: white; border-radius: 4px; border: none;}
            QPushButton:hover { background-color: #c50f1f; }
        """)

# ==========================================
# 3. 主窗口
# ==========================================
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(TRANS["app_title"])
        self.resize(550, 800) # 增加高度
        
        # 数据定义
        self.init_data()
        self.init_ui()

    def init_data(self):
        # 1. 原始 ZIP/7Z 任务
        self.tasks_zip = [
            {
                "name": TRANS.get("task_vits", "VITS-TTS (zh_en)"),
                "url": "https://modelscope.cn/models/himyworld/videotrans/resolve/master/vits-tts.zip",
                "dir": MODEL_DIR,
                "check": f"{MODEL_DIR}vits/zh_en"
            },
            {
                "name": TRANS.get("task_piper", "Piper-TTS (zh)"),
                "url": "https://github.com/jianchang512/stt/releases/download/0.0/piper-zh-en-models.7z",
                "dir": MODEL_DIR,
                "check": f"{MODEL_DIR}piper/zh"
            },
            {
                "name": TRANS.get("task_m2m", "M2M100 Translator"),
                "url": "https://modelscope.cn/models/himyworld/videotrans/resolve/master/m2m100_12b_model.zip",
                "dir": MODEL_DIR,
                "check": f"{MODEL_DIR}m2m100_12b/model.bin"
            },
            {
                "name": TRANS.get("task_realtime", "Realtime STT (ONNX)"),
                "url": "https://modelscope.cn/models/himyworld/videotrans/resolve/master/realtimestt.zip",
                "dir": f"{MODEL_DIR}",
                "check": f"{MODEL_DIR}onnx/encoder.onnx"
            }
        ]
        
        # 2. OpenAI Whisper (单文件 PT)
        self.tasks_openai = [
             {
            "name":"tiny.en", "url":"https://openaipublic.azureedge.net/main/whisper/models/d3dd57d32accea0b295c96e26691aa14d8822fac7d9d27d5dc00b4ca2826dd03/tiny.en.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}tiny.en.pt"
            },
            {
            "name":"tiny", "url":"https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}tiny.pt"
            },
            {
            "name":"base.en", "url":"https://openaipublic.azureedge.net/main/whisper/models/25a8566e1d0c1e2231d1c762132cd20e0f96a85d16145c3a00adf5d1ac670ead/base.en.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}base.en.pt"
            },
            {
            "name":"base", "url":"https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}base.pt"
            },
            {
            "name":"small.en", "url":"https://openaipublic.azureedge.net/main/whisper/models/f953ad0fd29cacd07d5a9eda5624af0f6bcf2258be67c92b79389873d91e0872/small.en.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}small.en.pt"
            },
            {
            "name":"small", "url":"https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}small.pt"
            },
            {
            "name":"medium.en", "url":"https://openaipublic.azureedge.net/main/whisper/models/d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f/medium.en.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}medium.en.pt"
            },
            {
            "name":"medium", "url":"https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}medium.pt"
            },
            {
            "name":"large-v1", "url":"https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a/large-v1.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}large-v1.pt"
            },
            {
            "name":"large-v2", "url":"https://openaipublic.azureedge.net/main/whisper/models/81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524/large-v2.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}large-v2.pt"
            },
            {
            "name":"large-v3", "url":"https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}large-v3.pt"
            },
            {
            "name":"large-v3-turbo", "url":"https://openaipublic.azureedge.net/main/whisper/models/aff26ae408abcba5fbf8813c21e62b0941638c5f6eebfb145be0c9839262a19a/large-v3-turbo.pt",
            "dir":MODEL_DIR, "check":f"{MODEL_DIR}large-v3-turbo.pt"
            },
        ]

        # 3. Faster Whisper (多文件列表)
        self.tasks_faster = [
            {
                "name":"tiny.en",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-tiny.en",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-tiny.en/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-tiny.en/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-tiny.en/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-tiny.en/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-tiny.en/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"tiny",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-tiny",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-tiny/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-tiny/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-tiny/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-tiny/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-tiny/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"base.en",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-base.en",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-base.en/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-base.en/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-base.en/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-base.en/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-base.en/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"base",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-base",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-base/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-base/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-base/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-base/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-base/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"small.en",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-small.en",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-small.en/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-small.en/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-small.en/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-small.en/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-small.en/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"small",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-small",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-small/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-small/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-small/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-small/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-small/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"medium.en",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-medium.en",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-medium.en/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-medium.en/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-medium.en/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-medium.en/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-medium.en/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"medium",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-medium",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-medium/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-medium/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-medium/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-medium/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-medium/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"large-v1",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-large-v1",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-large-v1/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-large-v1/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v1/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v1/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v1/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"large-v2",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-large-v2",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-large-v2/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-large-v2/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v2/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v2/resolve/main/vocabulary.txt?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v2/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"large-v3",
                "dir":f"{MODEL_DIR}models--Systran--faster-whisper-large-v3",
                "check":f"{MODEL_DIR}models--Systran--faster-whisper-large-v3/model.bin",
                "urls": [
                    'https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/preprocessor_config.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/vocabulary.json?download=true',
                    'https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"large-v3-turbo",
                "dir":f"{MODEL_DIR}models--mobiuslabsgmbh--faster-whisper-large-v3-turbo",
                "check":f"{MODEL_DIR}models--mobiuslabsgmbh--faster-whisper-large-v3-turbo/model.bin",
                "urls": [
                    'https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo/resolve/main/config.json?download=true',
                    'https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo/resolve/main/preprocessor_config.json?download=true',
                    'https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo/resolve/main/tokenizer.json?download=true',
                    'https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo/resolve/main/vocabulary.json?download=true',
                    'https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo/resolve/main/model.bin?download=true',
                ]
            },
            {
                "name":"distil-large-v3.5-ct2",
                "dir":f"{MODEL_DIR}models--distil-whisper--distil-large-v3.5-ct2",
                "check":f"{MODEL_DIR}models--distil-whisper--distil-large-v3.5-ct2/model.bin",
                "urls":[
                'https://huggingface.co/distil-whisper/distil-large-v3.5-ct2/resolve/main/config.json?download=true',
                'https://huggingface.co/distil-whisper/distil-large-v3.5-ct2/resolve/main/preprocessor_config.json?download=true',
                'https://huggingface.co/distil-whisper/distil-large-v3.5-ct2/resolve/main/tokenizer.json?download=true',
                'https://huggingface.co/distil-whisper/distil-large-v3.5-ct2/resolve/main/vocabulary.json?download=true',
                'https://huggingface.co/distil-whisper/distil-large-v3.5-ct2/resolve/main/model.bin?download=true',
                ]
            }
        ]

    def init_ui(self):
        # 外层布局
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)

        # 1. 顶部固定区域
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        title = QLabel(TRANS["header_title"])
        font = QFont() 
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        
        title.setAlignment(Qt.AlignCenter)
        
        tips = QLabel(TRANS["header_tips"])
        tips.setStyleSheet("color: #666; font-size: 12px;")
        tips.setAlignment(Qt.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(tips)
        outer_layout.addWidget(header_widget)

        # 2. 滚动区域 (核心修改点)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True) # 关键：让内部 widget 自适应宽度
        scroll.setFrameShape(QFrame.NoFrame)
        
        # 滚动区域的内容容器
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(5)

        # --- 辅助函数：添加分节标题 ---
        def add_section_header(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("background-color: #f0f0f0; padding: 8px; font-weight: bold; color: #333; margin-top: 10px; border-radius: 4px;")
            content_layout.addWidget(lbl)

        # 添加第一组：TTS & ZIP
        add_section_header(TRANS["section_tts"])
        for task in self.tasks_zip:
            content_layout.addWidget(TaskWidget(task))

        # 添加第二组：OpenAI Whisper
        add_section_header(TRANS["section_openai"])
        for task in self.tasks_openai:
            content_layout.addWidget(TaskWidget(task))

        # 添加第三组：Faster Whisper
        add_section_header(TRANS["section_faster"])
        for task in self.tasks_faster:
            content_layout.addWidget(TaskWidget(task))

        content_layout.addStretch() # 底部弹簧
        
        scroll.setWidget(content_widget)
        outer_layout.addWidget(scroll)

def get_best_font():
    """
    根据操作系统返回合适的字体名称
    注意：在 main 函数中创建 app 后才能调用
    """
    system_name = platform.system()
    
    if system_name == "Windows":
        priorities = ["Microsoft YaHei", "SimHei", "Segoe UI"]
    elif system_name == "Darwin": # macOS
        priorities = ["PingFang SC", "Heiti SC", "Helvetica Neue"]
    else: # Linux
        priorities = ["Noto Sans CJK SC", "WenQuanYi Micro Hei", "DejaVu Sans", "Ubuntu"]
    
    # 【修复点】使用静态方法，无需实例化
    available_families = QFontDatabase.families()
    
    for font_name in priorities:
        if font_name in available_families:
            return font_name
            
    return "sans-serif" # 回退选项

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    font_name = get_best_font()
    # 2. 设置全局字体
    if font_name == "sans-serif":
        font = QFont()
        font.setStyleHint(QFont.SansSerif)
    else:
        font = QFont(font_name)
    
    font.setPointSize(10)
    app.setFont(font)

    print(f"OS: {platform.system()}, Font: {font.family()}")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())