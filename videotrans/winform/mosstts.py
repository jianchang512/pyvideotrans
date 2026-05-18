def openwin():
    from pathlib import Path
    from PySide6 import QtWidgets, QtCore
    import requests

    from videotrans.configure.config import tr, app_cfg, params, TEMP_DIR, ROOT_DIR
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice

    def feed(d, role_name=''):
        if d == "ok":
            title = 'ok'
            message = 'Test Ok'
            if role_name:
                message = f'Test Ok\nRole: {role_name}'
            QtWidgets.QMessageBox.information(winobj, title, message)
        else:
            tools.show_error(d)
        winobj.local_test_btn.setText(tr("Test"))



    def _sync_params(force_refresh_roles: bool = False):
        url=winobj.clone_address.text().strip()
        if not url:
            return tools.show_error('The API URL is required.')
        params['moss_tts_url'] = url
        return url

    def save():
        winobj.hide()
        _sync_params(force_refresh_roles=True)
        params.save()
        tools.set_process(text='', type='refreshtts')
        winobj.close()


    def test_local_role():
        winobj.local_test_btn.setText(tr('Testing...'))
        _sync_params(force_refresh_roles=True)

        _rolename = next(reversed(tools.get_f5tts_role().values()))
        if not isinstance(_rolename,dict):
            return tools.show_error(tr("No reference audio {} exists",_rolename))
        rolename=_rolename.get('ref_wav')
        file=ROOT_DIR+f'/f5-tts/{rolename}'
        if not Path(file).exists():
            return tools.show_error(tr("No reference audio {} exists",file))

        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊，我的朋友们！',
            "role": rolename,
            "filename": TEMP_DIR + f"/{time.time()}-mosstts-local.wav",
            "tts_type": tts.MOSS_TTS,
        }], language="zh", tts_type=tts.MOSS_TTS)
        wk.uito.connect(lambda d, role_name=rolename: feed(d, role_name))
        wk.start()

    from videotrans.component.set_form import MossTTSForm
    winobj = MossTTSForm()
    app_cfg.child_forms['mosstts'] = winobj


    if params.get('moss_tts_url', ''):
        winobj.clone_address.setText(params.get('moss_tts_url', ''))
    winobj.set_clone.clicked.connect(save)
    winobj.local_test_btn.clicked.connect(test_local_role)
    winobj.show()