# -*- coding: utf-8 -*-
import os
import locale
import logging
from queue import Queue

from .language import translate_language, language_code_list

# 当前执行目录
rootdir = os.getcwd().replace('\\', '/')
homedir=os.path.join(os.path.expanduser('~'),'Videos/pyvideotrans').replace('\\','/')
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

    "tts_type": "edgeTTS",  # 所选的tts==edge-tts:openaiTTS|coquiTTS
    "tts_type_list": ["edgeTTS", "openaiTTS"],

    "voice_silence": 500,
    "whisper_type": "split",
    "whisper_model": "base",
    "translate_type": "google",
    "subtitle_type": 0,  # embed soft
    "voice_autorate": False,

    "deepl_authkey": "",

    "baidu_appid": "",
    "baidu_miyue": "",

    "coquitts_role": "",
    "coquitts_key": "",

    "chatgpt_api": "",
    "chatgpt_key": "",
    "openaitts_role": openaiTTS_rolelist,
    "chatgpt_model": "gpt-3.5-turbo",
    "chatgpt_template": """我将发给你一段以 "####" 连接的文本，你将文本翻译为{lang}，并保持以 "####" 连接的相同方式返回，发给你的文本中有几处 "####" ，翻译后的返回也必须有几处"####"。并且"####"数量必须同原始文本中相同。
例子:
我是一个地球人####我喜欢喝咖啡####他是火星人，他不喜欢。
I am an Earthling #### I like to drink coffee #### He is a Martian, he does not like it。

按照原 "####" 格式返回对我的工作非常非常重要，请必须严格按照此格式返回，如果某文字无法翻译，直接返回该文字原文。不要确认,不要显示原始文本，不要道歉，仅返回处理后的翻译正文
    """,
}
# 存放 edget-tts 角色列表
edgeTTS_rolelist = None
# 存放一次性多选的视频
queue_mp4 = []
# 是否安装 vlc
is_vlc=False
# 存放视频进度，noextname为key，用于判断某个视频是否是否已预先创建好 novice_mp4, “ing”=需等待，end=成功完成，error=出错了
queue_novice={}