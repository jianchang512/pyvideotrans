import torch
from videotrans.util.tools import runffmpeg, set_process, delete_files, match_target_amplitude, show_popup, cut_from_video,     ms_to_time_string
import os
from videotrans.configure import config
config.current_status='ing'

if torch.cuda.is_available():
    print('CUDA 可用，如果实际使用仍提示 cuda 相关错误，请尝试升级显卡驱动')
else:
    print("当前计算机CUDA不可用")

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
rs1=runffmpeg(['-y','-sseof','-3','-i',testmp4,'-vsync','0','-q:v','1','-qmin:v','1','-qmax:v','1','-update','true',f'{img}'])
print(f'{rs1=}')


# 测试创建一定时长的视频
rs2 = runffmpeg([
    '-loop', '1', '-i', f'{img}', '-vf', f'fps=30,scale=1548:892', '-c:v', "libx264",
    '-crf', '0', '-to', f'{totime}', '-pix_fmt', f'yuv420p', '-y', f'{last_clip}'])
print(f'{rs2=}')

# 开始将 test.mp4 和 last_clip 合并为无声视频
rs3=runffmpeg(
    ['-y', '-i', testmp4, '-i', f'{last_clip}', f'-filter_complex',
     '[0:v][1:v]concat=n=2:v=1:a=0[outv]', '-map', '[outv]', '-c:v', "libx264", '-crf', '0', '-an',
     f'{outmp4}'])
print(f'{rs3=}') 


rs4=cut_from_video(ss="0", to="00:00:00.500", source=testmp4, pts=2, out=mansu_clip)
print(f'{rs4=}')