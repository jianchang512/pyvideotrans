def openwin():
    from PySide6 import QtWidgets
    from videotrans.configure.config import ROOT_DIR,tr,app_cfg,settings,params,TEMP_DIR,logger,defaulelang,HOME_DIR
    from videotrans.util import tools
    from pathlib import Path
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
        _f5roles = tools.get_f5tts_role()
        if not _f5roles:
            return tools.show_error(tr("Please set reference audio first"))
        _rolename = next(reversed(_f5roles.values()))
        if not isinstance(_rolename,dict):
            return tools.show_error(tr("No reference audio {} exists",_rolename))
        rolename=_rolename.get('ref_audio')
        file=ROOT_DIR+f'/f5-tts/{rolename}'
        if not Path(file).exists():
            return tools.show_error(tr("No reference audio {} exists",file))
        params["fishtts_url"] = url
        winobj.test.setText('测试中请稍等...')
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": rolename,
            "filename": TEMP_DIR + f"/{time.time()}-fishtts.wav",
            "tts_type": tts.FISHTTS}],
                         language="zh",
                         tts_type=tts.FISHTTS)
        wk.uito.connect(feed)
        wk.start()



    def save():
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url = 'http://' + url
        params["fishtts_url"] = url

        params.save()
        tools.set_process(text='fishtts', type="refreshtts")
        winobj.close()

    from videotrans.component.set_form import FishTTSForm
    winobj = FishTTSForm()
    app_cfg.child_forms['fishtts'] = winobj
    winobj.api_url.setText(params.get("fishtts_url",''))

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
