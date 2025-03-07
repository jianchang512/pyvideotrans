import requests
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import QByteArray, QThread, Signal
from PySide6.QtGui import Qt, QPixmap

from videotrans.configure import config
from videotrans.util import tools


class Ui_infoform(object):
    def setupUi(self, infoform):
        infoform.setObjectName("infoform")
        infoform.setWindowModality(QtCore.Qt.NonModal)
        infoform.resize(950, 600)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(infoform.sizePolicy().hasHeightForWidth())
        infoform.setSizePolicy(sizePolicy)
        self.v1 = QtWidgets.QVBoxLayout(infoform)
        # 将 v1 设为垂直顶部对齐
        self.v1.setAlignment(Qt.AlignTop)

        self.label = QtWidgets.QLabel(infoform)
        self.label.setText(
            '捐助该软件以帮助持续维护' if config.defaulelang == 'zh' else 'Donate to help the software to keep on maintaining')
        self.label.setStyleSheet("""font-size:20px""")
        self.v1.addWidget(self.label)

        self.text1 = QtWidgets.QPlainTextEdit(infoform)
        self.text1.setObjectName("text1")
        self.text1.setReadOnly(True)
        self.text1.setMaximumHeight(180)
        self.text1.setPlainText("""本项目基于兴趣创建，无商业和收费计划，你可以一直免费使用，或者fork后自己修改(开源协议GPL-v3)。
所有代码均开源可审查。
至于维护问题呢，开源嘛都是用爱发电，闲时就多花些精力在这上面，忙时可能就一段时间顾不上。
当然了，如果觉得该项目对你有价值，并希望该项目能一直稳定持续维护，也欢迎小额捐助。

Email: jianchang512@gmail.com
文档站/下载: pyvideotrans.com
【软件免费下载使用，不收取任何费用，也未在任何平台销售】

""" if config.defaulelang == 'zh' else """This project is created based on interest, there is no commercial and no charge plan, you can use it for free or fork it and modify it (open source license GPL-v3). 
All code is open source and can be reviewed.
As for the maintenance issue, it is all about giving love to the open source, so idle time will spend more time on this, and sometimes just a period of time. 
Of course, if you think this project is useful to you and want it to be stable and continue to maintain, you are welcome to donate a small amount.

Email: jianchang512@gmail.com
Documents: pyvideotrans.com"""
                                )
        # text1的边框合为0
        self.text1.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.text1.setStyleSheet("""
        border:none;
        """)
        self.v1.addWidget(self.text1)

        self.link = QtWidgets.QPushButton(infoform)
        self.link.setText(
            " 感谢所有捐助者，本项目的每一点改善都离不开您的帮助 " if config.defaulelang == 'zh' else " Thank all donators, Click to view the list of donators ")
        # 设置高度35px，最大宽度300
        self.link.setFixedHeight(35)
        self.link.setStyleSheet("""background-color:transparent""")
        self.link.setCursor(Qt.PointingHandCursor)
        self.link.clicked.connect(lambda: tools.open_url('https://pyvideotrans.com/about.html'))

        label = QtWidgets.QLabel(infoform)
        label.setText("你可以扫描下方二维码捐助或者点击上方按钮打开网页扫码捐助 " if config.defaulelang == 'zh' else "You can scan the QR code or click the above button to donate via the web ")
        h2 = QtWidgets.QHBoxLayout()
        h2.addWidget(self.link)
        h2.addStretch()
        self.v1.addLayout(h2)
        self.v1.addWidget(label)

        self.h1 = QtWidgets.QHBoxLayout()
        if config.defaulelang == 'zh':
            self.wxpay = QtWidgets.QLabel()
            self.alipay = QtWidgets.QLabel()
            self.mp = QtWidgets.QLabel()
            self.wxpay.setFixedHeight(200)
            self.alipay.setFixedHeight(200)
            self.mp.setFixedHeight(200)
            self.h1.addWidget(self.wxpay)
            self.h1.addWidget(self.alipay)
            self.h1.addWidget(self.mp)
            self.v1.addLayout(self.h1)
            wxpaystask = DownloadImg(parent=self,
                                     urls={"name": "wxpay", "link": "https://pvtr2.pyvideotrans.com/images/wxpay.jpg"})
            alipaytask = DownloadImg(parent=self,
                                     urls={"name": "alipay", "link": "https://pvtr2.pyvideotrans.com/images/alipay.png"})
            mptask = DownloadImg(parent=self, urls={"name": "mp", "link": "https://pvtr2.pyvideotrans.com/images/mp.jpg"})
            wxpaystask.finished.connect(lambda: self.showimg("wxpay"))
            wxpaystask.start()
            alipaytask.finished.connect(lambda: self.showimg("alipay"))
            alipaytask.start()
            mptask.finished.connect(lambda: self.showimg("mp"))
            mptask.start()
        else:
            self.v1.addLayout(self.h1)
            link2 = QtWidgets.QPushButton(infoform)
            # 点击链接到 https://ko-fi.com/jianchang512
            link2.setText("Or Donate via https://ko-fi.com/jianchang512")
            link2.setFixedHeight(35)
            link2.setStyleSheet("""background-color:transparent;text-align:left""")
            link2.setCursor(Qt.PointingHandCursor)
            link2.clicked.connect(lambda: tools.open_url('https://ko-fi.com/jianchang512'))
            self.v1.addWidget(link2)

        lawbtn = QtWidgets.QPushButton()
        lawbtn.setFixedHeight(35)
        lawbtn.setMaximumWidth(300)
        lawbtn.setStyleSheet("background-color:rgba(255,255,255,0);text-align:left""")
        lawbtn.setCursor(Qt.PointingHandCursor)
        lawbtn.setText("软件使用协议/免责声明" if config.defaulelang == 'zh' else "Software License Agreement")
        lawbtn.clicked.connect(lambda: tools.open_url('https://pyvideotrans.com/law.html'))
        self.v1.addWidget(lawbtn)
        self.v1.addStretch()
        infoform.setWindowTitle(
            "捐助该软件以帮助持续维护" if config.defaulelang == 'zh' else "Donate to help the software to keep on maintaining")
        QtCore.QMetaObject.connectSlotsByName(infoform)

    def showimg(self, name):
        pixmap = QPixmap()
        pixmap.loadFromData(config.INFO_WIN['data'][name])
        pixmap = pixmap.scaledToHeight(200, Qt.SmoothTransformation)
        if name == 'wxpay':
            self.wxpay.setPixmap(pixmap)
        elif name == 'alipay':
            self.alipay.setPixmap(pixmap)
        elif name == 'mp':
            self.mp.setPixmap(pixmap)

    # 重写关闭事件，当关闭时仅隐藏
    def closeEvent(self, event):
        self.hide()


class DownloadImg(QThread):
    finished = Signal(str)

    def __init__(self, parent=None, urls=None):
        super().__init__(parent=parent)
        self.urls = urls

    def run(self):
        """下载网络图片并返回图片数据"""
        # 遍历字典 self.urls 分别获取 key和value
        try:
            response = requests.get(self.urls['link'])
            if response.status_code == 200:
                config.INFO_WIN["data"][self.urls['name']] = QByteArray(response.content)
                self.finished.emit(self.urls['name'])
        except:
            pass
