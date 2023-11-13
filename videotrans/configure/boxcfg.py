import logging
# 当前执行目录
import os
import queue

rootdir = os.getcwd().replace('\\', '/')
logging.basicConfig(
    level=logging.INFO,
    filename=f'{rootdir}/video.log',
    encoding="utf-8",
    filemode="a")
logger = logging.getLogger('boxtools')
# ffmpeg
os.environ['PATH'] = rootdir + ';' + os.environ['PATH']
homedir=os.path.join(os.path.expanduser('~'),'Videos/pyvideotrans').replace('\\','/')
#  名称: google翻译代码and语音识别代码，字幕语言代码，百度翻译代码，deep代码
lang_code={
        "中文简": ['zh-cn', 'chi','zh','ZH'],
        "中文繁": ['zh-tw', 'chi','cht','ZH'],
        "英语": ['en', 'eng','en','EN-US'],
        "法语": ['fr', 'fre','fra','FR'],
        "德语": ['de', 'ger','de','DE'],
        "日语": ['ja', 'jpn','jp','JA'],
        "韩语": ['ko', 'kor','kor','KO'],
        "俄语": ['ru', 'rus','ru','RU'],
        "西班牙语": ['es', 'spa','spa','ES'],
        "泰国语": ['th', 'tha','th','No'],
        "意大利语": ['it', 'ita','it','IT'],
        "葡萄牙语": ['pt', 'por','pt','PT'],
        "越南语": ['vi', 'vie','vie','No'],
        "阿拉伯语": ['ar', 'are','ara','No']
    }

# 前台通用配置
cfg={}
# 前台队列

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

check_camera_ing=False
enable_cuda=False


