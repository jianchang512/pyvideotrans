# 已废弃，请使用 api.py
# Please use api.py
# 当前文件仅可用于 Google Colab，若以其他方式使用，请修改 `/content` 等相关路径

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import zhconv

def download_file(url):
    """Downloads a file from a URL and saves it to /content."""
    if sys.platform!='linux':
        raise Exception('仅在 Google Colab 上可下载文件，其他系统请传递文件绝对路径')
    parsed_url = urlparse(url)
    filename = None
    filepath = None
    Path('/content').mkdir(exist_ok=True)

    # Case 1: Filename in URL path
    if parsed_url.path:
        potential_filename = os.path.basename(parsed_url.path)
        if '.' in potential_filename:
            filename = re.sub(r'[^\w\-_\.]', '', potential_filename) # Sanitize filename for Linux
            filepath = os.path.join('/content', filename)

    # Case 2: Filename in query parameters
    if not filepath:  # if no filename found in path
        query_params = parse_qs(parsed_url.query)
        video_audio_exts = ['mp4', 'mov', 'mkv', 'mpeg', 'avi', 'wmv', 'ts', 'wav', 'flac', 'mp3', 'm4a', 'wma']
        for param_value in query_params.values():  # Check all the parameter's values
              for value in param_value: # some parameter may have multiple values, we check all of them
                  potential_filename_with_ext = None
                  for ext in video_audio_exts:
                      if '.' + ext in value :
                          potential_filename_with_ext = value
                          break;
                  if potential_filename_with_ext:
                      filename = re.sub(r'[^\w\-_\.]', '', potential_filename_with_ext)
                      filepath = os.path.join('/content', filename)
                      break  # Stop after finding the first valid filename


    if filepath and filename:
        try:
           subprocess.run(['wget', '-O', filepath , url], check=True, capture_output=True) # Suppress output to avoid verbosity
           return filepath
        except subprocess.CalledProcessError as e:
            print(f"Error downloading file: {e.stderr.decode()}")  # Decode stderr for printing
            return None
    else:
        print("No valid filename found in URL.")
        return None



def speech_to_text(model_name='large-v2',language="auto",prompt=None,audio_file=None,device='cuda',compute_type='float16'):
    from videotrans.configure import config
    from videotrans.util import tools
    from faster_whisper import WhisperModel
    if audio_file.startswith('http'):
        audio_file=download_file(audio_file)
    if not audio_file or not Path(audio_file).exists():
        raise Exception(f'未找到 {audio_file} ，请传递文件绝对路径或文件是否存在')
    language=None if not language or language=='auto' else language[:2]
    model = WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
        download_root="./models",
        local_files_only=False
    )
    Path(config.TEMP_DIR).mkdir(parents=True, exist_ok=True)


    stem=Path(audio_file).stem
    shibie_file=config.TEMP_DIR+f'/{time.time()}.wav'

    tools.runffmpeg(['-y','-i',audio_file,'-ar','16000','-ac','1',shibie_file])
    segments, info = model.transcribe(
            shibie_file,
            beam_size=5,
            best_of=5,
            condition_on_previous_text=False,
            vad_filter=True,
            vad_parameters=dict(
                min_speech_duration_ms=500,
                max_speech_duration_s= float('inf'),
                min_silence_duration_ms=250,
                speech_pad_ms=100
            ),
            word_timestamps=True,
            language=language,
            initial_prompt=prompt if prompt else None
        )
    raws=[]
    for segment in segments:
        text=zhconv.convert(segment.text, 'zh-hans') if language=='zh' else segment.text
        startraw=tools.ms_to_time_string(ms=segment.words[0].start*1000)
        endraw=tools.ms_to_time_string(ms=segment.words[-1].end*1000)
        raws.append(f'{len(raws)+1}\n{startraw} --> {endraw}\n{text.strip()}')
    output=config.ROOT_DIR+'/../output'
    Path(output).mkdir(parents=True, exist_ok=True)
    with open(output+f'/{stem}.srt', 'w', encoding='utf-8') as f:
        srts="\n\n".join(raws)
        print(srts)
        f.write(srts)
        print(f'\n已保存到 {stem}.srt\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='视频翻译pyVideoTrans', description='')

    parser.add_argument('-m', '--model', default='large-v2', type=str, choices=['tiny','tiny.en','base','base.en','small','small.en','medium', 'medium.en', 'large-v1', 'large-v2', 'large-v3', 'large-v3-turbo'], help='选择使用哪个模型')

    parser.add_argument('-l', '--language', default='auto', type=str, choices=['zh', 'en', 'ja','ko','ru','fr','de','es','pt','it','id','hi','hu','ms','kk','cs','nl','sv','bn','he','vi','tr','th','ar','auto'], help='选择音视频发音语言')

    parser.add_argument('-f', '--file', default='', type=str,  help='填写要识别创建字幕的音频或视频名称，含后缀，文件请上传到cli.py本文件同目录下, 如果名字含空格或特殊符号，请用英文双引号包括起来')

    parser.add_argument('-d', '--device', default='auto', type=str,choices=['cpu','cuda','auto'],  help='填写要在cpu还是cuda上运行，auto为自动')
    parser.add_argument('-c', '--compute_type', default='default', type=str,choices=['default','float16','float32','int8','int8_float16','int8_float32'],  help='填写数据类型，最佳为float16，需显卡支持')

    parser.add_argument('-p', '--prompt', default=None, type=str, help='设置prompt，用于模型识别')

    DEFAULT_ARGS = vars(parser.parse_args([]))
    kw=parser.parse_args()
    speech_to_text(model_name=kw.model, language=kw.language, prompt=kw.prompt, audio_file=kw.file, device=kw.device, compute_type=kw.compute_type)

"""
## explame

python cli.py -m tiny -f "c:/users/c1/videos/5s.wav"

"""
