import json
import os
from pathlib import Path

import torch
from PySide6 import QtWidgets
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QTextCursor
from PySide6.QtWidgets import QMessageBox

from videotrans import translator
from videotrans.component.component import DropButton
from videotrans.configure import config
from videotrans.recognition import FASTER_WHISPER, OPENAI_WHISPER, is_allow_lang, is_input_api
from videotrans.task.recognworker import RecognWorker
from videotrans.winform import fn_downmodel


def open():
    RESULT_DIR = config.HOME_DIR + f"/recogn"
    Path(RESULT_DIR).mkdir(exist_ok=True)

    def feed(d):
        d = json.loads(d)
        if d['type'] == 'replace':
            recognform.shibie_text.clear()
            recognform.shibie_text.insertPlainText(d["text"])
        elif d['type'] == 'subtitle':
            recognform.shibie_text.moveCursor(QTextCursor.End)
            recognform.shibie_text.insertPlainText(d['text'].capitalize())
        elif d['type'] == 'error':
            recognform.shibie_startbtn.setDisabled(False)
            QMessageBox.critical(recognform, config.transobj['anerror'], d['text'])
            recognform.shibie_startbtn.setText(config.box_lang["Start"])
        elif d['type'] == 'logs':
            recognform.loglabel.setText(d['text'])
        elif d['type'] == 'jindu':
            recognform.shibie_startbtn.setText(d['text'])
        else:
            recognform.loglabel.setText(config.transobj['quanbuend'])
            recognform.shibie_startbtn.setText(config.transobj["zhixingwc"])
            recognform.shibie_startbtn.setDisabled(False)
            recognform.shibie_dropbtn.setText(config.transobj['quanbuend'] + ". " + config.transobj['xuanzeyinshipin'])

    def opendir_fn():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    # tab-3 语音识别 预执行，检查
    def shibie_start_fun():
        config.settings = config.parse_init()
        model = recognform.shibie_model.currentText()
        split_type_index = recognform.shibie_whisper_type.currentIndex()
        model_type = recognform.shibie_model_type.currentIndex()

        langcode = translator.get_audio_code(show_source=recognform.shibie_language.currentText())

        is_cuda = recognform.is_cuda.isChecked()
        if check_cuda(is_cuda) is not True:
            return QMessageBox.critical(recognform, config.transobj['anerror'],
                                        config.transobj["nocudnn"])

        if model_type == FASTER_WHISPER and model.find('/') == -1:
            file = f'{config.ROOT_DIR}/models/models--Systran--faster-whisper-{model}/snapshots'
            if model.startswith('distil'):
                file = f'{config.ROOT_DIR}/models/models--Systran--faster-{model}/snapshots'
            if not os.path.exists(file):
                fn_downmodel.open(model_name=model, model_type=FASTER_WHISPER)
                return

        if model_type == OPENAI_WHISPER and not Path(config.ROOT_DIR + f'/models/{model}.pt').exists():
            fn_downmodel.open(model_name=model, model_type=OPENAI_WHISPER)
            return
        # 待识别音视频文件列表
        files = recognform.shibie_dropbtn.filelist
        if not files or len(files) < 1:
            return QMessageBox.critical(recognform, config.transobj['anerror'], config.transobj['bixuyinshipin'])

        is_allow_lang_res = is_allow_lang(langcode=langcode, model_type=model_type)
        if is_allow_lang_res is not True:
            return QMessageBox.critical(recognform, config.transobj['anerror'], is_allow_lang_res)
        # 判断是否填写自定义识别api openai-api识别、zh_recogn识别信息
        if is_input_api(model_type=model_type) is not True:
            return

        wait_list = []
        recognform.shibie_startbtn.setText(config.transobj["running"])
        recognform.label_shibie10.setText('')
        for file in files:
            recognform.shibie_text.clear()
            wait_list.append(file)

        recognform.shibie_opendir.setDisabled(False)
        try:
            recognform.shibie_startbtn.setDisabled(True)
            recognform.loglabel.setText('')
            shibie_task = RecognWorker(
                audio_paths=wait_list,
                model=model,
                split_type=["all", "avg"][split_type_index],
                model_type=model_type,
                language=langcode,
                out_path=RESULT_DIR,
                is_cuda=is_cuda, parent=recognform)
            shibie_task.uito.connect(feed)
            shibie_task.start()
        except Exception as e:
            import traceback
            traceback.print_exc()

    def check_cuda(state):
        # 选中如果无效，则取消
        if state:
            if not torch.cuda.is_available():
                QMessageBox.critical(recognform, config.transobj['anerror'], config.transobj['nocuda'])
                recognform.is_cuda.setChecked(False)
                recognform.is_cuda.setDisabled(True)
                return False
            if recognform.shibie_model_type.currentIndex() == OPENAI_WHISPER:
                return True

            if recognform.shibie_model_type.currentIndex() == FASTER_WHISPER:
                from torch.backends import cudnn
                if not cudnn.is_available() or not cudnn.is_acceptable(torch.tensor(1.).cuda()):
                    QMessageBox.critical(recognform, config.transobj['anerror'], config.transobj["nocudnn"])
                    recognform.is_cuda.setChecked(False)
                    recognform.is_cuda.setDisabled(True)
                    return False
        return True

    # 设定模型类型
    def model_type_change():
        model_type = recognform.shibie_model_type.currentIndex()
        if model_type > 0:
            recognform.shibie_whisper_type.setDisabled(True)
        else:
            recognform.shibie_whisper_type.setDisabled(False)
        if model_type > 1:
            recognform.shibie_model.setDisabled(True)
        else:
            recognform.shibie_model.setDisabled(False)
        lang = translator.get_code(show_text=recognform.shibie_language.currentText())
        is_allow_lang_res = is_allow_lang(langcode=lang, model_type=config.params['model_type'])
        if is_allow_lang_res is not True:
            QMessageBox.critical(recognform, config.transobj['anerror'], is_allow_lang_res)

    from videotrans.component import Recognform
    try:
        recognform = config.child_forms.get('recognform')
        if recognform is not None:
            recognform.show()
            recognform.raise_()
            recognform.activateWindow()
            return

        recognform = Recognform()
        config.child_forms['recognform'] = recognform
        recognform.shibie_dropbtn = DropButton(config.transobj['xuanzeyinshipin'])
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(recognform.shibie_dropbtn.sizePolicy().hasHeightForWidth())
        recognform.shibie_dropbtn.setSizePolicy(sizePolicy)
        recognform.shibie_dropbtn.setMinimumSize(0, 150)
        recognform.shibie_widget.insertWidget(0, recognform.shibie_dropbtn)

        recognform.shibie_language.addItems(config.langnamelist)
        recognform.shibie_model.addItems(config.WHISPER_MODEL_LIST)
        recognform.shibie_startbtn.clicked.connect(shibie_start_fun)
        recognform.shibie_opendir.clicked.connect(opendir_fn)
        recognform.is_cuda.toggled.connect(check_cuda)
        recognform.shibie_model_type.currentIndexChanged.connect(model_type_change)

        recognform.show()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(e)
