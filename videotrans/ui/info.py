from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import QTimer
from PySide6.QtGui import QDesktopServices

from videotrans.configure import config



class Ui_infoform(object):
    def setupUi(self, infoform):
        infoform.setObjectName("infoform")
        infoform.setWindowModality(QtCore.Qt.NonModal)
        infoform.resize(800, 500)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(infoform.sizePolicy().hasHeightForWidth())
        infoform.setSizePolicy(sizePolicy)
        self.gridLayout = QtWidgets.QGridLayout(infoform)
        self.gridLayout.setObjectName("gridLayout")

        self.label=QtWidgets.QLabel(infoform)
        self.label.setText('捐助该软件以帮助持续维护' if config.defaulelang=='zh' else 'Donate to help the software to keep on maintaining')
        self.label.setStyleSheet("""font-size:20px""")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.textBrowser = QtWidgets.QTextBrowser(infoform)
        self.textBrowser.setObjectName("textBrowser")
        self.textBrowser.setOpenExternalLinks(True)
        self.textBrowser.anchorClicked.connect(self.openExternalLink)
        self.gridLayout.addWidget(self.textBrowser, 1, 0, 1, 1)
        if config.defaulelang == 'zh':
            self.retranslateUi(infoform)
        else:
            self.retranslateUi_en(infoform)
        QtCore.QMetaObject.connectSlotsByName(infoform)

    def openExternalLink(self, url):
        QDesktopServices.openUrl(url)

    def retranslateUi(self, infoform):
        infoform.setWindowTitle("捐助该软件以帮助持续维护")
        QTimer.singleShot(100, self._bindsignal)
    def _bindsignal(self):
        from . import mp, alipay, wx
        _mp, _alipay, _wx = mp, alipay, wx
        self.textBrowser.setHtml("""
        <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html><head><meta name="qrichtext" content="1" /><style type="text/css">
p, li { white-space: pre-wrap; }a{text-decoration:none}
</style></head><body style="font-size:14px; font-weight:400; font-style:normal;">

<p style=" margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">本项目基于兴趣创建，无商业和收费计划，你可以一直免费使用，或者fork后自己修改(开源协议GPL-v3)。所有代码均开源可审查。</p>
<p style=" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">至于维护问题呢，开源嘛都是用爱发电，闲时就多花些精力在这上面，忙时可能就一段时间顾不上。当然了，如果觉得该项目对你有价值，并希望该项目能一直稳定持续维护，也欢迎小额捐助。</p>

<hr />

<p style=" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">Email:jianchang512@gmail.com</p>

<p style=" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">网站:pyvideotrans.com</p>

<p style=" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">微信公众号/教程发布:pyvideotrans</p>

<p style=" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><a style="color:#fff" href="https://juejin.cn/user/4441682704623992/posts">掘金博客/教程发布: juejin.cn/user/4441682704623992</a></p>

<hr />

<h2 style="margin-top:16px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:x-large; font-weight:600;">如何捐助</span></h2>
<p style=" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">你可以向微信或支付宝二维码付款，备注你的github名称</p>
<p style=" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">
    <img src=":/png/wx.png" width="240" />
    <img src=":/png/alipay.png" width="240" style="margin-left:8px" />
    <img src=":/png/mp.jpg" width="200" /></p>
<hr />

<h2 style=" margin-top:16px; margin-bottom:30px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><a style=" font-size:x-large; font-weight:600;color:#ff0" href="https://pyvideotrans.com/about">
感谢所有捐助者，本项目的每一点改善都离不开您的帮助,点击查看捐赠名单</a></h2>
<hr />
<h2>免责声明：</h2>

在您下载或使用 "pyVideoTrans视频翻译配音" 软件（以下简称"本软件"）前，请仔细阅读并充分理解本免责声明中的各项条款。您的下载、安装或使用行为将被视为对本免责声明的接受，并同意按照本声明内容约束自己的行为。如果您不同意本声明的任何条款，请不要下载、安装或使用本软件。<br><br>

本软件所有源码均在 https://github.com/jianchang512/pyvideotrans 上开放。<br><br>

1. 本软件是由独立开发者使用开源语音识别模型并结合第三方翻译API和第三方配音API开发的免费工具，旨在提供视频翻译和配音功能。开发者保证在软件运行过程中不会获取或存储用户数据。<br><br>

2. 本软件中集成的语音识别功能（openai和faster模式）完全在本地环境下运行，不涉及将任何数据发送到开发者的服务器。当使用第三方翻译API和配音API时，相关数据将由用户的计算机直接传输至第三方服务器，未经开发者服务器处理。本软件无需用户注册或登录，不收集或存储任何个人信息。<br><br>

3. 本软件纯属个人爱好项目，开发者无营利目的，未制定任何盈利计划，并不提供付费技术支持或其他付费服务。<br><br>

4. 本软件不提供视频内容转移的功能，也不鼓励或支持任何形式的视频内容搬运行为。本软件仅旨在降低观赏外语视频时的语言障碍。<br><br>

5. 用户在使用本软件时，须自觉遵守当地法律以及中华人民共和国的法律法规，敬重并维护他人版权和知识产权。<br><br>

6. 用户因违反法律法规或侵犯他人权利而造成的任何后果，由用户本人承担，本软件开发者不承担任何连带责任。<br><br>

7. 鉴于开发者从本软件中未获利，对于本软件的使用引发的任何问题或损失，开发者不负责任。<br><br>

8. 本软件采用GPL-v3开源协议。任何基于本软件的二次开发或分支版本，需遵循GPL-v3协议规定，遵守相应义务和约束。<br>

本软件的所有解释权均属于开发者。谨请用户在理解、同意、遵守本免责声明的前提下使用本软件。<br>


</body></html>
""")

    def retranslateUi_en(self, infoform):
        infoform.setWindowTitle("Donate to this software")
        self.textBrowser.setHtml("""
        <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html><head><meta name="qrichtext" content="1" /><style type="text/css">
p, li { white-space: pre-wrap; }a{text-decoration:none}
</style></head><body style="font-size:14px; font-weight:400; font-style:normal;">
<p style=" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">This project is created based on interest, with no commercial or charging plans. You can always use it for free, or fork it and modify it yourself (open source agreement GPL-v3). All codes are open source and can be reviewed.</p>
<p style=" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">As for maintenance, open source is all about love. When you are free, you can spend more time on it. When you are busy, you may not be able to take care of it for a while. Of course, if you think the project is valuable to you and hope that the project can be maintained stably and continuously, small donations are also welcome.</p>

<hr />

<p style=" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">Email:jianchang512@gmail.com</p>

<p style=" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">Documents:pyvideotrans.com</p>


<hr />

<h2 style="margin-top:16px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:x-large; font-weight:600;">How to Donate</span></h2>
<p><a style="font-size:18px;color:#4caf50" href="https://ko-fi.com/jianchang512"> 👑 Donate to this project and support at https://ko-fi.com/jianchang512 </a></p>

<h2 style=" margin-top:16px; margin-bottom:30px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><a style=" font-size:x-large; font-weight:600;color:#ff0" href="https://pyvideotrans.com/about">
Thank you to all of our donors, every improvement in this program is made possible with your help, click here to see all donors!</a></h2>
</body></html>
""")
