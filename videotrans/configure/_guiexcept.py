from PySide6.QtCore import QObject, Signal


class ExceptionHandler(QObject):
    # 一个信号，它会传递一个字符串参数（错误信息）
    show_exception_signal = Signal(str)


# 全局的单例实例，方便在任何地方调用
exception_handler = ExceptionHandler()


def global_exception_hook(exctype, value, tb):
    """
    发射信号。
    """
    import traceback
    tb_str = "".join(traceback.format_exception(exctype, value, tb))
    print(f"!!! UNHANDLED EXCEPTION !!!\n{tb_str}")

    exception_handler.show_exception_signal.emit(tb_str)
