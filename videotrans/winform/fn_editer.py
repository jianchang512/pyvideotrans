from videotrans.configure import config


# 字幕编辑
def openwin():
    from videotrans.component import SubtitleEditer
    try:
        winobj = config.child_forms.get('subtitle_editer')
        if winobj is not None:
            winobj.show()
            winobj.raise_()
            winobj.activateWindow()
            return
        winobj = SubtitleEditer()
        config.child_forms['subtitle_editer'] = winobj
        winobj.show()
    except Exception as e:
        print(e)
