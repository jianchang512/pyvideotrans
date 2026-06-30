def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure.config import tr,params,app_cfg
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    from videotrans.winform._helpers import make_setallmodels
    from videotrans.component.set_form import ZijiehuoshanForm

    winobj = ZijiehuoshanForm()
    app_cfg.child_forms['zijie'] = winobj
    winobj.update_ui()

    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test_zijiehuoshan.setText('Test')

    def test():
        key = winobj.zijiehuoshan_key.text()
        model = winobj.zijiehuoshan_model.currentText()
        if not key or not model.strip():
            return tools.show_error('API KEY and Model')
        params["zijiehuoshan_key"] = key
        params["zijiehuoshan_model"] = model
        params.save()
        winobj.test_zijiehuoshan.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.ZIJIE_INDEX)
        task.uito.connect(feed)
        task.start()

    def save_zijiehuoshan():
        params["zijiehuoshan_key"] = winobj.zijiehuoshan_key.text()
        params["zijiehuoshan_model"] = winobj.zijiehuoshan_model.currentText()
        params.save()
        winobj.close()

    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'zijiehuoshan_model', 'zijiehuoshan_model'))
    winobj.set_zijiehuoshan.clicked.connect(save_zijiehuoshan)
    winobj.test_zijiehuoshan.clicked.connect(test)
    winobj.show()
