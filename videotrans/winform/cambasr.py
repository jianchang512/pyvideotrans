

def openwin():
    from videotrans.configure.config import tr, app_cfg, params
    from videotrans.util import tools

    def save():
        key = winobj.camb_api_key.text()
        params['camb_api_key'] = key
        params.save()
        winobj.close()

    from videotrans.component.set_form import CambASRForm
    winobj = CambASRForm()
    app_cfg.child_forms['cambasr'] = winobj
    winobj.camb_api_key.setText(params.get('camb_api_key', ''))
    winobj.set.clicked.connect(save)
    winobj.show()
