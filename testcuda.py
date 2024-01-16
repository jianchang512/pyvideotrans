# 测试 CUDA 可用性
# 找到一个 h264 编码的mp4视频，重命名为 raw.mp4，然后复制到和当前脚本同目录下，然后执行测试

import json
import subprocess
import torch
import os
import sys

if torch.cuda.is_available():
    print('CUDA 可用，如果实际使用仍提示 cuda 相关错误，请尝试升级显卡驱动并重新配置CUDA12')
else:
    print("当前计算机CUDA不可用")
    input("\n按回车键关闭窗口")
    sys.exit()

result = subprocess.run(['ffmpeg', '-hwaccels'], text=True, stdout=subprocess.PIPE)
print(f'当前支持的硬件加速器:\n{result.stdout}')

rootdir = os.getcwd()
tmpdir = os.path.join(rootdir, 'tmp')
if not os.path.exists(tmpdir):
    os.makedirs(tmpdir, exist_ok=True)

# 原始视频
sourcemp4 = rootdir + "/raw.mp4"
sourceavi = rootdir + "/raw.mp4.avi"
if not os.path.exists(sourcemp4):
    print('为进一步测试能否真实正确完成CUDA下视频处理,\n请复制一个mp4视频，重名为 raw.mp4,粘贴到当前项目目录下')
    input("\n按回车键关闭窗口")
    sys.exit()


def runffmpeg(cmd,*,title=""):
    p = subprocess.Popen(cmd,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    outs, errs = p.communicate()
    if p.returncode == 0:
        return f'[OK] {title}: {cmd=}'
    print("\n\n******出错了Error*******")
    print(f'{cmd=}')
    print(str(errs))
    print("\n******Error出错了*******\n")
    input("\n按回车键关闭窗口")
    sys.exit()

def runffprobe(cmd):
    try:
        p = subprocess.run(['ffprobe'] + cmd, stdout=subprocess.PIPE, text=True)
        if p.returncode == 0:
            return p.stdout.strip()
        else:
            print(f'{p.stderr=}')
        return False
    except subprocess.CalledProcessError as e:
        print(f'{e=}')
        return False


# 获取视频信息
def get_video_info(mp4_file, *, video_fps=False, video_scale=False, video_time=False):
    out = runffprobe(['-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', mp4_file])
    if out is False:
        raise Exception(f'ffprobe error:dont get video information')
    out = json.loads(out)
    result = {
        "video_fps": 0,
        "video_codec_name": "h264",
        "audio_codec_name": "aac",
        "width": 0,
        "height": 0,
        "time": 0,
        "streams_len": 0,
        "streams_audio": 0
    }
    if "streams" not in out or len(out["streams"]) < 1:
        raise Exception(f'ffprobe error:streams is 0')

    if "format" in out and out['format']['duration']:
        result['time'] = int(float(out['format']['duration']) * 1000)
    for it in out['streams']:
        result['streams_len'] += 1
        if it['codec_type'] == 'video':
            result['video_codec_name'] = it['codec_name']
            result['width'] = int(it['width'])
            result['height'] = int(it['height'])
            fps, c = it['r_frame_rate'].split('/')
            if not c or c == '0':
                c = 1
                fps = int(fps)
            else:
                fps = round(int(fps) / int(c))
            result['video_fps'] = fps
        elif it['codec_type'] == 'audio':
            result['streams_audio'] += 1
            result['audio_codec_name'] = it['codec_name']

    if video_time:
        return result['time']
    if video_fps:
        return ['video_fps']
    if video_scale:
        return result['width'], result['height']
    return result


# 从视频中截取的图片
img = os.path.join(tmpdir, '1.jpg')
# 从原始视频中分离出的无声视频
novoice = os.path.join(tmpdir, 'novoice.mp4')
# 视频 音频 硬字幕合并后输出
out_hard = os.path.join(tmpdir, 'out_hard.mp4')

# 视频 音频 软字幕合并后输出
out_soft = os.path.join(tmpdir, 'out_soft.mp4')
# 配音无字幕
out_nosrt = os.path.join(tmpdir, 'out_nosrt.mp4')

# 从原始视频中分离出音频
m4a = os.path.join(tmpdir, '1.m4a')
# m4a 格式转为 wav格式
wav = os.path.join(tmpdir, '1.wav')
wavspeedup = os.path.join(tmpdir, '1-speedup.wav')

# 连接2个视频片段
concat = os.path.join(tmpdir, 'concat.txt')
# 字幕文件
srtfile = os.path.join(tmpdir, 'zimu.srt')
# 根据图片生成的视频
imgvideo = os.path.join(tmpdir, 'img.mp4')
# 从视频中截取的片段
pianduan = os.path.join(tmpdir, 'pianduan.mp4')

# 图片视频片段和截取的片段合并
hebing = os.path.join(tmpdir, 'imgvideo-pianduan.mp4')

# 获取视频信息
video_info = get_video_info(sourcemp4)
if not video_info or video_info['time'] == 0:
    print("视频数据存在错误，请更换视频")
    input("\n按回车键关闭窗口")
    sys.exit()

if video_info['video_codec_name'] != 'h264' or video_info['audio_codec_name'] != 'aac':
    # 转换
    tmptestmp4 = os.path.join(rootdir, 'tmptest.mp4')
    runffmpeg(['ffmpeg',
 '-hide_banner',
 '-ignore_unknown',
 '-vsync',
 'vfr',
 '-hwaccel',
 'cuvid',
 '-hwaccel_output_format',
 'nv12',
 '-extra_hw_frames',
 '2',
 '-y',
 '-i',
 sourcemp4,
 '-c:v',
 'h264_nvenc',
 '-c:a',
 'aac',
 tmptestmp4]
,title="raw.mp4格式不正确，请确保是h264编码的mp4视频")
    os.unlink(sourcemp4)
    os.rename(tmptestmp4, sourcemp4)
    # 获取视频信息
    video_info = get_video_info(sourcemp4)
    if not video_info or video_info['time'] == 0:
        print("视频数据存在错误，请更换raw.mp4视频")
        input("\n按回车键关闭窗口")
        sys.exit()

fps = video_info['video_fps']
scale = [video_info['width'], video_info['height']]

# 从原始视频 分离出无声视频 cuda + h264_cuvid
runffmpeg(['ffmpeg',
 '-hide_banner',
 '-ignore_unknown',
 '-vsync',
 'vfr',
 '-hwaccel',
 'cuvid',
 '-hwaccel_output_format',
 'cuda',
 '-extra_hw_frames',
 '2',
 '-c:v',
 'h264_cuvid',
 '-y',
 '-i',
 sourcemp4,
 '-an',
 '-c:v',
 'h264_nvenc',
 novoice]
,title='从原始视频 分离出无声视频')


# 从原始视频 分离出音频 cuda + h264_cuvid
runffmpeg(['ffmpeg',
 '-hide_banner',
 '-ignore_unknown',
 '-vsync',
 'vfr',
 '-hwaccel',
 'cuvid',
 '-hwaccel_output_format',
 'cuda',
 '-extra_hw_frames',
 '2',
 '-c:v',
 'h264_cuvid',
 '-y',
 '-i',
 sourcemp4,
 '-vn',
 '-c:a',
 'copy',
 m4a]
,title='从原始视频 分离出音频')

# 分离出的 m4a 转为 wav cuda + h264_cuvid
runffmpeg(['ffmpeg',
 '-hide_banner',
 '-ignore_unknown',
 '-vsync',
 'vfr',
 '-hwaccel',
 'cuvid',
 '-hwaccel_output_format',
 'cuda',
 '-extra_hw_frames',
 '2',
 '-c:v',
 'h264_cuvid',
 '-y',
 '-i',
 m4a,
 '-ac',
 '1',
 wav]
,title='分离出的 m4a 转为 wav')

# 提取最后一帧为图片 nv12 + h264_cuvid
runffmpeg(['ffmpeg',
 '-hide_banner',
 '-ignore_unknown',
 '-vsync',
 'vfr',
 '-hwaccel',
 'cuvid',
 '-hwaccel_output_format',
 'nv12',
 '-extra_hw_frames',
 '2',
 '-c:v',
 'h264_cuvid',
 '-y',
 '-sseof',
 '-3',
 '-i',
 novoice,
 '-q:v',
 '1',
 '-qmin:v',
 '1',
 '-qmax:v',
 '1',
 '-update',
 'true',
 img]
,title='提取最后一帧为图片')

# 根据图片创建 5s 的视频 nv12 +  not h264_cuvid
runffmpeg(['ffmpeg',
 '-hide_banner',
 '-ignore_unknown',
 '-vsync',
 'vfr',
 '-hwaccel',
 'cuvid',
 '-hwaccel_output_format',
 'nv12',
 '-extra_hw_frames',
 '2',
 '-y',
 '-loop',
 '1',
 '-i',
 img,
 '-vf',
 f"fps={fps},scale={scale[0]}:{scale[1]}",
 '-c:v',
 'h264_nvenc',
 '-crf',
 '13',
 '-to',
 '00:00:05',
 imgvideo]
,title='根据图片创建 5s 的视频')

# 截取 00:00:05 -- 00:00:15 nv12 +  not h264_cuvid
runffmpeg(['ffmpeg',
 '-hide_banner',
 '-ignore_unknown',
 '-vsync',
 'vfr',
 '-hwaccel',
 'cuvid',
 '-hwaccel_output_format',
 'cuda',
 '-extra_hw_frames',
 '2',
 '-c:v',
 'h264_cuvid',
 '-y',
 '-ss',
 '00:00:05',
 '-to',
 '00:00:10.500',
 '-i',
 novoice,
 '-vf',
 "setpts=2*PTS",
 '-c:v',
 'h264_nvenc',
 '-crf',
 '13',
 pianduan]
,title='截取 00:00:05 -- 00:00:15')

# imgvideo 和 pianduan 合并
srttext = f"""
file '{imgvideo}'
file '{pianduan}'
"""
with open(concat, 'w', encoding='utf-8') as f:
    f.write(srttext)
# 连接 2个视频片段 cuda +  h264_cuvid
runffmpeg(['ffmpeg',
 '-hide_banner',
 '-ignore_unknown',
 '-vsync',
 'vfr',
 '-hwaccel',
 'cuvid',
 '-hwaccel_output_format',
 'cuda',
 '-extra_hw_frames',
 '2',
 '-c:v',
 'h264_cuvid',
 '-y',
 '-f',
 'concat',
 '-safe',
 '0',
 '-i',
 concat,
 '-c:v',
 'h264_nvenc',
 '-crf',
 '13',
 '-an',
 hebing]
,title='连接 2个视频片段')

with open(srtfile, 'w', encoding='utf-8') as f:
    f.write("""
1
00:00:00,000 --> 00:00:05,780
rear seat

2
00:00:05,780 --> 00:00:08,436
In this issue we introduce electromagnetic punishment in the park

3
00:00:08,436 --> 00:00:10,132
First of all, we got an electromagnetic penalty
    """)

# 视频 音频 硬字幕合并 nv12 +  h264_cuvid
runffmpeg(['ffmpeg',
 '-hide_banner',
 '-ignore_unknown',
 '-vsync',
 'vfr',
 '-hwaccel',
 'cuvid',
 '-hwaccel_output_format',
 'nv12',
 '-extra_hw_frames',
 '2',
 '-c:v',
 'h264_cuvid',
 '-y',
 '-i',
 novoice,
 '-i',
 m4a,
 '-c:v',
 'h264_nvenc',
 '-c:a',
 'copy',
 '-vf',
 'subtitles={srtfile}',
 out_hard]
,title='视频 音频 硬字幕合并')

# 视频 硬字幕 nv12 +  h264_cuvid
runffmpeg(['ffmpeg',
 '-hide_banner',
 '-ignore_unknown',
 '-vsync',
 'vfr',
 '-hwaccel',
 'cuvid',
 '-hwaccel_output_format',
 'nv12',
 '-extra_hw_frames',
 '2',
 '-c:v',
 'h264_cuvid',
 '-y',
 '-i',
 novoice,
 '-c:v',
 'h264_nvenc',
 '-vf',
 f'subtitles={srtfile}',
 out_hard]
,title='视频 硬字幕')

# 视频 配音 软字幕 cuda +   h264_cuvid
runffmpeg(['ffmpeg',
 '-hide_banner',
 '-ignore_unknown',
 '-vsync',
 'vfr',
 '-hwaccel',
 'cuvid',
 '-hwaccel_output_format',
 'cuda',
 '-extra_hw_frames',
 '2',
 '-c:v',
 'h264_cuvid',
 '-y',
 '-i',
 novoice,
 '-i',
 m4a,
 '-i',
 srtfile,
 '-c:v',
 'h264_nvenc',
 '-c:a',
 'copy',
 '-c:s',
 'mov_text',
 '-metadata:s:s:0',
 'language=chi',
 out_soft]
,title='视频 配音 软字幕')

# 软字幕无配音 cuda + h264_cuvid
runffmpeg(["ffmpeg","-hide_banner","-ignore_unknown","-vsync","vfr","-hwaccel","cuvid","-hwaccel_output_format","cuda","-extra_hw_frames","2","-c:v","h264_cuvid","-y","-i",novoice,"-i",srtfile,"-c:v","h264_nvenc","-c:s","mov_text","-metadata:s:s:0","language=chi",out_soft],title='软字幕无配音')

# 配音无字幕
runffmpeg(["ffmpeg","-hide_banner","-ignore_unknown","-vsync","vfr","-hwaccel","cuvid","-hwaccel_output_format","cuda","-extra_hw_frames","2","-c:v","h264_cuvid","-y","-i",novoice,"-i",m4a,"-c:v","h264_nvenc","-c:a","copy",out_nosrt],title='配音无字幕')

# 加速音频
runffmpeg(["ffmpeg","-hide_banner","-ignore_unknown","-vsync","vfr","-hwaccel","cuvid","-hwaccel_output_format","cuda","-extra_hw_frames","2","-c:v","h264_cuvid","-y","-i",wav,"-af","atempo=2",wavspeedup],title='加速音频')

# mp4 转为 api
runffmpeg(["ffmpeg","-hide_banner","-ignore_unknown","-vsync","vfr","-hwaccel","cuvid","-hwaccel_output_format","nv12","-extra_hw_frames","2","-y","-i",sourcemp4,"-c:v","h264_nvenc","-c:a","aac",sourceavi],title='mp4 转为 avi')

# avi 转为 mp4
runffmpeg(["ffmpeg","-hide_banner","-ignore_unknown","-vsync","vfr","-hwaccel","cuvid","-hwaccel_output_format","nv12","-extra_hw_frames","2","-y","-i",sourceavi,"-c:v","h264_nvenc","-c:a","aac",sourceavi,".mp4"],title='avi 转为 mp4')



input("\n按回车键关闭窗口")
