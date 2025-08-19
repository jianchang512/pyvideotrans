def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.TestSrtTrans import TestSrtTrans
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText('测试' if config.defaulelang == 'zh' else 'Test')

    def save():
        appid = winobj.ali_id.text()
        miyue = winobj.ali_key.text()
        config.params["ali_id"] = appid
        config.params["ali_key"] = miyue
        config.getset_params(config.params)
        winobj.close()

    def test():
        appid = winobj.ali_id.text()
        miyue = winobj.ali_key.text()
        if not appid or not miyue:
            return tools.show_error(
                '必须填写 AccessKey ID 和 AccessKey Secret 等信息' if config.defaulelang == 'zh' else 'Please input AccessKey ID and AccessKey Secret',
                False)
        config.params["ali_id"] = appid
        config.params["ali_key"] = miyue

        winobj.test.setText('测试中请稍等...' if config.defaulelang == 'zh' else 'Testing...')
        from videotrans import translator
        task = TestSrtTrans(parent=winobj, translator_type=translator.ALI_INDEX)
        task.uito.connect(feed)
        task.start()

    from videotrans.component import AliForm
    winobj = config.child_forms.get('aliw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = AliForm()
    config.child_forms['aliw'] = winobj
    if config.params["ali_id"]:
        winobj.ali_id.setText(config.params["ali_id"])
    if config.params["ali_key"]:
        winobj.ali_key.setText(config.params["ali_key"])
    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
