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
        winobj.test.setText(tr("Test"))
        winobj.local_test_btn.setText(tr("Test local role"))

    def _refresh_local_role_combo():
        current_text = winobj.local_role_combo.currentText() if hasattr(winobj, 'local_role_combo') else ''
        rows = _parse_local_roles(winobj.local_role.toPlainText().strip(), need_raise=False)
        role_names = [name for name, _ in rows]
        winobj.local_role_combo.clear()
        winobj.local_role_combo.addItems(role_names)
        if current_text and current_text in role_names:
            winobj.local_role_combo.setCurrentText(current_text)

    def _normalize_url(url: str):
        return tools.get_mosstts_service_urls(url).get('service_root', '')

    def _parse_local_roles(role_text: str, need_raise: bool = False):
        rows = []
        for raw_line in str(role_text or '').splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if '#' in line:
                audio_name, ref_text = line.split('#', 1)
            else:
                audio_name, ref_text = line, ''
            audio_name = audio_name.strip()
            ref_text = ref_text.strip()
            if not audio_name:
                continue
            audio_file = Path(f'{ROOT_DIR}/f5-tts/{audio_name}')
            if not audio_file.is_file():
                msg = tr('Please save the audio file in the {}/f5-tts directory', ROOT_DIR)
                if need_raise:
                    raise Exception(f'{audio_name}: {msg}')
                continue
            rows.append((audio_name, ref_text))
        return rows

    def _normalize_local_role_text(role_text: str, need_raise: bool = False):
        rows = _parse_local_roles(role_text, need_raise=need_raise)
        return '\n'.join([f'{name}#{text}' if text else name for name, text in rows])

    def _sync_params(force_refresh_roles: bool = False):
        url = _normalize_url(winobj.clone_address.text().strip())
        local_role_text = _normalize_local_role_text(winobj.local_role.toPlainText().strip(), need_raise=True)
        params['moss_tts_url'] = url
        params['moss_tts_local_role'] = local_role_text
        if force_refresh_roles:
            tools.get_mosstts_role(force=True)
        return url, local_role_text

    def _check_service_health(url: str):
        service_urls = tools.get_mosstts_service_urls(url)
        health_url = service_urls.get('health_url', '')
        if not health_url:
            raise Exception('Please configure the MOSS-TTS-Nano API address first.')
        proxies = {"http": "", "https": ""} if ('127.0.0.1' in health_url or 'localhost' in health_url) else None
        response = requests.get(health_url, timeout=20, proxies=proxies)
        response.raise_for_status()
        return service_urls

    def save():
        _sync_params(force_refresh_roles=True)
        params.save()
        tools.set_process(text='mosstts', type='refreshtts')
        winobj.close()

    def test():
        url, _ = _sync_params(force_refresh_roles=False)
        _check_service_health(url)
        demo_role_map = tools.get_mosstts_demo_map(force=True, raise_exception=True)
        test_role = next(iter(demo_role_map.keys()), '')
        if not test_role:
            return tools.show_error('MOSS-TTS-Nano remote roles not found. Please check the API address and service status.')
        tools.get_mosstts_role(force=True)
        test_text = tools.get_mosstts_role_test_text(test_role, '你好啊我的朋友,希望你今天开心！')
        winobj.test.setText(tr('Testing...'))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": test_text,
            "role": test_role,
            "filename": TEMP_DIR + f"/{time.time()}-mosstts.wav",
            "tts_type": tts.MOSS_TTS,
        }], language="zh", tts_type=tts.MOSS_TTS)
        wk.uito.connect(lambda d, role_name=test_role: feed(d, role_name))
        wk.start()

    def test_local_role():
        _sync_params(force_refresh_roles=False)
        _refresh_local_role_combo()
        role_name = winobj.local_role_combo.currentText().strip()
        if not role_name:
            return tools.show_error('No local role available for testing.')
        test_text = tools.get_mosstts_role_test_text(role_name, '你好啊我的朋友,希望你今天开心！')
        winobj.local_test_btn.setText(tr('Testing...'))
        from videotrans import tts
        import time
        wk = ListenVoice(parent=winobj, queue_tts=[{
            "text": test_text,
            "role": role_name,
            "filename": TEMP_DIR + f"/{time.time()}-mosstts-local.wav",
            "tts_type": tts.MOSS_TTS,
        }], language="zh", tts_type=tts.MOSS_TTS)
        wk.uito.connect(lambda d, role_name=role_name: feed(d, role_name))
        wk.start()

    from videotrans.component.set_form import CloneForm
    winobj = CloneForm()
    app_cfg.child_forms['mosstts'] = winobj
    winobj.setWindowTitle('MOSS-TTS-Nano')
    winobj.resize(760, 520)
    try:
        winobj.label.setText('MOSS-TTS-Nano API URL')
    except Exception:
        pass
    try:
        winobj.set_clone.setText(tr('Save'))
    except Exception:
        pass

    local_role_label = QtWidgets.QLabel(tr('Reference Audio#Audio Text'))
    local_role_tip = QtWidgets.QLabel(tr('Audio must be stored in {}/f5-tts. One role per line. Example: demo.wav#你好，我是本地角色', ROOT_DIR))
    local_role_tip.setStyleSheet('color:#999')
    local_role_tip.setWordWrap(True)
    local_role_editor = QtWidgets.QPlainTextEdit()
    local_role_editor.setPlaceholderText(tr('Reference Audio#Audio Text'))
    local_role_editor.setMinimumHeight(120)
    winobj.local_role = local_role_editor

    winobj.verticalLayout.insertWidget(1, local_role_label)
    winobj.verticalLayout.insertWidget(2, local_role_tip)
    winobj.verticalLayout.insertWidget(3, local_role_editor)

    if winobj.layout_btn.count() > 2:
        help_item = winobj.layout_btn.takeAt(2)
        if help_item and help_item.widget():
            help_item.widget().deleteLater()

    local_test_wrap = QtWidgets.QHBoxLayout()
    local_test_label = QtWidgets.QLabel(tr('Local role'))
    local_role_combo = QtWidgets.QComboBox()
    local_role_combo.setMinimumHeight(35)
    local_test_btn = QtWidgets.QPushButton(tr('Test local role'))
    local_test_btn.setMinimumHeight(35)
    local_test_wrap.addWidget(local_test_label)
    local_test_wrap.addWidget(local_role_combo)
    local_test_wrap.addWidget(local_test_btn)
    winobj.verticalLayout.insertLayout(4, local_test_wrap)
    winobj.local_role_combo = local_role_combo
    winobj.local_test_btn = local_test_btn

    if params.get('moss_tts_url', ''):
        winobj.clone_address.setText(params.get('moss_tts_url', ''))
    if params.get('moss_tts_local_role', ''):
        winobj.local_role.setPlainText(params.get('moss_tts_local_role', ''))
    _refresh_local_role_combo()
    winobj.local_role.textChanged.connect(_refresh_local_role_combo)
    winobj.set_clone.clicked.connect(save)
    winobj.test.clicked.connect(test)
    winobj.local_test_btn.clicked.connect(test_local_role)
    winobj.show()