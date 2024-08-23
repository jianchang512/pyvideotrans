import os

import torch
from PySide6 import QtWidgets
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QTextCursor
from PySide6.QtWidgets import QMessageBox

from videotrans import translator
from videotrans.box.component import DropButton
from videotrans.configure import config
from videotrans.task.recognworker import RecognWorker


def open():
    def feed(d):
        print(f'{d=}')
        if d.startswith('replace:'):
            config.recognform.shibie_text.clear()
            config.recognform.shibie_text.insertPlainText(d[8:])
        elif d.startswith('set:'):
            config.recognform.shibie_text.moveCursor(QTextCursor.End)
            config.recognform.shibie_text.insertPlainText(d[4:].capitalize())
        elif d.startswith('error:'):
            config.recognform.shibie_startbtn.setDisabled(False)
            QMessageBox.critical(config.recognform, config.transobj['anerror'], d[6:])
        elif d.startswith('jd:'):
            config.recognform.shibie_startbtn.setText(d[3:])
        else:
            config.recognform.shibie_startbtn.setText(config.transobj["zhixingwc"])
            config.recognform.shibie_startbtn.setDisabled(False)
            config.recognform.shibie_dropbtn.setText(
                config.transobj['quanbuend'] + ". " + config.transobj['xuanzeyinshipin'])

    def opendir_fn(dirname=None):
        if not dirname:
            return
        if not os.path.isdir(dirname) or not os.path.exists(dirname):
            dirname = os.path.dirname(dirname)
        QDesktopServices.openUrl(QUrl.fromLocalFile(dirname))

    # tab-3 语音识别 预执行，检查
    def shibie_start_fun():
        config.settings = config.parse_init()
        model = config.recognform.shibie_model.currentText()
        split_type_index = config.recognform.shibie_whisper_type.currentIndex()
        if config.recognform.shibie_model_type.currentIndex() == 1:
            model_type = 'openai'
        elif config.recognform.shibie_model_type.currentIndex() == 2:
            model_type = 'GoogleSpeech'
        elif config.recognform.shibie_model_type.currentIndex() == 3:
            model_type = 'zh_recogn'
        elif config.recognform.shibie_model_type.currentIndex() == 4:
            model_type = 'doubao'
        else:
            model_type = "faster"

        langcode = translator.get_audio_code(show_source=config.recognform.shibie_language.currentText())

        is_cuda = config.recognform.is_cuda.isChecked()
        if is_cuda and model_type == 'faster':
            allow = True
            try:
                from torch.backends import cudnn
                if not cudnn.is_available() or not cudnn.is_acceptable(torch.tensor(1.).cuda()):
                    allow = False
            except:
                allow = False
            finally:
                if not allow:
                    config.recognform.is_cuda.setChecked(False)
                    return QMessageBox.critical(config.recognform, config.transobj['anerror'],
                                                config.transobj["nocudnn"])
        if model_type == 'faster' and model.find('/') == -1:
            file = f'{config.rootdir}/models/models--Systran--faster-whisper-{model}/snapshots'
            if model.startswith('distil'):
                file = f'{config.rootdir}/models/models--Systran--faster-{model}/snapshots'
            if not os.path.exists(file):
                QMessageBox.critical(config.recognform, config.transobj['anerror'],
                                     config.transobj['downloadmodel'].replace('{name}', model))
                return
        elif model_type == 'openai' and not os.path.exists(config.rootdir + f'/models/{model}.pt'):
            return QMessageBox.critical(config.recognform, config.transobj['anerror'],
                                        config.transobj['openaimodelnot'].replace('{name}', model))
        files = config.recognform.shibie_dropbtn.filelist

        if not files or len(files) < 1:
            return QMessageBox.critical(config.recognform, config.transobj['anerror'], config.transobj['bixuyinshipin'])

        if model_type == 'zh_recogn' and langcode[:2] not in ['zh']:
            return QMessageBox.critical(config.recognform, config.transobj['anerror'],
                                        'zh_recogn 仅支持中文语音识别' if config.defaulelang == 'zh' else 'zh_recogn Supports Chinese speech recognition only')

        if model_type == 'doubao' and langcode[:2] not in ["zh", "en", "ja", "ko", "fr", "es", "ru"]:
            return QMessageBox.critical(config.recognform, config.transobj['anerror'], '豆包语音识别仅支持中英日韩法俄西班牙语言，其他不支持')

        wait_list = []
        config.recognform.shibie_startbtn.setText(config.transobj["running"])

        config.recognform.label_shibie10.setText('')
        for file in files:
            config.recognform.shibie_text.clear()
            wait_list.append(file)

        shibie_out_path = config.homedir + f"/recogn"

        os.makedirs(shibie_out_path, exist_ok=True)
        config.recognform.shibie_opendir.setDisabled(False)
        try:
            shibie_task = RecognWorker(
                audio_paths=wait_list,
                model=model,
                split_type=["all", "avg"][split_type_index],
                model_type=model_type,
                language=langcode,
                out_path=shibie_out_path,
                is_cuda=is_cuda,parent=config.recognform)
            shibie_task.uito.connect(feed)
            shibie_task.start()
        except Exception as e:
            import traceback
            traceback.print_exc()

    def check_cuda(state):
        # 选中如果无效，则取消
        if state:
            if not torch.cuda.is_available():
                QMessageBox.critical(config.recognform, config.transobj['anerror'], config.transobj['nocuda'])
                config.recognform.is_cuda.setChecked(False)
                config.recognform.is_cuda.setDisabled(True)
            else:
                from torch.backends import cudnn
                if not cudnn.is_available() or not cudnn.is_acceptable(torch.tensor(1.).cuda()):
                    QMessageBox.critical(config.recognform, config.transobj['anerror'], config.transobj["nocudnn"])
                    config.recognform.is_cuda.setChecked(False)
                    config.recognform.is_cuda.setDisabled(True)

    # 设定模型类型
    def model_type_change():
        if config.recognform.shibie_model_type.currentIndex() == 1:
            model_type = 'openai'
            config.recognform.shibie_whisper_type.setDisabled(True)
            config.recognform.shibie_model.setDisabled(False)
        elif config.recognform.shibie_model_type.currentIndex() == 2:
            model_type = 'GoogleSpeech'
            config.recognform.shibie_whisper_type.setDisabled(True)
            config.recognform.shibie_model.setDisabled(True)
        elif config.recognform.shibie_model_type.currentIndex() == 3:
            model_type = 'zh_recogn'
            config.recognform.shibie_whisper_type.setDisabled(True)
            config.recognform.shibie_model.setDisabled(True)
        elif config.recognform.shibie_model_type.currentIndex() == 4:
            model_type = 'doubao'
            config.recognform.shibie_whisper_type.setDisabled(True)
            config.recognform.shibie_model.setDisabled(True)
        else:
            config.recognform.shibie_whisper_type.setDisabled(False)
            config.recognform.shibie_model.setDisabled(False)
            model_type = 'faster'

    from videotrans.component import Recognform
    try:
        if config.recognform is not None:
            config.recognform.show()
            config.recognform.raise_()
            config.recognform.activateWindow()
            return

        config.recognform = Recognform()
        config.recognform.shibie_dropbtn = DropButton(config.transobj['xuanzeyinshipin'])
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(config.recognform.shibie_dropbtn.sizePolicy().hasHeightForWidth())
        config.recognform.shibie_dropbtn.setSizePolicy(sizePolicy)
        config.recognform.shibie_dropbtn.setMinimumSize(0, 150)
        config.recognform.shibie_widget.insertWidget(0, config.recognform.shibie_dropbtn)

        config.recognform.shibie_language.addItems(config.langnamelist)
        config.recognform.shibie_model.addItems(config.model_list)
        config.recognform.shibie_startbtn.clicked.connect(shibie_start_fun)
        config.recognform.shibie_opendir.clicked.connect(lambda: opendir_fn(config.homedir + f"/recogn"))
        config.recognform.is_cuda.toggled.connect(check_cuda)
        config.recognform.shibie_model_type.currentIndexChanged.connect(model_type_change)

        config.recognform.show()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(e)
