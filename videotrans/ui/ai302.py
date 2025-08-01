# run again.  Do not edit this file unless you know what you are doing.


from PySide6 import QtCore, QtWidgets

from videotrans.util import tools


class Ui_ai302form(object):
    def setupUi(self, ai302form):
        ai302form.setObjectName("ai302form")
        ai302form.setWindowModality(QtCore.Qt.NonModal)
        ai302form.resize(600, 550)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(ai302form.sizePolicy().hasHeightForWidth())
        ai302form.setSizePolicy(sizePolicy)
        ai302form.setMaximumSize(QtCore.QSize(600, 550))

        self.has_done = False
        v1= QtWidgets.QVBoxLayout(ai302form)

        h1= QtWidgets.QHBoxLayout()

        self.label_1 = QtWidgets.QLabel()
        self.label_1.setObjectName("label_1")
        self.label_1.setText("已接入文字大模型翻译字幕 及 语音识别 和 openai/豆包/Azure/Minimaxi/Dubbingx 配音角色")
        v1.addWidget(self.label_1)

        self.label_2 = QtWidgets.QLabel()
        self.label_2.setObjectName("label_2")
        self.ai302_key = QtWidgets.QLineEdit(ai302form)
        self.ai302_key.setMinimumSize(QtCore.QSize(0, 35))
        self.ai302_key.setObjectName("ai302_key")
        h1.addWidget(self.label_2)
        h1.addWidget(self.ai302_key)
        v1.addLayout(h1)

        h2= QtWidgets.QHBoxLayout()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)

        self.label_3 = QtWidgets.QLabel(ai302form)
        self.label_3.setObjectName("label_3")
        self.ai302_model = QtWidgets.QComboBox(ai302form)
        self.ai302_model.setMinimumSize(QtCore.QSize(0, 35))
        self.ai302_model.setObjectName("ai302_model")
        self.ai302_model.setSizePolicy(sizePolicy)
        h2.addWidget(self.label_3)
        h2.addWidget(self.ai302_model)
        v1.addLayout(h2)

        self.label_allmodels = QtWidgets.QLabel(ai302form)
        self.label_allmodels.setObjectName("label_allmodels")
        v1.addWidget(self.label_allmodels)



        self.edit_allmodels = QtWidgets.QPlainTextEdit(ai302form)
        self.edit_allmodels.setObjectName("edit_allmodels")
        v1.addWidget(self.edit_allmodels)

        self.label_4 = QtWidgets.QLabel(ai302form)
        self.label_4.setObjectName("label_4")
        v1.addWidget(self.label_4)

        self.ai302_template = QtWidgets.QPlainTextEdit(ai302form)
        self.ai302_template.setObjectName("ai302_template")
        v1.addWidget(self.ai302_template)


        h3= QtWidgets.QHBoxLayout()
        self.set_ai302 = QtWidgets.QPushButton(ai302form)
        self.set_ai302.setMinimumSize(QtCore.QSize(0, 35))
        self.set_ai302.setObjectName("set_ai302")

        self.test_ai302 = QtWidgets.QPushButton(ai302form)
        self.test_ai302.setMinimumSize(QtCore.QSize(0, 30))
        self.test_ai302.setObjectName("test_ai302")

        self.label_0 = QtWidgets.QPushButton(ai302form)
        self.label_0.setCursor(QtCore.Qt.PointingHandCursor)
        self.label_0.setStyleSheet("""text-align:left;background-color:transparent""")
        self.label_0.setText('查看填写教程')
        self.label_0.clicked.connect(lambda: tools.open_url("https://pyvideotrans.com/302ai"))


        h3.addWidget(self.set_ai302)
        h3.addWidget(self.test_ai302)
        h3.addWidget(self.label_0)
        v1.addLayout(h3)

        self.retranslateUi(ai302form)
        QtCore.QMetaObject.connectSlotsByName(ai302form)

    def retranslateUi(self, ai302form):
        ai302form.setWindowTitle("302.ai 接入翻译和配音渠道配置")
        self.label_3.setText('选择模型')
        self.label_allmodels.setText('填写所有可用模型，以英文逗号分隔，填写后可在上方选择')
        self.ai302_template.setPlaceholderText("prompt")
        self.label_4.setText("{lang}代表目标语言名称，不要删除。")
        self.set_ai302.setText('保存')
        self.test_ai302.setText('测试..')
        self.ai302_key.setPlaceholderText("在api超市-api管理-创建API KEY")
        self.ai302_key.setToolTip("如果没有账号，可去 302.ai 注册，有7元免费额度")
        self.label_2.setText("API KEY")
