def openwin():
    import json
    import os
    from pathlib import Path

    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.configure.config import tr
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans import translator
    def feed(d):
        if not d.startswith("ok"):
            tools.show_error(d)
        else:
            QtWidgets.QMessageBox.information(winobj, "OK", d[3:])
        winobj.test.setText(tr("Test"))

    def test():
        key = winobj.gemini_key.text()
        model = winobj.model.currentText()
        os.environ['GOOGLE_API_KEY'] = key
        config.params["gemini_model"] = model
        config.params["gemini_key"] = key

        ttsmodel = winobj.ttsmodel.currentText()
        config.params["gemini_ttsmodel"] = ttsmodel

        config.getset_params(config.params)
        winobj.test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=winobj, translator_type=translator.GEMINI_INDEX)
        task.uito.connect(feed)
        task.start()

    def save():
        key = winobj.gemini_key.text()
        model = winobj.model.currentText()
        gemini_srtprompt = winobj.gemini_srtprompt.toPlainText()

        config.params["gemini_model"] = model
        config.params["gemini_key"] = key

        ttsmodel = winobj.ttsmodel.currentText()
        config.params["gemini_ttsmodel"] = ttsmodel


        with Path(config.ROOT_DIR + f'/videotrans/prompts/recogn/gemini_recogn.txt').open('w', encoding='utf-8') as f:
            f.write(gemini_srtprompt)
        config.getset_params(config.params)
        winobj.close()

    def setallmodels():
        t = winobj.edit_allmodels.toPlainText().strip().replace('，', ',').rstrip(',')
        current_text = winobj.model.currentText()
        winobj.model.clear()
        winobj.model.addItems([x for x in t.split(',') if x.strip()])
        if current_text:
            winobj.model.setCurrentText(current_text)
        config.settings['gemini_model'] = t
        with open(config.ROOT_DIR + '/videotrans/cfg.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(config.settings, ensure_ascii=False))



    from videotrans.component import GeminiForm

    winobj = GeminiForm()
    config.child_forms['gemini'] = winobj
    winobj.update_ui()
    winobj.set_gemini.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(setallmodels)
    winobj.show()
