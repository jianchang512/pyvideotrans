import os
import re
import shutil

from moviepy.editor import VideoFileClip, clips_array,concatenate_videoclips
from moviepy.video.fx.speedx import speedx
import numpy as np
from moviepy.video.VideoClip import ImageClip, TextClip


# 视频末尾延长 duration ms
def novoicemp4_add_time(duration):
    duration=duration/1000
    out="C:/Users/c1/Videos/out.mp4"
    novoice_mp4="C:/Users/c1/Videos/novoice.mp4"
    last_frame_image = "C:/Users/c1/Videos/last.png"
    # 提取视频1.mp4的最后一帧为图片1.jpg
    video_clip = VideoFileClip(novoice_mp4)
    video_clip.save_frame(last_frame_image, t=video_clip.duration-0.1)
    # 创建一个静态图像的视频剪辑，确保分辨率与原视频一致
    # static_clip = ImageClip(last_frame_image, duration=video_clip.duration)
    static_clip = ImageClip(last_frame_image, duration=video_clip.duration)


    # 设置生成的2.mp4时长为10秒
    video2_clip = clips_array([[static_clip]])
    video2_clip = video2_clip.set_duration(duration)

    # 将整个视频变为静态图片序列
    video2_clip = video2_clip.fx(lambda x: x.resize(newsize=(x.w, x.h)))


    # 写入视频文件
    video2_clip.write_videofile(out, codec="libx264", audio=False,fps=video_clip.fps)

def cut_and_composite(*,start=None,clip=None,end=None,pts=1):
    out="C:/Users/c1/Videos/out-yanchang.mp4"
    novoice_mp4="C:/Users/c1/Videos/novoice.mp4"
    # 读取原视频1.mp4
    video_clip1 = VideoFileClip(novoice_mp4)

    # 剪切第1245毫秒到2455毫秒的部分为2.mp4
    cut_clip = video_clip1.subclip(clip[0]/1000, clip[1]/1000 if clip[1] else video_clip1.duration)

    # 将2.mp4慢放以调整时长为20秒
    slow_clip = cut_clip.fx(speedx, round(1/pts,1))

    # 获取1.mp4中除了特定时间段外的部分
    cms=[]
    if start:
        part1 = video_clip1.subclip(start[0]/1000, start[1]/1000)
        cms.append(part1)
    cms.append(slow_clip)
    if end:
        part2 = video_clip1.subclip(end[0]/1000, end[1]/1000 if end[1] else video_clip1.duration)
        cms.append(part2)

    # 组合视频
    final_clip = concatenate_videoclips(cms,method='compose')

    # 将组合后的视频写入为文件，保持原始分辨率和质量
    final_clip.write_videofile(novoice_mp4, codec="libx264", audio=False, bitrate="5000k", threads=4)


video_path = "C:/Users/c1/Videos/11.mp4"
audio_path = "C:/Users/c1/Videos/22/1.wav"
subtitles_path = "C:/Users/c1/Videos/22/1.srt"
shutil.copy2(video_path,"C:/Users/c1/Videos/1111.mp4")