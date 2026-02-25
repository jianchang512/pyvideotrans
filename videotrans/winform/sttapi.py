def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.configure.config import tr,params,settings,app_cfg,logger
    from videotrans.util import tools
    from videotrans import recognition
    from videotrans.util.TestSTT import TestSTT
    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(winobj, "ok", d[3:])
        else:
            tools.show_error(d)
        winobj.test.setText(tr("Test"))

    def test():
        url = winobj.stt_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        params['stt_url'] = url
        winobj.test.setText(tr("Testing..."))
        task = TestSTT(parent=winobj, recogn_type=recognition.STT_API, model_name=winobj.stt_model.currentText())
        task.uito.connect(feed)
        task.start()

    def save():
        url = winobj.stt_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        model = winobj.stt_model.currentText()
        url = url.rstrip('/')

        params["stt_url"] = url
        params["stt_model"] = model
        params.save()
        winobj.close()

    from videotrans.component.set_form import SttAPIForm
    winobj = SttAPIForm()
    app_cfg.child_forms['sttapi'] = winobj
    winobj.stt_url.setText(params.get("stt_url",''))
    winobj.stt_model.setCurrentText(params.get("stt_model",''))
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
