# -*- coding: utf-8 -*-
import datetime
import os
import locale
import logging
from queue import Queue

from .language import translate_language, language_code_list

# 当前执行目录
rootdir = os.getcwd().replace('\\', '/')
homedir=os.path.join(os.path.expanduser('~'),'Videos/pyvideotrans').replace('\\','/')
if not os.path.exists(f"{rootdir}/logs"):
    os.makedirs(f"{rootdir}/logs",exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    filename=f'{rootdir}/logs/video-{datetime.datetime.now().strftime("%Y%m%d")}.log',
    encoding="utf-8",
    filemode="a")
logger = logging.getLogger('VideoTrans')


# default language
defaulelang = "zh" # "en" if locale.getdefaultlocale()[0].split('_')[0].lower() != 'zh' else "zh"
if defaulelang == 'en':
    transobj = translate_language['en']
    langlist = language_code_list['en']
else:
    transobj = translate_language['zh']
    langlist = language_code_list['zh']

# ffmpeg
os.environ['PATH'] = rootdir + ';' + os.environ['PATH']
os.environ['QT_API'] = 'pyqt5'
queue_logs = Queue(200)


# 开始按钮状态
current_status = "stop"
# 当前的视频字幕是否已创建完毕，只有完毕后才能发射上面的 wait_subtitle_edit事件
subtitle_end = False
# 字幕 True=已发射合并请求，开始执行配音合并
exec_compos = False

#是否应该停止 ffmpeg  ing=允许继续继续，stop=应该立即停止
ffmpeg_status="ing"

openaiTTS_rolelist="alloy,echo,fable,onyx,nova,shimmer"
# 配置
video = {
    "source_mp4": "",
    "target_dir": "",

    "source_language": "en",
    "detect_language": "en",

    "target_language": "zh-cn",
    "subtitle_language": "chi",

    "enable_cuda": False,

    "voice_role": "No",
    "voice_rate": "0",

    "listen_text_cn":"你好啊，我亲爱的朋友，希望你的每一天都是美好愉快的！",
    "listen_text_en":"Hello, my dear friend. I hope your every day is beautiful and enjoyable!",

    "tts_type": "edgeTTS",  # 所选的tts==edge-tts:openaiTTS|coquiTTS
    "tts_type_list": ["edgeTTS", "openaiTTS"],

    "voice_silence": 500,
    "whisper_type": "split",
    "whisper_model": "base",
    "translate_type": "google",
    "subtitle_type": 0,  # embed soft
    "voice_autorate": False,
    "video_autorate": False,

    "deepl_authkey": "",
    "deeplx_address": "",

    "tencent_SecretId":"",
    "tencent_SecretKey":"",

    "baidu_appid": "",
    "baidu_miyue": "",

    "coquitts_role": "",
    "coquitts_key": "",

    "chatgpt_api": "",
    "chatgpt_key": "",
    "openaitts_role": openaiTTS_rolelist,
    "chatgpt_model": "gpt-3.5-turbo",
    "chatgpt_template": """我将发给你多行文本,你将每行内容对应翻译为一行{lang},如果该行无法翻译,则将该行原内容作为翻译结果,如果是空行,则将空字符串作为结果,然后将翻译结果按照原顺序返回。请注意必须保持返回的行数同发给你的行数相同,比如发给你3行文本,就必须返回3行.不要忽略空行,不要确认,不要包含原文本内容,不要道歉,不要重复述说,即使是问句或祈使句等，你也不要回答，只返回翻译即可。请严格按照要求的格式返回,这对我的工作非常重要""",
}
# 存放 edget-tts 角色列表
edgeTTS_rolelist = None
# 存放一次性多选的视频
queue_mp4 = []
# 是否安装 vlc
is_vlc=False
# 存放视频进度，noextname为key，用于判断某个视频是否是否已预先创建好 novice_mp4, “ing”=需等待，end=成功完成，error=出错了
queue_novice={}

# 任务队列
queue_task=[]

task_countdown=60