# 测试 CUDA 可用性
# 找到一个 h264 编码的mp4视频，重命名为 raw.mp4，然后复制到和当前脚本同目录下，然后执行测试

import json
import subprocess
import torch
import os
import sys
from torch.backends import cudnn

# ffmpeg
rootdir = os.getcwd()
tmpdir = os.path.join(rootdir, 'tmp')
if sys.platform == 'win32':
    os.environ['PATH'] = rootdir + f';{rootdir}\\ffmpeg;' + os.environ['PATH']
else:
    os.environ['PATH'] = rootdir + f':{rootdir}/ffmpeg:' + os.environ['PATH']

if torch.cuda.is_available():
    print('CUDA is ok')
else:
    print("no CUDA environ")
    input("\nPress enter for close")
    sys.exit()
if cudnn.is_available() and cudnn.is_acceptable(torch.tensor(1.).cuda()):
    print('cudnn is ok')
else:
    print('no cudnn  ')
    input("\nPress enter for close")
    sys.exit()

result = subprocess.run(['ffmpeg', '-hwaccels'], text=True, stdout=subprocess.PIPE)
print(f'Accels:\n{result.stdout}')

if not os.path.exists(tmpdir):
    os.makedirs(tmpdir, exist_ok=True)

# 原始视频
sourcemp4 = rootdir + "/raw.mp4"
sourceavi = rootdir + "/raw.mp4.avi"
if not os.path.exists(sourcemp4):
    print('\ncopy a video rename raw.mp4, and paster to here')
    input("\nPress enter for close")
    sys.exit()


def runffmpeg(cmd, *, title=""):
    p = subprocess.Popen(cmd,
                         stdout=subprocess.PIPE,
                         encoding="utf-8",
                         stderr=subprocess.PIPE)
    outs, errs = p.communicate()
    if p.returncode == 0:
        print(f'\n[OK] {title}:\n{cmd=}\n')
        return True

    print("\n\n******Its Error*******")
    print(f'\n[Error] {title}\n')
    print(f'{cmd=}')
    print(str(errs))
    print("\n******Error*******\n")

    # for (i, it) in enumerate(cmd):
    #    if it == '-hwaccel' and cmd[i] == 'cuda':
    #        print(f'hwaccel_output_format=cuda Dont Support, But hwaccel_output_format=nv12 is OK')
    #        break

    input("\nPress enter for close")
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


def test_cuda(libx264="libx264"):
    # 从视频中截取的图片
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
    # 从视频中截取的片段
    pianduan = os.path.join(tmpdir, 'pianduan.mp4')

    # 图片视频片段和截取的片段合并

    # 获取视频信息
    video_info = get_video_info(sourcemp4)
    if not video_info or video_info['time'] == 0:
        print("The video is error,please replace")
        input("\nPress enter will close")
        sys.exit()

    print(f"start test  ...")
    if video_info['video_codec_name'] != 'h264' or video_info['audio_codec_name'] != 'aac':
        # 转换
        tmptestmp4 = os.path.join(rootdir, 'tmptest.mp4')
        accel_pre = ['ffmpeg',
                     '-hide_banner',
                     '-ignore_unknown',
                     '-vsync',
                     'vfr',
                     '-extra_hw_frames',
                     '2']
        runffmpeg(accel_pre + [
            '-y',
            '-i',
            sourcemp4,
            '-c:v',
            libx264,
            '-c:a',
            'aac',
            tmptestmp4]
                  , title="raw.mp4格式不正确，请确保是h264编码的mp4视频")
        os.unlink(sourcemp4)
        os.rename(tmptestmp4, sourcemp4)
        # 获取视频信息
        video_info = get_video_info(sourcemp4)
        if not video_info or video_info['time'] == 0:
            print("The video is error,please replace")
            input("\nPress enter will close")
            sys.exit()

    fps = video_info['video_fps']
    scale = [video_info['width'], video_info['height']]

    # 从原始视频 分离出无声视频 cuda + h264_cuvid
    accel_pre = ['ffmpeg',
                 '-hide_banner',
                 '-ignore_unknown',
                 '-vsync',
                 'vfr',
                 '-extra_hw_frames',
                 '2']
    runffmpeg(accel_pre + [

        '-y',
        '-i',
        sourcemp4,
        '-an',
        '-c:v',
        libx264,
        novoice]
              , title='从原始视频 分离出无声视频')

    # 从原始视频 分离出音频 cuda + h264_cuvid
    accel_pre = ['ffmpeg',
                 '-hide_banner',
                 '-ignore_unknown',
                 '-vsync',
                 'vfr',
                 '-extra_hw_frames',
                 '2']
    runffmpeg(accel_pre + [

        '-y',
        '-i',
        sourcemp4,
        '-vn',
        '-c:a',
        'aac',
        m4a]
              , title='从原始视频 分离出音频')

    # 分离出的 m4a 转为 wav cuda + h264_cuvid
    accel_pre = ['ffmpeg',
                 '-hide_banner',
                 '-ignore_unknown',
                 '-vsync',
                 'vfr',
                 '-extra_hw_frames',
                 '2']
    runffmpeg(accel_pre + [

        '-y',
        '-i',
        m4a,
        '-ac',
        '1',
        wav]
              , title='分离出的 m4a 转为 wav')

    # 截取 00:00:05 -- 00:00:15 nv12 +  not h264_cuvid
    accel_pre = ['ffmpeg',
                 '-hide_banner',
                 '-ignore_unknown',
                 '-vsync',
                 'vfr',
                 '-extra_hw_frames',
                 '2']
    runffmpeg(accel_pre + [

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
        libx264,
        '-crf',
        '13',
        pianduan]
              , title='截取 00:00:05 -- 00:00:15')

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
First of all, we got an electromagnetic penalty""")
    if sys.platform == 'win32':
        hardfile = os.path.basename(srtfile)
    else:
        hardfile = srtfile
    # 视频 音频 硬字幕合并 nv12 +  h264_cuvid
    os.chdir(os.path.dirname(srtfile))
    accel_pre = ['ffmpeg',
                 '-hide_banner',
                 '-ignore_unknown',
                 '-vsync',
                 'vfr',
                 '-extra_hw_frames',
                 '2']
    runffmpeg(accel_pre + [

        '-y',
        '-i',
        novoice,
        '-i',
        m4a,
        '-c:v',
        libx264,
        '-c:a',
        'aac',
        '-vf',
        f'subtitles={hardfile}',
        out_hard]
              , title='视频 音频 硬字幕合并')

    # 视频 硬字幕 nv12 +  h264_cuvid
    accel_pre = ['ffmpeg',
                 '-hide_banner',
                 '-ignore_unknown',
                 '-vsync',
                 'vfr',
                 '-extra_hw_frames',
                 '2']
    runffmpeg(accel_pre + [

        '-y',
        '-i',
        novoice,
        '-c:v',
        libx264,
        '-vf',
        f'subtitles={hardfile}',
        out_hard]
              , title='视频 硬字幕')

    # 视频 配音 软字幕 cuda +   h264_cuvid
    accel_pre = ['ffmpeg',
                 '-hide_banner',
                 '-ignore_unknown',
                 '-vsync',
                 'vfr',
                 '-extra_hw_frames',
                 '2'
                 ]
    runffmpeg(accel_pre + [

        '-y',
        '-i',
        novoice,
        '-i',
        m4a,
        '-i',
        srtfile,
        '-c:v',
        libx264,
        '-c:a',
        'aac',
        '-c:s',
        'mov_text',
        '-metadata:s:s:0',
        'language=chi',
        out_soft]
              , title='视频 配音 软字幕')

    # 软字幕无配音 cuda + h264_cuvid
    accel_pre = ["ffmpeg", "-hide_banner",
                 "-ignore_unknown", "-vsync", "vfr",
                 "-extra_hw_frames", "2"]
    runffmpeg(
        accel_pre + ["-y", "-i", novoice, "-i", srtfile, "-c:v", libx264, "-c:s", "mov_text",
                     "-metadata:s:s:0", "language=chi", out_soft], title='软字幕无配音')

    # 配音无字幕
    accel_pre = ["ffmpeg", "-hide_banner",
                 "-ignore_unknown", "-vsync", "vfr",
                 "-extra_hw_frames", "2"]
    runffmpeg(accel_pre + ["-y", "-i", novoice, "-i", m4a, "-c:v", libx264, "-c:a", "aac",
                           out_nosrt], title='配音无字幕')

    # 加速音频
    accel_pre = ["ffmpeg", "-hide_banner",
                 "-ignore_unknown", "-vsync", "vfr",

                 "-extra_hw_frames", "2"]
    runffmpeg(accel_pre + ["-y", "-i", wav, "-af", "atempo=2", wavspeedup], title='加速音频')

    # mp4 转为 api
    accel_pre = ["ffmpeg", "-hide_banner",
                 "-ignore_unknown", "-vsync", "vfr",
                 "-extra_hw_frames", "2", ]
    runffmpeg(accel_pre + ["-y", "-i", sourcemp4, "-c:v", libx264, "-c:a", "aac", sourceavi], title='mp4 转为 avi')

    # avi 转为 mp4
    accel_pre = ["ffmpeg", "-hide_banner",
                 "-ignore_unknown", "-vsync", "vfr",
                 "-extra_hw_frames", "2", ]
    runffmpeg(accel_pre + ["-y", "-i", sourceavi, "-c:v", libx264, "-c:a", "aac", f"{sourceavi}.mp4"],
              title='avi 转为 mp4')


test_cuda(libx264='h264_nvenc')
test_cuda(libx264='h264_qsv')
test_cuda(libx264='h264_vaapi')
test_cuda(libx264='h264_videotoolbox')
