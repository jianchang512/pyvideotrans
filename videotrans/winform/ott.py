from videotrans.configure import config
from PySide6 import QtWidgets
from videotrans.util import tools
def openwin():
    def save():
        url = winobj.ott_address.text().strip()
        if tools.check_local_api(url) is not True:
            return
        if not url.startswith('http'):
            url = 'http://' + url
        config.params["ott_address"] = url
        config.getset_params(config.params)
        winobj.close()

    from videotrans.component import OttForm
    winobj = config.child_forms.get('ottw')
    if winobj is not None:
        winobj.show()
        winobj.raise_()
        winobj.activateWindow()
        return
    winobj = OttForm()
    config.child_forms['ottw'] = winobj
    if config.params["ott_address"]:
        winobj.ott_address.setText(config.params["ott_address"])
    winobj.set_ott.clicked.connect(save)
    winobj.show()
