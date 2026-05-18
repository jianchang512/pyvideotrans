from typing import Union
from PySide6.QtCore import QObject, Signal, Slot

from videotrans.task.taskcfg import SignMsg


class SignalHub(QObject):
    """单例信号中心，跨线程消息传递的核心桥梁。
    - 任意线程可调用 post()，消息自动排队到主线程处理
    """
    _instance = None
    # 信号: new_message(uuid: str, json_string: object)
    new_message = Signal(str, object)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._initialized = True

    @classmethod
    def instance(cls) -> 'SignalHub':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @Slot(str, object)
    def post(self, uuid: Union[str,None]=None, data: SignMsg=None):
        """从任意线程投递消息。
        Args:
            uuid: 任务 UUID，无 UUID 时传 ""（global 消息）
            data: dict 消息体，内部自动序列化为 JSON 字符串
            也可直接传 str（已序列化的 JSON）
        """

        self.new_message.emit(uuid, data)