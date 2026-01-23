# 定义一个工厂函数，返回配置好的 Session
import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry


def custom_session_factory():
    sess = requests.Session()
    # 配置重试策略
    retries = Retry(
        total=3,  # 总重试次数 (改为3)
        connect=2,  # 连接重试次数
        read=2,  # 读取重试次数
        backoff_factor=1,  # 重试间隔时间 (秒)，避免瞬间频繁请求
        status_forcelist=[500, 502, 503, 504]  # 遇到这些状态码才重试
    )

    # 将重试策略挂载到 http 和 https 协议上
    adapter = HTTPAdapter(max_retries=retries)
    sess.mount('http://', adapter)
    sess.mount('https://', adapter)
    return sess
