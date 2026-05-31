# 对应 豆包语音合成大模型2.0

def openwin():
    from PySide6 import QtWidgets
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans.configure.config import tr,app_cfg, params
    from videotrans.configure import config
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText(tr('Test'))

    def test():

        appid = winobj.doubao2_appid.text().strip()
        access = winobj.doubao2_access.text().strip()

        if not appid or not access:
            return tools.show_error(tr('Appid access and cluster are required'))
        params["doubao2_appid"] = appid
        params["doubao2_access"] = access
        params.save()
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": "Vivi 2.0",
            "filename": config.TEMP_DIR + f"/{time.time()}-doubao2.wav",
            "tts_type": tts.DOUBAO2_TTS}],
                         language="zh",
                         tts_type=tts.DOUBAO2_TTS)
        wk.uito.connect(feed)
        wk.start()
        winobj.test.setText(tr('Testing...'))

    def save():
        appid = winobj.doubao2_appid.text().strip()
        access = winobj.doubao2_access.text().strip()


        params["doubao2_appid"] = appid
        params["doubao2_access"] = access
        params.save()
        winobj.close()



    from videotrans.component.set_form import Doubao2TTSForm
    winobj = Doubao2TTSForm()
    app_cfg.child_forms['doubao2'] = winobj
    winobj.update_ui()
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
