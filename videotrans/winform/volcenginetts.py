def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans.configure.config import tr
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText(tr('Test'))

    def test():

        appid = winobj.volcenginetts_appid.text().strip()
        access = winobj.volcenginetts_access.text().strip()
        cluster = winobj.volcenginetts_cluster.text().strip()
        if not appid or not access or not cluster:
            return tools.show_error(tr('Appid access and cluster are required'))
        config.params["volcenginetts_appid"] = appid
        config.params["volcenginetts_access"] = access
        config.params["volcenginetts_cluster"] = cluster
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": "通用男声",
            "filename": config.TEMP_HOME + f"/{time.time()}-volcenginetts.wav",
            "tts_type": tts.VOLCENGINE_TTS}],
                         language="zh",
                         tts_type=tts.VOLCENGINE_TTS)
        wk.uito.connect(feed)
        wk.start()
        winobj.test.setText(tr('Testing...'))

    def save():
        appid = winobj.volcenginetts_appid.text().strip()
        access = winobj.volcenginetts_access.text().strip()
        cluster = winobj.volcenginetts_cluster.text().strip()

        config.params["volcenginetts_appid"] = appid
        config.params["volcenginetts_access"] = access
        config.params["volcenginetts_cluster"] = cluster
        config.getset_params(config.params)
        winobj.close()



    from videotrans.component.set_form import VolcEngineTTSForm
    winobj = VolcEngineTTSForm()
    config.child_forms['volcenginetts'] = winobj
    winobj.update_ui()
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
