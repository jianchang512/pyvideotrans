# 对应 豆包语音合成

def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
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
        params["volcenginetts_appid"] = appid
        params["volcenginetts_access"] = access
        params["volcenginetts_cluster"] = cluster
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": "通用男声",
            "filename": TEMP_DIR + f"/{time.time()}-volcenginetts.wav",
            "tts_type": tts.DOUBAO_TTS}],
                         language="zh",
                         tts_type=tts.DOUBAO_TTS)
        wk.uito.connect(feed)
        wk.start()
        winobj.test.setText(tr('Testing...'))

    def save():
        appid = winobj.volcenginetts_appid.text().strip()
        access = winobj.volcenginetts_access.text().strip()
        cluster = winobj.volcenginetts_cluster.text().strip()

        params["volcenginetts_appid"] = appid
        params["volcenginetts_access"] = access
        params["volcenginetts_cluster"] = cluster
        params.save()
        winobj.close()



    from videotrans.component.set_form import VolcEngineTTSForm
    winobj = VolcEngineTTSForm()
    app_cfg.child_forms['volcenginetts'] = winobj
    winobj.update_ui()
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
