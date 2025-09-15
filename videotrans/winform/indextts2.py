# videotrans/winform/indextts2.py

def openwin():
    from PySide6 import QtWidgets
    from videotrans import tts
    from videotrans.configure import config
    from videotrans.util import tools
    from videotrans.util.ListenVoice import ListenVoice
    from videotrans.component import IndexTTS2Form

    # def feed(d):
    #     if d == "ok":
    #         QtWidgets.QMessageBox.information(winobj, "成功", "测试成功！语音已生成。")
    #     else:
    #         tools.show_error(d)
    #     winobj.test.setText("测试Api" if config.defaulelang == 'zh' else "Test API")
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "成功", "测试成功！语音已生成。")
        else:
            # 直接显示后端传来的详细错误信息 d，而不是通用提示
            tools.show_error(f"测试失败: {d}") 
        winobj.test.setText("测试Api" if config.defaulelang == 'zh' else "Test API")

    def test():
        url = winobj.api_url.text().strip()
        if not url or not url.startswith('http'):
            tools.show_error("URL格式不正确，必须以 http 开头。")
            return

        # --- 关键修正2：在测试前，先保存当前配置 ---
        config.params["indextts2_url"] = url
        config.params["indextts2_rolelist"] = winobj.rolelist.toPlainText().strip()
        config.getset_params(config.params) # 使用正确的保存函数

        winobj.test.setText('测试中...' if config.defaulelang == 'zh' else 'Testing...')

        roles = tools.get_indextts2_role()
        test_role = "clone"
        if roles:
            test_role = list(roles.keys())[0]

        tts_type = tts.INDEXTTS2_TTS 

        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": 'Hello, this is a test from pyVideoTrans.', 
            "role": test_role,
            "filename": config.TEMP_HOME + f"/test-indextts2.wav",
            "tts_type": tts_type,
            "ref_wav": "./videotrans/styles/test.wav"
        }], language="en", tts_type=tts_type)

        wk.uito.connect(feed)
        wk.start()

    def save():
        url = winobj.api_url.text().strip()
        if not url or not url.startswith('http'):
            tools.show_error("URL格式不正确，必须以 http 开头。")
            return

        # VVVVVV 在这里添加一行代码 VVVVVV
        # 告诉主程序，当前的 tts_type 就是 IndexTTS2
        config.params['tts_type'] = tts.INDEXTTS2_TTS
        # ^^^^^^ 在这里添加一行代码 ^^^^^^

        config.params["indextts2_url"] = url
        config.params["indextts2_rolelist"] = winobj.rolelist.toPlainText().strip()
        config.getset_params(config.params)

        # 这行代码会通知主界面刷新，现在主界面知道了 tts_type，就会正确切换了
        tools.set_process(text='indextts2', type="refreshtts")
        winobj.close()

    winobj = config.child_forms.get('indextts2w')
    if winobj:
        winobj.show()
        winobj.raise_()
        return

    winobj = IndexTTS2Form()
    config.child_forms['indextts2w'] = winobj

    if config.params.get("indextts2_url"):
        winobj.api_url.setText(config.params["indextts2_url"])
    if config.params.get("indextts2_rolelist"):
        winobj.rolelist.setPlainText(config.params["indextts2_rolelist"])

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()