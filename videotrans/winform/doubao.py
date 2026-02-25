# 字节火山音视频字幕生成 对应 字节字幕生成渠道

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
        winobj.test.setText(
            tr("Test"))

    def test():
        appid = winobj.doubao_appid.text()
        access = winobj.doubao_access.text()
        params["doubao_appid"] = appid
        params["doubao_access"] = access
        if not appid or not access:
            tools.show_error('必须填写 Appid & Access_token')
            return
        params.save()
        winobj.test.setText(tr("Testing..."))
        task = TestSTT(parent=winobj, recogn_type=recognition.DOUBAO_API)
        task.uito.connect(feed)
        task.start()

    def save():
        appid = winobj.doubao_appid.text()
        access = winobj.doubao_access.text()
        if not appid or not access:
            tools.show_error('必须填写 Appid & Access_token')
            return
        params["doubao_appid"] = appid
        params["doubao_access"] = access
        params.save()

        winobj.close()

    from videotrans.component.set_form import DoubaoForm
    winobj = DoubaoForm()
    app_cfg.child_forms['doubao'] = winobj
    winobj.doubao_appid.setText(params.get("doubao_appid",''))
    winobj.doubao_access.setText(params.get("doubao_access",''))

    winobj.set_save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
