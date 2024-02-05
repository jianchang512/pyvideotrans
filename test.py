import re

from videotrans.configure import config
from videotrans.util import tools
from videotrans.task.trans_create import TransCreate

file="C:/Users/c1/Videos/tmp.srt"

config.defaulelang="zh"
print(config.rev_langlist)
config.params['source_language']="英语"
config.params['target_language']="中文简"

obj=TransCreate({"source_mp4":"C:/Users/c1/Videos/1.mp4","app_mode":"biaozhun"})

obj.save_srt_target(tools.get_subtitle_from_srt(file),'ceshi.srt')