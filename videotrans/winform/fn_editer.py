from videotrans.configure import config

# 字幕编辑
def openwin():
    from videotrans.component import SubtitleEditer
    try:
        winobj = SubtitleEditer()
        config.child_forms['edier_win']=winobj
        winobj.show()
    except Exception as e:
        print(e)
