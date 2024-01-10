import torch
from videotrans.util.tools import runffmpeg, set_process, delete_files, match_target_amplitude, show_popup, cut_from_video,     ms_to_time_string
import os
from videotrans.configure import config
config.current_status='ing'

if torch.cuda.is_available():
    print('CUDA 可用，如果实际使用仍提示 cuda 相关错误，请尝试升级显卡驱动')
    config.params['cuda']=True
else:
    print("当前计算机CUDA不可用")
    exit()

rootdir=os.getcwd()
tmpdir=os.path.join(rootdir, 'tmp')
if not os.path.exists(tmpdir):
    os.makedirs(tmpdir, exist_ok=True)

# 创建 ms 格式
totime = ms_to_time_string(ms=3200).replace(',', '.')
img=os.path.join(tmpdir, '1.jpg')
last_clip=os.path.join(tmpdir, 'lastclip.mp4')
mansu_clip=os.path.join(tmpdir, 'mansu.mp4')
testmp4=os.path.join(rootdir, 'test.mp4')
outmp4=os.path.join(tmpdir, 'testout.mp4')
# 创建 totime 时长的视频
# 测试截图
rs1=runffmpeg(['-y','-sseof','-3','-i',testmp4,'-vsync','0','-q:v','1','-qmin:v','1','-qmax:v','1','-update','true',f'{img}'], disable_gpu=True, no_decode=True)
print(f'test crop img:{rs1=}')


# 测试创建一定时长的视频
rs2 = runffmpeg([
    '-loop', '1', '-i', f'{img}', '-vf', f'fps=30,scale=1548:892', '-c:v', "libx264",
    '-crf', '0', '-to', f'{totime}',  '-y', f'{last_clip}'], no_decode=True)
print(f'test create videotrans from img:{rs2=}')

# 开始将 test.mp4 和 last_clip 合并为无声视频
rs3=runffmpeg(
    ['-y', '-i', testmp4, '-i', f'{last_clip}', f'-filter_complex',
     '[0:v][1:v]concat=n=2:v=1:a=0[outv]', '-map', '[outv]', '-c:v', "libx264", '-crf', '0', '-an',
     f'{outmp4}'],  de_format="nv12")
print(f'test concat 2 video:{rs3=}') 


rs4=cut_from_video(ss="0", to="00:00:00.500", source=testmp4, pts=2, out=mansu_clip)
print(f'test cut video:{rs4=}')











'''

# 处理视频 非拼接  cuda 格式 需解码 h264_cuvid
# 视频去掉音频轨道，得到无声视频
ffmpeg -hide_banner -vsync 0 -hwaccel cuvid -hwaccel_output_format cuda -c:v h264_cuvid -extra_hw_frames 2 -y -i "真实存在的视频地址，正斜杠做路径分隔符，比如 D:/1.mp4" -c:v h264_nvenc -an "D:/novoice.mp4.raw.mp4"


# 从视频截图最后一帧
ffmpeg -hide_banner -vsync 0 -y -sseof -3 -i "D:/novoice.mp4.raw.mp4" -q:v 1 -qmin:v 1 -qmax:v 1 -update true "D:/last.jpg"


# 求帧率, 输出的结果，比如 3000/100,  用 3000除以100=30，帧率即为30
ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "D:/novoice.mp4.raw.mp4"


# 获取宽和高
#执行后边命令得到宽度数字  
ffprobe -v error -select_streams "v:0" -show_entries "stream=width" -of "csv=s=x:p=0" "D:/novoice.mp4.raw.mp4"

# 执行后边命令得到高度数字
ffprobe -v error -select_streams "v:0" -show_entries "stream=height" -of "csv=s=x:p=0" "D:/novoice.mp4.raw.mp4"


# 从图片生成视频
ffmpeg -hide_banner -vsync 0 -hwaccel cuvid -hwaccel_output_format cuda -extra_hw_frames 2 -loop 1 -i "D:/last.jpg" -vf "fps=帧率数字,scale_cuda=宽度数字:高度数字" -c:v h264_nvenc -crf 18 -to 00:00:03.366 -y "D:/last_clip.mp4"


# 视频处理 拼接  nv12 格式  需解码 h264_cuvid
ffmpeg -hide_banner -vsync 0 -hwaccel cuvid -hwaccel_output_format nv12 -extra_hw_frames 2 -c:v h264_cuvid -y -i "D:/novoice.mp4.raw.mp4" -c:v h264_cuvid -i "D:/last_clip.mp4" -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[outv]" -map "[outv]" -c:v h264_nvenc -crf 18 -an "D:/novoice.mp4"



'''


