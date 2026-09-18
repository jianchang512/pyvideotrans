from PySide6 import QtCore, QtGui, QtWidgets
from videotrans.ui.menu_list import MENU_CFG_TRANS, MENU_CFG_TTS, MENU_CFG_STT, MENU_CFG_TOOLS, MENU_CFG_HELP, \
    MENU_CFG_PANEL
from videotrans.util.help_misc import open_url, show_popup
from videotrans.winform import get_win


def _make_action(ui, obj=None,menu=None,add_hr=True):
    print(f'{obj=}')
    k,title,_inst=obj
    action = QtGui.QAction()
    action.setObjectName(k)
    action.setText(title)
    setattr(ui, k, action)
    if _inst is not False:
        if _inst is None:
            action.triggered.connect(lambda :get_win(k))
        elif isinstance(_inst,str) and _inst.startswith('http'):
            action.triggered.connect(lambda :open_url(_inst))
        elif isinstance(_inst,str):
            action.triggered.connect(lambda :show_popup(title,_inst))

    if menu:
        menu.addAction(action)
        if add_hr:
            menu.addSeparator()
    return action



def _fill_menu(menu, actions):
    for action in actions:
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

    ui.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
    ui.toolBar.setFloatable(True)
    ui.toolBar.setObjectName("toolBar")
    ui.toolBar.setStyleSheet("""
    QToolBar QToolButton {
        min-width: 100px; 
        text-align: center; 
    }
""")
    MainWindow.addToolBar(QtCore.Qt.LeftToolBarArea, ui.toolBar)
    # 翻译设置
    for obj in MENU_CFG_TRANS:
        _make_action(ui, obj,ui.menu_Key)


    for obj in MENU_CFG_TTS:
        _make_action(ui, obj,ui.menu_TTS)

    for obj in MENU_CFG_STT:
        _make_action(ui, obj,ui.menu_RECOGN)

    for obj in MENU_CFG_TOOLS:
        _make_action(ui, obj,ui.menu)

    for obj in MENU_CFG_HELP:
        _make_action(ui, obj,ui.menu_H)


    for obj in MENU_CFG_PANEL:
        _make_action(ui, obj,ui.toolBar,False)











    ui.menuBar.addAction(ui.menu_Key.menuAction())
    ui.menuBar.addAction(ui.menu_TTS.menuAction())
    ui.menuBar.addAction(ui.menu_RECOGN.menuAction())
    ui.menuBar.addAction(ui.menu.menuAction())
    ui.menuBar.addAction(ui.menu_H.menuAction())

    # ui.toolBar.addAction(ui.action_biaozhun)
    # ui.toolBar.addAction(ui.action_tiquzimu)
    # ui.toolBar.addAction(ui.fn_recogn)
    # ui.toolBar.addAction(ui.fn_peiyin)
    # ui.toolBar.addAction(ui.fn_fanyisrt)
    # ui.toolBar.addAction(ui.fn_peiyinrole)
    # ui.toolBar.addAction(ui.fn_vas)
