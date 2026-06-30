from PySide6 import QtCore, QtGui, QtWidgets


def _make_action(ui, name):
    action = QtGui.QAction()
    action.setObjectName(name)
    setattr(ui, name, action)
    return action


def _fill_menu(menu, actions):
    for action in actions:
        menu.addAction(action)
        menu.addSeparator()


def _fill_menu_h(menu, actions):
    for action in actions:
        menu.addSeparator()
        menu.addAction(action)
    menu.addSeparator()


def _setup_actions_and_menus(ui, MainWindow):
    ui.menuBar = QtWidgets.QMenuBar()
    ui.menuBar.setObjectName("menuBar")
    ui.menu_Key = QtWidgets.QMenu(ui.menuBar)
    ui.menu_Key.setObjectName("menu_Key")
    ui.menu_TTS = QtWidgets.QMenu(ui.menuBar)
    ui.menu_TTS.setObjectName("menu_TTS")
    ui.menu_RECOGN = QtWidgets.QMenu(ui.menuBar)
    ui.menu_RECOGN.setObjectName("menu_RECOGN")
    ui.menu = QtWidgets.QMenu(ui.menuBar)
    ui.menu.setObjectName("menu")
    ui.menu_H = QtWidgets.QMenu(ui.menuBar)
    ui.menu_H.setObjectName("menu_H")
    MainWindow.setMenuBar(ui.menuBar)

    ui.toolBar = QtWidgets.QToolBar()
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
    sizePolicy.setHorizontalStretch(1)
    sizePolicy.setVerticalStretch(0)
    sizePolicy.setHeightForWidth(ui.toolBar.sizePolicy().hasHeightForWidth())
    ui.toolBar.setSizePolicy(sizePolicy)
    ui.toolBar.setMinimumSize(QtCore.QSize(0, 0))
    ui.toolBar.setMaximumSize(QtCore.QSize(16777215, 16777215))
    ui.toolBar.setMovable(True)
    ui.toolBar.setIconSize(QtCore.QSize(100, 40))
    ui.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
    ui.toolBar.setFloatable(True)
    ui.toolBar.setObjectName("toolBar")
    ui.toolBar.setStyleSheet("""
    QToolBar QToolButton {
        min-width: 130px; 
        text-align: center; 
    }
""")
    MainWindow.addToolBar(QtCore.Qt.LeftToolBarArea, ui.toolBar)

    _make_action(ui, "actionbaidu_key")
    _make_action(ui, "actionali_key")
    _make_action(ui, "actionchatgpt_key")
    _make_action(ui, "actionzhipuai_key")
    _make_action(ui, "actionsiliconflow_key")
    _make_action(ui, "actiondeepseek_key")
    _make_action(ui, "actionminimax_key")
    _make_action(ui, "actionqwenmt_key")
    _make_action(ui, "actionopenrouter_key")
    _make_action(ui, "actionlibretranslate_key")
    _make_action(ui, "actionopenaitts_key")
    _make_action(ui, "actionxaitts_key")
    _make_action(ui, "actionxiaomi_key")
    _make_action(ui, "actionqwentts_key")
    _make_action(ui, "actionopenairecognapi_key")
    _make_action(ui, "actionparakeet_key")
    _make_action(ui, "actionai302_key")
    _make_action(ui, "actionlocalllm_key")
    _make_action(ui, "actionzijiehuoshan_key")
    _make_action(ui, "actiondeepL_key")
    _make_action(ui, "actionazure_tts")
    _make_action(ui, "action_ffmpeg")
    _make_action(ui, "action_git")
    _make_action(ui, "action_issue")
    _make_action(ui, "actiondeepLX_address")
    _make_action(ui, "actionclone_address")
    _make_action(ui, "actionkokoro_address")
    _make_action(ui, "actionchattts_address")
    _make_action(ui, "actiontts_api")
    _make_action(ui, "actionminimaxi_api")
    _make_action(ui, "actiontrans_api")
    _make_action(ui, "actionrecognapi")
    _make_action(ui, "actionsttapi")
    _make_action(ui, "actionwhisperx")
    _make_action(ui, "actiondeepgram")
    _make_action(ui, "actionxxl")
    _make_action(ui, "actioncpp")
    _make_action(ui, "actionzijierecognmodel_api")
    _make_action(ui, "actiontts_gptsovits")
    _make_action(ui, "actiontts_chatterbox")
    _make_action(ui, "actiontts_cosyvoice")
    _make_action(ui, "actiontts_omnivoice")
    _make_action(ui, "actiontts_qwenttslocal")
    _make_action(ui, "actiontts_fishtts")
    _make_action(ui, "actiontts_f5tts")
    _make_action(ui, "actiontts_refaudio")
    _make_action(ui, "actiontts_doubao2")
    _make_action(ui, "action_website")
    _make_action(ui, "action_blog")
    _make_action(ui, "action_discord")
    _make_action(ui, "action_gtrans")
    _make_action(ui, "action_cuda")
    _make_action(ui, "action_online")
    _make_action(ui, "actiontencent_key")
    _make_action(ui, "action_about")

    ui.action_biaozhun = QtGui.QAction()
    ui.action_biaozhun.setCheckable(True)
    ui.action_biaozhun.setChecked(True)
    ui.action_biaozhun.setObjectName("action_biaozhun")

    _make_action(ui, "action_yuyinshibie")
    _make_action(ui, "action_yuyinhecheng")

    ui.action_tiquzimu = QtGui.QAction()
    ui.action_tiquzimu.setCheckable(True)
    ui.action_tiquzimu.setObjectName("action_tiquzimu")

    _make_action(ui, "action_yingyinhebing")
    _make_action(ui, "action_clipvideo")
    _make_action(ui, "action_realtime_stt")
    _make_action(ui, "action_textmatching")
    _make_action(ui, "action_hun")
    _make_action(ui, "action_fanyi")
    _make_action(ui, "action_hebingsrt")
    _make_action(ui, "action_clearcache")
    _make_action(ui, "action_set_proxy")
    _make_action(ui, "actionazure_key")
    _make_action(ui, "actiongemini_key")
    _make_action(ui, "actioncamb_key")
    _make_action(ui, "actionElevenlabs_key")
    _make_action(ui, "actionwatermark")
    _make_action(ui, "actionsepar")
    _make_action(ui, "actionsetini")
    ui.actionvideoandaudio = QtGui.QAction()
    ui.actionvideoandaudio.setObjectName("videoandaudio")
    ui.actionvideoandaudio = QtGui.QAction()
    ui.actionvideoandaudio.setObjectName("videoandaudio")
    _make_action(ui, "actionvideoandsrt")
    _make_action(ui, "actionformatcover")
    _make_action(ui, "actionsubtitlescover")
    _make_action(ui, "actionsrtmultirole")
    _make_action(ui, "action_yinshipinfenli")

    _fill_menu(ui.menu_Key, [
        ui.actionbaidu_key, ui.actionali_key, ui.actiontencent_key,
        ui.actionai302_key, ui.actionchatgpt_key, ui.actionlocalllm_key,
        ui.actionzhipuai_key, ui.actionsiliconflow_key, ui.actiondeepseek_key,
        ui.actionxiaomi_key, ui.actionminimax_key, ui.actionqwenmt_key,
        ui.actionopenrouter_key, ui.actionlibretranslate_key,
        ui.actionzijiehuoshan_key, ui.actionazure_key, ui.actiongemini_key,
        ui.actioncamb_key, ui.actiondeepL_key, ui.actiondeepLX_address,
        ui.actiontrans_api,
    ])

    _fill_menu(ui.menu_TTS, [
        ui.actiontts_refaudio, ui.actionclone_address, ui.actionkokoro_address,
        ui.actionchattts_address, ui.actiontts_gptsovits, ui.actiontts_omnivoice,
        ui.actiontts_cosyvoice, ui.actiontts_qwenttslocal, ui.actionqwentts_key,
        ui.actiontts_fishtts, ui.actiontts_f5tts, ui.actionai302_key,
        ui.actiontts_doubao2, ui.actionElevenlabs_key, ui.actionazure_tts,
        ui.actionxaitts_key, ui.actionopenaitts_key, ui.actionminimaxi_api,
        ui.actiontts_api, ui.actiontts_chatterbox,
    ])

    _fill_menu(ui.menu_RECOGN, [
        ui.actionzijierecognmodel_api, ui.actionopenairecognapi_key,
        ui.actionparakeet_key, ui.actionrecognapi, ui.actionai302_key,
        ui.actionsttapi, ui.actionwhisperx, ui.actiondeepgram,
        ui.actionxxl, ui.actioncpp,
    ])

    _fill_menu(ui.menu, [
        ui.actionsetini, ui.action_clipvideo, ui.actionwatermark,
        ui.action_realtime_stt, ui.action_textmatching, ui.action_yingyinhebing,
        ui.actionvideoandaudio, ui.actionvideoandsrt, ui.actionformatcover,
        ui.actionsubtitlescover, ui.actionsrtmultirole, ui.action_yinshipinfenli,
        ui.action_hun, ui.action_hebingsrt, ui.actionsepar, ui.action_set_proxy,
    ])
    ui.menu.addAction(ui.action_clearcache)
    ui.menu.addSeparator()

    _fill_menu_h(ui.menu_H, [
        ui.action_website, ui.action_blog, ui.action_discord,
        ui.action_gtrans, ui.action_cuda, ui.action_git, ui.action_issue,
        ui.action_ffmpeg, ui.action_online, ui.action_about,
    ])

    ui.menuBar.addAction(ui.menu_Key.menuAction())
    ui.menuBar.addAction(ui.menu_TTS.menuAction())
    ui.menuBar.addAction(ui.menu_RECOGN.menuAction())
    ui.menuBar.addAction(ui.menu.menuAction())
    ui.menuBar.addAction(ui.menu_H.menuAction())

    ui.toolBar.addAction(ui.action_biaozhun)
    ui.toolBar.addAction(ui.action_tiquzimu)
    ui.toolBar.addAction(ui.action_yuyinshibie)
    ui.toolBar.addAction(ui.action_fanyi)
    ui.toolBar.addAction(ui.action_yuyinhecheng)
    ui.toolBar.addAction(ui.actionsrtmultirole)
    ui.toolBar.addAction(ui.action_yingyinhebing)
