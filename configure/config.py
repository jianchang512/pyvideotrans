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
wait_subtitle_edit=False
# 配置
video = {
    "source_mp4": "",
    "target_dir": "",

    "source_language": "en",
    "detect_language": "en",

    "target_language": "zh-cn",
    "subtitle_language": "chi",

    "voice_role": "No",
    "voice_rate": "0",

    "voice_silence": 500,
    "whisper_model": "base",
    "translate_type": "google",
    "subtitle_type": 0,  # embed soft
    "voice_autorate": False,

    "baidu_appid":"",
    "baidu_miyue":"",
    "chatgpt_key":"",
}
voice_list = None
