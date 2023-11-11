# -*- coding: utf-8 -*-
import os
import locale
import logging

from .language import translate_language, language_code_list

# 当前执行目录
rootdir = os.getcwd().replace('\\', '/')
logging.basicConfig(
    level=logging.INFO,
    filename=f'{rootdir}/video.log',
    encoding="utf-8",
    filemode="a")
logger = logging.getLogger('VideoTrans')

# default language
defaulelang = "en" if locale.getdefaultlocale()[0].split('_')[0].lower() != 'zh' else "zh"
if defaulelang == 'en':
    transobj = translate_language['en']
    langlist = language_code_list['en']
else:
    transobj = translate_language['zh']
    langlist = language_code_list['zh']



# ffmpeg
os.environ['PATH'] = rootdir + ';' + os.environ['PATH']




# 开始按钮状态
current_status = "stop"
# True=已发射合并请求，开始执行配音合并
exec_compos=False
# 当前的视频是否已创建完毕，只有完毕后才能发射上面的 wait_subtitle_edit事件
subtitle_end=False
# 配置
video = {
    "source_mp4": "",
    "target_dir": "",

    "source_language": "en",
    "detect_language": "en",

    "target_language": "zh-cn",
    "subtitle_language": "chi",

    "enable_cuda":False,

    "voice_role": "No",
    "voice_rate": "0",

    "voice_silence": 500,
    "whisper_model": "base",
    "translate_type": "google",
    "subtitle_type": 0,  # embed soft
    "voice_autorate": False,

    "deepl_authkey":"",

    "baidu_appid":"",
    "baidu_miyue":"",

    "chatgpt_api":"",
    "chatgpt_key":"",
    "chatgpt_model":"gpt-3.5-turbo",
    "chatgpt_template":"""You have been sent a subtitle srt file. Please translate the text inside into natural and fluent {lang}, without any translation tone. Make sure to maintain the original format and line breaks after translation. Do not translate or delete the number and time formats, keep them as they are. For example:
    
1
00:00:01,123 --> 00:00:10,345

Keep lines like this as they are, without translation or deletion,it is very important for my job. Do not reply to this message.""",
}
voice_list = None

queue=[]