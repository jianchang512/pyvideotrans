# -*- coding: utf-8 -*-
import queue


# 摄像头队列
camera_list=[]
# 录制中
luzhicfg={}
luzhicfg['video_running'] = False
luzhicfg['capture_thread'] = None
luzhicfg['videoFlag'] = False
luzhicfg['camera_start']=False
luzhicfg['running'] = False
luzhicfg['camindex']=-1
luzhicfg['queue'] = queue.Queue()
luzhicfg['quitFlag']=False
luzhicfg['audio_thread']=None

# 是否正在检测摄像头，如果是，则忽略，不能同时多检测
check_camera_ing=False

# 需格式化的文件数量
geshi_num=0

enable_cuda=False


