def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr,params, app_cfg
    from videotrans.util import tools
    from videotrans import recognition
    from videotrans.util.TestSTT import TestSTT
    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "ok", d[3:])
        else:
            tools.show_error(d)
        winobj.test.setText(
            tr("Test"))

    def test():
        url = winobj.parakeet_address.text().strip().strip('/')
        if not url:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        url = url.replace('/audio/transcriptions', '').strip('/')
        if not url.endswith('/v1'):
            url = 'http://' + url + '/v1'

        params["parakeet_address"] = url
        winobj.test.setText(tr("Testing..."))
        task = TestSTT(parent=winobj, recogn_type=recognition.PARAKEET)
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.parakeet_address.text().strip()
        if not url:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        url = url.replace('/audio/transcriptions', '').strip('/')
        if not url.endswith('/v1'):
            url = 'http://' + url + '/v1'

        params["parakeet_address"] = url
        params.save()
        tools.set_process(text='', type="refreshtts")
        winobj.close()



    from videotrans.component.set_form import ParakeetForm
    winobj = ParakeetForm()
    app_cfg.child_forms['parakeet'] = winobj
    winobj.update_ui()
    winobj.set_btn.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
