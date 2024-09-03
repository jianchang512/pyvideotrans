from videotrans.configure import config
from videotrans.recognition import OPENAI_WHISPER, FASTER_WHISPER


# 字幕编辑
def open():
    from videotrans.component import SubtitleEditer
    try:
        edier_win = SubtitleEditer()
        config.child_forms['edier_win']=edier_win
        edier_win.show()
    except Exception as e:
        print(e)
