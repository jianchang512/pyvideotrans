def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.util import tools

    from videotrans import recognition
    from videotrans.util.TestSTT import TestSTT
    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "ok", d[3:])
        else:
            tools.show_error(d)
        winobj.test.setText(
            '测试' if config.defaulelang == 'zh' else 'Test')

    def test():
        url = winobj.parakeet_address.text().strip().strip('/')
        if not url:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        url = url.replace('/audio/transcriptions', '').strip('/')
        if not url.endswith('/v1'):
            url = 'http://' + url + '/v1'

        config.params["parakeet_address"] = url
        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        task = TestSTT(parent=winobj, recogn_type=recognition.PARAKEET)
        task.uito.connect(feed)
        task.start()

    def save_openairecognapi():
        url = winobj.parakeet_address.text().strip()
        if not url:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        url = url.replace('/audio/transcriptions', '').strip('/')
        if not url.endswith('/v1'):
            url = 'http://' + url + '/v1'

        config.params["parakeet_address"] = url
        config.getset_params(config.params)
        winobj.close()

    def update_ui():
        if config.params["parakeet_address"]:
            winobj.parakeet_address.setText(config.params["parakeet_address"])

    from videotrans.component import ParakeetForm
    winobj = config.child_forms.get('parakeet')
    if winobj is not None:
        winobj.show()
        update_ui()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = ParakeetForm()
    config.child_forms['parakeet'] = winobj
    update_ui()
    winobj.set_btn.clicked.connect(save_openairecognapi)
    winobj.test.clicked.connect(test)
    winobj.show()
