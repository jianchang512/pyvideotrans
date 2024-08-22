import math
import os
import shutil
import time
import traceback
from pathlib import Path

from pydub import AudioSegment

from videotrans.util import tools

import librosa
import soundfile as sf
import torch
from videotrans.separate.vr import AudioPre
from videotrans.configure import config
from videotrans.util import tools
import hashlib


def uvr(*, model_name=None, save_root=None, inp_path=None, source="logs", btnkey=None,percent=[0,1]):
    infos = []
    try:
        func = AudioPre
        pre_fun = func(
            agg=10,
            model_path=os.path.join(config.rootdir, f"uvr5_weights/{model_name}.pth"),
            device="cuda" if torch.cuda.is_available() else "cpu",
            is_half=False,
            source=source
        )
        done = 0
        try:
            y, sr = librosa.load(inp_path, sr=None)
            info = sf.info(inp_path)
            channels = info.channels
            need_reformat = 0
            pre_fun._path_audio_(
                inp_path,
                ins_root=save_root,
                btnkey=btnkey,
                percent=percent
            )
            done = 1
        except  Exception:
            traceback.print_exc()
    except:
        infos.append(traceback.format_exc())
        yield "\n".join(infos)
    finally:
        try:
            del pre_fun.model
            del pre_fun
        except Exception:
            traceback.print_exc()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    yield "\n".join(infos)


def convert_to_pure_eng_num(string):
    # 将输入字符串转换为UTF-8编码的bytes
    encoded_string = string.encode('utf-8')
    # 创建一个md5哈希对象
    hasher = hashlib.md5()
    # 用输入字符串的bytes更新哈希对象
    hasher.update(encoded_string)
    # 获取哈希的十六进制字符串形式
    hex_digest = hasher.hexdigest()
    return hex_digest

def split_audio(file_path):
    # Load the audio file
    audio = AudioSegment.from_wav(file_path)
    segment_length=10
    output_folder=Path(config.TEMP_DIR)/"separate"
    output_folder.mkdir(parents=True,exist_ok=True)
    output_folder=output_folder.as_posix()

    # Calculate the total number of segments
    total_length = len(audio)  # Total length in milliseconds
    segment_length_ms = segment_length * 1000  # Convert segment length to milliseconds
    segments = []

    # Split the audio and save each segment
    for i in range(0, total_length, segment_length_ms):
        start = i
        end = min(i + segment_length_ms, total_length)
        segment = audio[start:end]

        # Create a segment file name and save it
        segment_filename = os.path.join(output_folder, f"segment_{i // 1000}.wav")
        # 如果音频不是2通道，16kHz，则进行转换
        if segment.channels != 2:
            segment = segment.set_channels(2)
        if segment.frame_rate != 44100:
            segment = segment.set_frame_rate(44100)
        segment.export(segment_filename, format="wav")
        segments.append(segment_filename)

    return segments

def concatenate_audio(input_wav_list, out_wav):
    # Initialize an empty AudioSegment
    combined = AudioSegment.empty()

    # Iterate over each wav file in the input list
    for wav_file in input_wav_list:
        # Load the current wav file
        audio = AudioSegment.from_wav(wav_file)
        if audio.channels != 2:
            audio = audio.set_channels(2)
        if audio.frame_rate != 44100:
            audio = audio.set_frame_rate(44100)
        # Append it to the combined AudioSegment
        combined += audio

    # Export the combined AudioSegment to the output file
    combined.export(out_wav, format="wav")


# path 是需要保存vocal.wav的目录
def start(audio, path, source="logs", btnkey=None):
    Path(path).mkdir(parents=True,exist_ok=True)
    reslist=split_audio(audio)
    vocal_list=[]
    instr_list=[]

    grouplen=len(reslist)
    per=round(1/grouplen,2)
    for i,audio_seg in enumerate(reslist):
        audio_path=Path(audio_seg)
        path_dir=audio_path.parent/audio_path.stem
        path_dir.mkdir(parents=True,exist_ok=True)
        try:
            gr = uvr(model_name="HP2", save_root=path_dir.as_posix(), inp_path=Path(audio_seg).as_posix(), source=source, btnkey=btnkey,percent=[i*per,per])
            print(next(gr))
            print(next(gr))
        except StopIteration:
            vocal_list.append((path_dir/'vocal.wav').as_posix())
            instr_list.append((path_dir/'instrument.wav').as_posix())
        except Exception as e:
            print('异常'+str(e))
            raise

    if len(vocal_list)<1 or len(instr_list)<1:
        raise Exception('separate bgm error')
    concatenate_audio(instr_list,Path(f"{path}/instrument.wav").as_posix())
    concatenate_audio(vocal_list,Path(f"{path}/vocal.wav").as_posix())
    # try:
    #     # 获取总时长秒
    #     # sec = tools.get_audio_time(audio)
    #     # print(f'{path=}')
    #     Path(path).mkdir(parents=True,exist_ok=True)
    #     # print(f'222{path=}')
    #     # if sec<=dist:
    #     gr = uvr(model_name="HP2", save_root=path, inp_path=audio, source=source, btnkey=btnkey)
    #     print(next(gr))
    #     print(next(gr))
    # except StopIteration:
    #     pass
    # except Exception as e:
    #     print(type(e))
    #     msg = f"保留背景音:{str(e)}"
    #     raise Exception(msg)
