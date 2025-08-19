def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText('测试')

    def test():

        appid = winobj.volcenginetts_appid.text().strip()
        access = winobj.volcenginetts_access.text().strip()
        cluster = winobj.volcenginetts_cluster.text().strip()
        if not appid or not access or not cluster:
            return tools.show_error('必须填写 appid access 和 cluster', False)
        config.params["volcenginetts_appid"] = appid
        config.params["volcenginetts_access"] = access
        config.params["volcenginetts_cluster"] = cluster
        from videotrans import tts
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": "通用男声",
            "filename": config.TEMP_HOME + f"/test-volcenginetts.wav",
            "tts_type": tts.VOLCENGINE_TTS}],
                         language="zh",
                         tts_type=tts.VOLCENGINE_TTS)
        wk.uito.connect(feed)
        wk.start()
        winobj.test.setText('测试中请稍等...')

    def save():
        appid = winobj.volcenginetts_appid.text().strip()
        access = winobj.volcenginetts_access.text().strip()
        cluster = winobj.volcenginetts_cluster.text().strip()

        config.params["volcenginetts_appid"] = appid
        config.params["volcenginetts_access"] = access
        config.params["volcenginetts_cluster"] = cluster
        config.getset_params(config.params)
        winobj.close()

    def update_ui():

        if config.params["volcenginetts_appid"]:
            winobj.volcenginetts_appid.setText(config.params["volcenginetts_appid"])
        if config.params["volcenginetts_access"]:
            winobj.volcenginetts_access.setText(config.params["volcenginetts_access"])
        if config.params["volcenginetts_cluster"]:
            winobj.volcenginetts_cluster.setText(config.params["volcenginetts_cluster"])

    from videotrans.component import VolcEngineTTSForm
    winobj = config.child_forms.get('volcenginettsw')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = VolcEngineTTSForm()
    config.child_forms['volcenginettsw'] = winobj
    update_ui()
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
