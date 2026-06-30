from PySide6 import QtWidgets
from videotrans.configure.config import tr
from videotrans.util import tools


def make_feed_translator(form, test_btn_name):
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(form, "OK", d[3:])
        getattr(form, test_btn_name).setText(tr("Test"))
    return feed


def make_feed_stt(form, test_btn_name):
    def feed(d):
        if d.startswith("ok"):
            QtWidgets.QMessageBox.information(form, "ok", d[3:])
        else:
            tools.show_error(d)
        getattr(form, test_btn_name).setText(tr("Test"))
    return feed


def make_feed_tts(form, test_btn_name, success_msg="Test Ok"):
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(form, "ok", success_msg)
        else:
            tools.show_error(d)
        getattr(form, test_btn_name).setText(tr("Test"))
    return feed


def make_setallmodels(form, model_widget_name, settings_key):
    from videotrans.configure.config import settings
    def setallmodels():
        t = form.edit_allmodels.toPlainText().strip().replace('\uff0c', ',').rstrip(',')
        model_widget = getattr(form, model_widget_name)
        current_text = model_widget.currentText()
        model_widget.clear()
        model_widget.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            model_widget.setCurrentText(current_text)
        settings[settings_key] = t
        settings.save()
    return setallmodels
