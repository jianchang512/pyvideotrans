# import ctypes
# import io
# import json
# import os
# import re
# import subprocess
#
# # cmd=f"ffmpeg -y -i \"C:/Users/c1/Videos/kx.mp4\" -c:v libx264 -c:a pcm_s16le ceshi.mp4"
# #
# # p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,shell=True)
# #
# # while True:
# #     try:
# #         print(f"是否结束={p.poll()}")
# #
# #
# #         rs=p.wait(5)
# #         print("rs后边有没有来到")
# #         print(f"{rs=},returncode={p.returncode=}")
# #         print(f"out={p.stdout}")
# #         break
# #     except Exception as e:
# #         print("异常"+str(e))
#
#
# # with open(r'C:\Users\c1\Videos\_video_out\srt\earth.srt', "r", encoding="utf-8") as f:
# #     tx = re.split(r"\n\s*?\n", f.read().strip())
# #     for (idx, it) in enumerate(tx):
# #         c = it.strip().split("\n")
# #         start, end = c[1].strip().split(" --> ")
# #         text = "".join(c[2:]).strip()
# #         print(f"{text=}")
#
#
#
# from pydub import AudioSegment
# from pydub.silence import detect_nonsilent
# merged_audio = AudioSegment.empty()
# merged_audio+=AudioSegment.from_wav("./hc22.wav")
# #exit()
# merged_audio += AudioSegment.silent(duration=82000)
# merged_audio.export("./tts.wav", format="wav")
import os
import re
import shutil
import subprocess
import time
from datetime import timedelta

# start = timedelta(seconds=12,milliseconds=30)
# print(start)
import cv2
from pydub import AudioSegment

import videotrans
from videotrans.configure import config
from videotrans.util.tools import is_novoice_mp4, runffmpeg, runffprobe


def get_video_duration(file_path):
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        f"{file_path}"
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        duration = int(float(result.stdout.strip())*1000)
        return duration
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return None

def ms_to_time_string(*,ms=0,seconds=None):
    # 计算小时、分钟、秒和毫秒
    if seconds is None:
        td = timedelta(milliseconds=ms)
    else:
        td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000

    # 格式化为字符串
    time_string = f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    return time_string


# cv2 复制 novoice_mp4最后一帧，直到
def add_clip_to_last_cv2(noextname, duration_ms):
    folder_path = config.rootdir + f'/tmp/{noextname}'
    novoice_mp4 = f"{folder_path}/novoice.mp4"
    # 提取 1.mp4 的最后一帧为 1.png
    output_image = f"{folder_path}/{time.time()}.png"

    cap = cv2.VideoCapture(novoice_mp4)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    # 设置最后一帧为输出帧
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count - 1)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(output_image, frame)
        print(f"Successfully saved the last frame as {output_image}")
        cap.release()
    else:
        cap.release()
        set_process(f"[error]cv2延长视频末尾失败")
        return
    # 读取 源视频的帧率
    cap = cv2.VideoCapture(novoice_mp4)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()

    # 生成 设定时间的片段mp4
    clip_video = f"{folder_path}/{time.time()}.mp4"
    # 计算生成视频的帧数
    frame_count_new = int(fps * duration_ms / 1000)
    # 用相同的帧生成  clip
    image = cv2.imread(output_image)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(clip_video, fourcc, fps, (width, height))
    for _ in range(frame_count_new):
        video_writer.write(image)
    video_writer.release()
    # 连接源视频和该片段
    runffmpeg(
        f'-y -i "{novoice_mp4}" -i "{clip_video}" -filter_complex "[0:v]setsar=1[v0];[1:v]setsar=1[v1];[v0][v1]concat=n=2:v=1:a=0[outv]" -map "[outv]" -c:v libx264 -y "{novoice_mp4}-tmp.mp4"')



# ffmepg
def add_clip_to_last(noextname, duration_ms):
    folder_path = config.rootdir + f'/tmp/{noextname}'
    novoice_mp4 = f"{folder_path}/novoice.mp4"
    # 生成 设定时间的片段mp4
    clip_video = f"{folder_path}/{time.time()}.mp4"
    tmp_video = f"{folder_path}/{time.time()}-tmp.mp4"
    total_length = get_video_duration(novoice_mp4)

    if total_length<1000:
        dur=1000
    else:
        pass

    runffmpeg([
        "-y",
        "-i",
        f'"{novoice_mp4}"',
        "-ss",
        ms_to_time_string(ms=total_length - 1000).replace(',', '.'),
        "-t",
        "1",
        f'{clip_video}'
    ])
    if duration_ms <= 1000:
        tmp_video = clip_video
    else:
        pts = round(duration_ms / 1000,2)
        runffmpeg(
            f'-y  -i "{clip_video}" -vf "setpts={pts}*PTS" -c:v libx264  -crf 0   -an "{tmp_video}"'
        )

    runffmpeg(
        f'-y -i "{novoice_mp4}" -i "{tmp_video}" -filter_complex "[0:v]setsar=1[v0];[1:v]setsar=1[v1];[v0][v1]concat=n=2:v=1:a=0[outv]" -map "[outv]" -c:v libx264 -y "{novoice_mp4}-tmp.mp4"')
    return

def runffmpeg2(arg, *, noextname=None, error_exit=True):
    cmd = "ffmpeg -hide_banner "

    if isinstance(arg, list):
        arg = " ".join(arg)
    cmd += arg

    p = subprocess.run(cmd, stdout=subprocess.PIPE,
                       shell=True,
                       stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
    if p.returncode!=0:
        err=str(p.stderr)
        if err:
            print(err[err.find('Error'):])
        # print(f'{p.stderr=}')


def set_process(text,type='logs'):
    print(f'{type=}:{text=}')

def runffmpeg3(arg, *, noextname=None, error_exit=True):
    cmd = ["ffmpeg","-hide_banner"]
    if config.video['enable_cuda']:
        cmd.append("-hwaccel")
        cmd.append("cuda")
    cmd = cmd + arg
    print(cmd)


    p = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def set_result(code,errs):
        if code == 0:
            set_process("ffmpeg 执行成功")
            return True
        else:
            # set_process(f"[error]ffmpeg执行结果:失败 {cmd=},\nerrs={errs}")
            return None
    while True:
        # p_res=p.poll()
        # print(f"{p_res=}")
        # # 已结束
        # if p_res is not None:
        #     return set_result(p_res)
        try:
            #等待0.1未结束则异常
            outs, errs = p.communicate(timeout=1)
            print(errs)
            # 如果结束从此开始执行
            if set_result(p.returncode,str(errs)):
                # 成功
                return True
            # 失败
            if error_exit:
                set_process(f'执行ffmpeg失败:{errs=}','error')
            return None
        except subprocess.TimeoutExpired as e:
            # 如果前台要求停止
            print(f"超时:")
        except Exception as e:
            #出错异常
            set_process(f"[error]ffmpeg执行结果:失败 {cmd=},\n{str(e)}",'error' if error_exit else 'logs')
            return None

rs=runffmpeg3(['-hide_banner', '-loop', '1', '-i', 'E:/python/pyvideotranslate/win/speech_to_subtitle/tmp/1 -1/last.jpg', '-vf', 'fps=23,scale=640:368', '-c:v', 'libx264', '-crf', '0', '-to', '00:01:12.506', '-pix_fmt', 'yuv420p', '-y', 'E:/python/pyvideotranslate/win/speech_to_subtitle/tmp/1 -1/last_clip.mp4'])
print(rs)