def openwin():
    from PySide6 import QtWidgets

    from videotrans.configure import config
    from videotrans.util import tools
    import json
    from videotrans.configure.config import tr
    from videotrans.util.ListenVoice import ListenVoice
    def feed(d):
        if d == "ok":
            QtWidgets.QMessageBox.information(winobj, "ok", "Test Ok")
        else:
            tools.show_error(d)
        winobj.test.setText(tr("Test"))

    def test():

        apikey = winobj.apikey.text()
        model = winobj.model.currentText()
        apiurl = winobj.apiurl.currentText()

        if not apikey:
            return tools.show_error(tr("SK is required"))


        emotion = winobj.emotion.currentText()
        config.params["minimaxi_emotion"] = emotion
        config.params["minimaxi_apikey"] = apikey
        config.params["minimaxi_model"] = model
        config.params["minimaxi_apiurl"] = apiurl
        config.getset_params(config.params)
        '''
        try:
            updaterole()
        except Exception as e:
            return tools.show_error(str(e))
        '''
        winobj.test.setText(tr("Testing..."))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": '你好啊我的朋友',
            "role": "青涩青年音色" if "api.minimaxi.com"==apiurl else 'Reliable Executive',
            "filename": config.TEMP_HOME + f"/{time.time()}-minimaxi.wav",
            "tts_type": tts.MINIMAXI_TTS}],
                         language="zh",
                         tts_type=tts.MINIMAXI_TTS)
        wk.uito.connect(feed)
        wk.start()
        tools.set_process(text='minimaxi', type="refreshtts")

    def save():

        apikey = winobj.apikey.text()
        model = winobj.model.currentText()
        apiurl = winobj.apiurl.currentText()
        config.params["minimaxi_apiurl"] = apiurl



        emotion = winobj.emotion.currentText()
        config.params["minimaxi_emotion"] = emotion

        config.params["minimaxi_apikey"] = apikey
        config.params["minimaxi_model"] = model
        config.getset_params(config.params)
        tools.set_process(text='minimaxi', type="refreshtts")
        winobj.close()

    def updaterole():
        import requests
        import os


        url = f'https://{config.params.get("minimaxi_apiurl")}/v1/get_voice'
        headers = {
            'authority': 'api.minimax.io',
            'Authorization': f'Bearer {config.params.get("minimaxi_apikey","")}',
            'content-type': 'application/json'
        }

        data = {
            'voice_type': 'voice_cloning'
        }

        response = requests.post(url, headers=headers, json=data)
        role=response.json()
        print(role)
        if 'voice_cloning' not in role:
            raise RuntimeError(role)
        if not role['voice_cloning']:
            raise RuntimeError('No voice id for clone')
        rolelist={}
        for it in role['voice_cloning']:
            rolelist[it['voice_name'] if it['voice_name'] else it['voice_id']]=it['voice_id']
        raws=tools.get_minimaxi_rolelist()
        for k in raws.keys():
            raws[k].update(rolelist)
        try:
            filejson=config.ROOT_DIR + "/videotrans/voicejson/minimaxi.json"
            if config.params["minimaxi_apiurl"]=='api.minimax.io':
                filejson=config.ROOT_DIR + "/videotrans/voicejson/minimaxiio.json"
            with open(filejson,'w',encoding='utf-8') as f:
                f.write(json.dumps(raws,ensure_ascii=False))
            tools.set_process(text='minimaxi', type="refreshtts")
        except (OSError,json.JSONDecodeError):
            pass
            
        


    from videotrans.component import MinimaxiForm
    winobj = MinimaxiForm()
    config.child_forms['minimaxi'] = winobj


    winobj.apikey.setText(config.params.get("minimaxi_apikey",''))
    winobj.apiurl.setCurrentText(config.params.get("minimaxi_apiurl",'api.minimaxi.com'))

    winobj.emotion.setCurrentText(config.params.get("minimaxi_emotion",''))
    winobj.emotion.setCurrentText(config.params.get("minimaxi_model",''))

    winobj.save.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.show()
