

def openwin(init_show_type=None):
    from videotrans.configure.config import tr,logs
    from videotrans.configure import config
    if not init_show_type:
        init_show_type=config.params.get("f5tts_ttstype",'F5-TTS')
    from pathlib import Path

    from PySide6 import QtWidgets

    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans import tts
    # 每个渠道的名字 # NAMES=['F5-TTS', 'Spark-TTS', 'Index-TTS', 'Dia-TTS','VoxCPM-TTS']
    NAMES=config.F5_TTS_WINFORM_NAMES
    # 根据名字对应 渠道类型
    TTS_TYPE_LIST={
        NAMES[0]:tts.F5_TTS,
        NAMES[1]:tts.SPARK_TTS,
        NAMES[2]:tts.INDEX_TTS,
        NAMES[3]:tts.DIA_TTS,
        NAMES[4]:tts.VOXCPM_TTS,
    }

    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "Ok", "Test Ok")
        else:
            tools.show_error(d)

        winobj.test.setText(tr('Test'))

    # URL 输入框变化时更新url地址
    def _change_byurl(url):
        name=winobj.ttstype.currentText()
        config.params[config.get_key_byf5tts(name)]=url

    # 下拉框变化时根据name对应名字，取出url给api_url文本框
    def _change_bytype(name):
        url=config.get_url_byf5tts(name)
        winobj.api_url.setText(url)

    def _save_url_bytype():
        # 每个渠道的名字 # NAMES=['F5-TTS', 'Spark-TTS', 'Index-TTS', 'Dia-TTS','VoxCPM-TTS']
        url = winobj.api_url.text().strip()
        if not url.startswith('http'):
            url=f'http://{url}'
        name=winobj.ttstype.currentText()
        config.params[config.get_key_byf5tts(name)]=url



    def test():
        index_tts_version = winobj.index_tts_version.currentIndex()
        role = winobj.role.toPlainText().strip()
        if not role:
            tools.show_error(tr('Please input reference audio path'))
            return
        role_test = getrole()
        if not role_test:
            return
        is_whisper = winobj.is_whisper.isChecked()
        # 通用
        config.params["f5tts_is_whisper"] = is_whisper
        config.params["index_tts_version"] = index_tts_version
        config.params["f5tts_role"] = role

        # 当前类型显示名字，用于默认显示，内容如 config.F5_TTS_WINFORM_NAMES
        show_ttstype_name=  winobj.ttstype.currentText()
        config.params["f5tts_ttstype"]=show_ttstype_name
        _save_url_bytype()

        config.getset_params(config.params)

        winobj.test.setText(tr('Testing...'))
        import time
        print(f'{TTS_TYPE_LIST[show_ttstype_name]=}')
        wk = ListenVoice(parent=winobj,
                         queue_tts=[{"text": '你好啊我的朋友', "role": role_test, "filename": config.TEMP_HOME + f"/{time.time()}-{show_ttstype_name}.wav", "tts_type": TTS_TYPE_LIST[show_ttstype_name]}],
                         language="zh",
                         tts_type=TTS_TYPE_LIST[show_ttstype_name])
        wk.uito.connect(feed)
        wk.start()

    def getrole():
        tmp = winobj.role.toPlainText().strip()
        role = None
        if not tmp:
            return role

        for it in tmp.split("\n"):
            s = it.strip().split('#')
            if len(s) != 2:
                tools.show_error(tr("Each line must be split into two parts with #, in the format of audio name.wav#audio text content"))
                return
            elif not Path(config.ROOT_DIR + f'/f5-tts/{s[0]}').is_file():
                tools.show_error(tr("Please save the audio file in the {}/f5-tts directory",config.ROOT_DIR))
                return
            role = s[0]
        config.params['f5tts_role'] = tmp
        return role

    def save():

        index_tts_version = winobj.index_tts_version.currentIndex()
        role = winobj.role.toPlainText().strip()
        is_whisper = winobj.is_whisper.isChecked()

        config.params["f5tts_role"] = role
        config.params["f5tts_is_whisper"] = is_whisper
        config.params["index_tts_version"] = index_tts_version

        show_ttstype_name=  winobj.ttstype.currentText()
        config.params["f5tts_ttstype"]=show_ttstype_name
        _save_url_bytype()


        config.getset_params(config.params)
        tools.set_process(text='f5tts', type="refreshtts")
        winobj.close()

    from videotrans.component.set_form import F5TTSForm
    Path(config.ROOT_DIR + "/f5-tts").mkdir(exist_ok=True)
    winobj = F5TTSForm()
    config.child_forms['f5tts'] = winobj
    winobj.role.setPlainText(config.params.get("f5tts_role",''))
    winobj.is_whisper.setChecked(bool(config.params.get("f5tts_is_whisper",False)))
    winobj.index_tts_version.setCurrentIndex(int(config.params.get('index_tts_version',0)))

    # open参数是默认需要显示的
    init_show_url=config.get_url_byf5tts(init_show_type)
    if init_show_url:
        winobj.api_url.setText(init_show_url)

    winobj.ttstype.setCurrentText(init_show_type)


    winobj.ttstype.currentTextChanged.connect(_change_bytype)
    winobj.api_url.textChanged.connect(_change_byurl)
    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
