def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr
    from videotrans.configure import config
    from videotrans.util import tools

    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "Ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText(tr('Test'))

    def test():
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        config.params["fishtts_url"] = url
        winobj.test.setText('测试中请稍等...')
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": getrole(),
            "filename": config.TEMP_HOME + f"/{time.time()}-fishtts.wav",
            "tts_type": tts.FISHTTS}],
                         language="zh",
                         tts_type=tts.FISHTTS)
        wk.uito.connect(feed)
        wk.start()

    def getrole():
        tmp = winobj.role.toPlainText().strip()
        role = None
        if not tmp:
            return role

        for it in tmp.split("\n"):
            s = it.strip().split('#')
            if len(s) != 2:
                tools.show_error(tr("Each line must be split into two parts with #, in the format of audio name.wav#audio text content"))
                return

            role = s[0]
        config.params['fishtts_role'] = tmp
        return role

    def save():
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        role = winobj.role.toPlainText().strip()

        config.params["fishtts_url"] = url
        config.params["fishtts_role"] = role

        config.getset_params(config.params)
        tools.set_process(text='fishtts', type="refreshtts")
        winobj.close()

    from videotrans.component.set_form import FishTTSForm
    winobj = FishTTSForm()
    config.child_forms['fishtts'] = winobj
    winobj.api_url.setText(config.params.get("fishtts_url",''))
    winobj.role.setPlainText(config.params.get("fishtts_role",''))

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
