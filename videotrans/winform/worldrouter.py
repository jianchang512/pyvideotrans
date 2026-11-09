def openwin():
    from pathlib import Path
    from videotrans import translator
    from videotrans.configure.config import params, tr
    from videotrans.util.help_misc import show_error
    from videotrans.util.TestSrtTrans import TestSrtTrans
    from videotrans.winform import get_cls
    from videotrans.winform._helpers import make_feed_translator, make_setallmodels

    winobj = get_cls(Path(__file__).stem)()
    winobj.update_ui()
    feed = make_feed_translator(winobj, 'test')

    def store_config():
        key = winobj.worldrouter_key.text().strip()
        model = winobj.worldrouter_model.currentText().strip()
        if not key:
            show_error(tr("Please input Secret"))
            return False
        if not model:
            show_error(tr("Please select a model"))
            return False
        if not winobj.max_token.hasAcceptableInput():
            show_error(tr("Maximum output token") + ': 1 - 1048576')
            return False
        params['worldrouter_key'] = key
        params['worldrouter_model'] = model
        params['worldrouter_max_token'] = winobj.max_token.text().strip()
        params.save()
        return True

    def test():
        if not store_config():
            return
        winobj.test.setText(tr("Testing..."))
        winobj.test.setEnabled(False)
        task = TestSrtTrans(parent=winobj, translator_type=translator.WORLDROUTER_INDEX)
        task.uito.connect(feed)
        task.finished.connect(lambda: winobj.test.setEnabled(True))
        task.finished.connect(task.deleteLater)
        task.start()

    def save():
        if store_config():
            winobj.close()

    winobj.set.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.edit_allmodels.textChanged.connect(make_setallmodels(winobj, 'worldrouter_model', 'worldrouter_model'))
    return winobj
