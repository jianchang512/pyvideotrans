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


def openwin():
    RESULT_DIR = config.HOME_DIR + f"/recogn"
    Path(RESULT_DIR).mkdir(exist_ok=True)

    def feed(d):
        if winobj.has_done:
            return
        d = json.loads(d)
        if d['type'] == 'replace':
            winobj.shibie_text.clear()
            winobj.shibie_text.insertPlainText(d["text"])
        elif d['type'] == 'subtitle':
            winobj.shibie_text.moveCursor(QTextCursor.End)
            winobj.shibie_text.insertPlainText(d['text'].capitalize())
        elif d['type'] == 'error':
            winobj.has_done=True
            winobj.shibie_startbtn.setDisabled(False)
            QMessageBox.critical(winobj, config.transobj['anerror'], d['text'])
            winobj.shibie_startbtn.setText(config.box_lang["Start"])
        elif d['type'] == 'logs':
            winobj.loglabel.setText(d['text'])
        elif d['type'] == 'jindu':
            winobj.shibie_startbtn.setText(d['text'])
        else:
            winobj.has_done=True
            winobj.loglabel.setText(config.transobj['quanbuend'])
            winobj.shibie_startbtn.setText(config.transobj["zhixingwc"])
            winobj.shibie_startbtn.setDisabled(False)
            winobj.shibie_dropbtn.setText(config.transobj['quanbuend'] + ". " + config.transobj['xuanzeyinshipin'])

    def opendir_fn():
        QDesktopServices.openUrl(QUrl.fromLocalFile(RESULT_DIR))

    # tab-3 语音识别 预执行，检查
    def shibie_start_fun():
        winobj.has_done=False
        config.settings = config.parse_init()
        model = winobj.shibie_model.currentText()
        split_type_index = winobj.shibie_whisper_type.currentIndex()
        model_type = winobj.shibie_model_type.currentIndex()

        langcode = translator.get_audio_code(show_source=winobj.shibie_language.currentText())

        is_cuda = winobj.is_cuda.isChecked()
        if check_cuda(is_cuda) is not True:
            return QMessageBox.critical(winobj, config.transobj['anerror'],
                                        config.transobj["nocudnn"])

        if model_type == FASTER_WHISPER and model.find('/') == -1:
            file = f'{config.ROOT_DIR}/models/models--Systran--faster-whisper-{model}/snapshots'
            if model.startswith('distil'):
                file = f'{config.ROOT_DIR}/models/models--Systran--faster-{model}/snapshots'
            if not os.path.exists(file):
                fn_downmodel.openwin(model_name=model, model_type=FASTER_WHISPER)
                return

        if model_type == OPENAI_WHISPER and not Path(config.ROOT_DIR + f'/models/{model}.pt').exists():
            fn_downmodel.openwin(model_name=model, model_type=OPENAI_WHISPER)
            return
        # 待识别音视频文件列表
        files = winobj.shibie_dropbtn.filelist
        if not files or len(files) < 1:
            return QMessageBox.critical(winobj, config.transobj['anerror'], config.transobj['bixuyinshipin'])

        is_allow_lang_res = is_allow_lang(langcode=langcode, model_type=model_type)
        if is_allow_lang_res is not True:
            return QMessageBox.critical(winobj, config.transobj['anerror'], is_allow_lang_res)
        # 判断是否填写自定义识别api openai-api识别、zh_recogn识别信息
        if is_input_api(model_type=model_type) is not True:
            return

        wait_list = []
        winobj.shibie_startbtn.setText(config.transobj["running"])
        winobj.label_shibie10.setText('')
        for file in files:
            winobj.shibie_text.clear()
            wait_list.append(file)

        winobj.shibie_opendir.setDisabled(False)
        try:
            winobj.shibie_startbtn.setDisabled(True)
            winobj.loglabel.setText('')
            shibie_task = RecognWorker(
                audio_paths=wait_list,
                model=model,
                split_type=["all", "avg"][split_type_index],
                model_type=model_type,
                language=langcode,
                out_path=RESULT_DIR,
                is_cuda=is_cuda, parent=winobj)
            shibie_task.uito.connect(feed)
            shibie_task.start()
        except Exception as e:
            import traceback
            traceback.print_exc()

    def check_cuda(state):
        # 选中如果无效，则取消
        if state:
            if not torch.cuda.is_available():
                QMessageBox.critical(winobj, config.transobj['anerror'], config.transobj['nocuda'])
                winobj.is_cuda.setChecked(False)
                winobj.is_cuda.setDisabled(True)
                return False
            if winobj.shibie_model_type.currentIndex() == OPENAI_WHISPER:
                return True

            if winobj.shibie_model_type.currentIndex() == FASTER_WHISPER:
                from torch.backends import cudnn
                if not cudnn.is_available() or not cudnn.is_acceptable(torch.tensor(1.).cuda()):
                    QMessageBox.critical(winobj, config.transobj['anerror'], config.transobj["nocudnn"])
                    winobj.is_cuda.setChecked(False)
                    winobj.is_cuda.setDisabled(True)
                    return False
        return True

    # 设定模型类型
    def model_type_change():
        model_type = winobj.shibie_model_type.currentIndex()
        if model_type > 0:
            winobj.shibie_whisper_type.setDisabled(True)
        else:
            winobj.shibie_whisper_type.setDisabled(False)
        if model_type > 1:
            winobj.shibie_model.setDisabled(True)
        else:
            winobj.shibie_model.setDisabled(False)
        lang = translator.get_code(show_text=winobj.shibie_language.currentText())
        is_allow_lang_res = is_allow_lang(langcode=lang, model_type=config.params['model_type'])
        if is_allow_lang_res is not True:
            QMessageBox.critical(winobj, config.transobj['anerror'], is_allow_lang_res)

    from videotrans.component import Recognform
    try:
        winobj = config.child_forms.get('recognform')
        if winobj is not None:
            winobj.show()
            winobj.raise_()
            winobj.activateWindow()
            return

        winobj = Recognform()
        config.child_forms['recognform'] = winobj
        winobj.shibie_dropbtn = DropButton(config.transobj['xuanzeyinshipin'])
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(winobj.shibie_dropbtn.sizePolicy().hasHeightForWidth())
        winobj.shibie_dropbtn.setSizePolicy(sizePolicy)
        winobj.shibie_dropbtn.setMinimumSize(0, 150)
        winobj.shibie_widget.insertWidget(0, winobj.shibie_dropbtn)

        winobj.shibie_language.addItems(config.langnamelist)
        winobj.shibie_model.addItems(config.WHISPER_MODEL_LIST)
        winobj.shibie_startbtn.clicked.connect(shibie_start_fun)
        winobj.shibie_opendir.clicked.connect(opendir_fn)
        winobj.is_cuda.toggled.connect(check_cuda)
        winobj.shibie_model_type.currentIndexChanged.connect(model_type_change)

        winobj.show()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(e)
