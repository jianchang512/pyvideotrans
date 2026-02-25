import re

import aiohttp
import requests
from elevenlabs.core import ApiError as ApiError_11
from openai import AuthenticationError, PermissionDeniedError, NotFoundError, BadRequestError, RateLimitError, \
    APIConnectionError, APIError, ContentFilterFinishReasonError, InternalServerError, LengthFinishReasonError
from requests.exceptions import TooManyRedirects, MissingSchema, InvalidSchema, InvalidURL, ProxyError, SSLError, \
    Timeout, ConnectionError as ReqConnectionError, RetryError, HTTPError
from deepgram.clients.common.v1.errors import DeepgramApiError
from videotrans.configure import config
from videotrans.configure.config import tr, params, settings, app_cfg, logger, defaulelang
import httpx, httpcore
from tenacity import RetryError as TenRetryError


# 内部已整理好错误提示消息的异常，将ex=None,message='{错误消息}'
class VideoTransError(Exception):
    def __init__(self, message=''):
        super().__init__(message)
        self.message=message
        

    def __str__(self):
        return str(self.message)


class TranslateSrtError(VideoTransError):
    pass


class DubbSrtError(VideoTransError):
    pass


class SpeechToTextError(VideoTransError):
    pass


class StopRetry(VideoTransError):
    pass




# 无需继续重试的异常
NO_RETRY_EXCEPT = (
    TooManyRedirects,  # 重定向次数过多
    MissingSchema,  # URL 缺少协议 (如 "http://")
    InvalidSchema,  # URL 协议无效
    InvalidURL,  # URL 格式无效
    SSLError,  # SSL 证书验证失败

    # 连接问题，检查网络或尝试设置代理
    RetryError,
    ReqConnectionError,
    ConnectionError,
    ConnectionRefusedError,  # 连接被拒绝
    ConnectionResetError,  # 连接被重置
    ConnectionAbortedError,  #

    httpx.ConnectError,
    httpx.ReadError,

    # 代理错误
    ProxyError,

    # openai 库的永久性错误 (通常是 4xx 状态码)
    AuthenticationError,  # 401 认证失败 (API Key 错误)
    PermissionDeniedError,  # 403 无权限访问该模型
    NotFoundError,  # 404 找不到资源 (例如模型名称错误)
    BadRequestError,  # 400 错误请求 (例如输入内容过长、参数无效等)

    LengthFinishReasonError,
    RateLimitError,

    DeepgramApiError,
    StopRetry
)

"""检查错误信息中是否包含本地地址"""


def _is_local_address(url_or_message):
    if not url_or_message:
        return False

    text = str(url_or_message).lower()
    local_indicators = ['127.0.0.1', 'localhost', '0.0.0.0', '::1', '[::1]']

    return any(indicator in text for indicator in local_indicators)


"""尝试从错误信息中提取API地址"""


def _extract_api_url_from_error(error):
    error_str = str(error)

    # 查找URL模式
    url_patterns = [
        r'https?://[^\s\'"]+',
        r'www\.[^\s\'"]+\.[a-z]{2,}',
        r'[a-zA-Z0-9.-]+\.[a-z]{2,}',
    ]

    for pattern in url_patterns:
        matches = re.findall(pattern, error_str)
        if matches:
            return matches[0]

    return None


"""处理连接错误的详细信息"""


def _handle_connection_error_detail(error, lang):
    error_str = str(error).lower()

    # 检查是否为本地地址
    is_local = _is_local_address(error_str)
    api_url = _extract_api_url_from_error(error)

    base_message = ""

    if "dns" in error_str or "name or service not known" in error_str:
        base_message = (
            "域名解析失败，无法找到服务器地址" if lang == 'zh'
            else "Domain name resolution failed, cannot find server address"
        )
    elif "ProxyError" in error_str:
        base_message = (
            "代理设置不正确或代理不可用，请检查代理或关闭代理并删掉代理文本框中所填内容" if lang == 'zh'
            else "The proxy address is not available, please check"
        )

    elif "refused" in error_str or "10061" in error_str or "积极拒绝" in error_str:
        if is_local:
            base_message = (
                "连接被拒绝，请确保本地服务已启动并正在运行" if lang == 'zh'
                else "Connection refused, please ensure the local service is started and running"
            )
        else:
            base_message = (
                "连接被拒绝，目标服务可能未运行或端口错误" if lang == 'zh'
                else "Connection refused, target service may not be running or wrong port"
            )
    elif "reset" in error_str:
        base_message = (
            "连接被重置，网络可能不稳定" if lang == 'zh'
            else "Connection reset, network may be unstable"
        )
    elif "timeout" in error_str or "timed out" in error_str:
        base_message = (
            "连接超时，请检查网络连接是否稳定" if lang == 'zh'
            else "Connection timeout, please check network stability"
        )
    elif "max retries exceeded" in error_str:
        if is_local:
            if "0.0.0.0" in error_str:
                base_message = (
                    "API 地址不可是 0.0.0.0 ，请修改为 127.0.0.1 " if lang == 'zh'
                    else "The API address cannot be 0.0.0.0, please change it to 127.0.0.1"
                )
            else:
                base_message = (
                    "多次重试连接失败，请确保本地服务已正确启动" if lang == 'zh'
                    else "Multiple connection retries failed, please ensure local service is properly started"
                )
        else:
            base_message = (
                "多次重试连接失败，服务可能暂时不可用" if lang == 'zh'
                else "Multiple connection retries failed, service may be temporarily unavailable"
            )

    else:
        base_message = (
            "网络连接失败" if lang == 'zh'
            else "Network connection failed"
        )

    # 为中文用户添加额外提示
    if lang == 'zh' and api_url and not is_local:
        if "api.msedgeservices.com" in api_url.lower():
            base_message += ". EdgeTTS使用频繁可能触发限流，请稍等段时间重试。"
            return base_message
        if "edge.microsoft.com" in api_url.lower():
            base_message += ". 微软翻译使用频繁可能触发限流，请稍等段时间重试。"
            return base_message
        # 检查是否为国外知名API服务
        foreign_apis = ['openai', 'anthropic', 'claude', 'elevenlabs', 'deepgram', 'google', 'aws.amazon']
        if any(api in api_url.lower() for api in foreign_apis):
            base_message += "。注意：某些国外服务需要科学上网才能访问"

    return base_message


"""处理API错误的详细信息"""


def _handle_api_error_detail(error, lang):
    message = ""

    # 尝试从各种API错误格式中提取消息
    if hasattr(error, 'body') and isinstance(error.body, dict):
        message = error.body.get('message') or error.body.get('error', {}).get('message', '')
    elif hasattr(error, 'message'):
        message = str(error.message)
    elif hasattr(error, 'detail'):
        if isinstance(error.detail, dict):
            message = error.detail.get('message') or error.detail.get('error', {}).get('message', '')
        else:
            message = str(error.detail)
    if _is_local_address(message):
        message = f'{"请确认本地服务已启动 " if lang == "zh" else "please ensure local service is properly started"} {message}'
    if message:

        return (
            f"服务返回错误：{message}" if lang == 'zh'
            else f"Service returned error: {message}"
        )
    else:
        return (
            "服务暂时不可用，请稍后重试" if lang == 'zh'
            else "Service temporarily unavailable, please try again later"
        )



# 根据异常类型，返回整理后的可读性错误消息
def get_msg_from_except(ex):
    if isinstance(ex, VideoTransError):
        return str(ex)
        
    lang = defaulelang
    if isinstance(ex, TenRetryError):
        try:
            ex = ex.last_attempt.exception()
        except AttributeError:
            pass

    # 异常处理映射
    exception_handlers = {
        # === 认证和权限问题 ===
        AuthenticationError: lambda e: (
            f"API密钥错误，请检查密钥是否正确 {e.message}" if lang == 'zh'
            else f"API key error, please check if the key is correct {e.message}"
        ),

        PermissionDeniedError: lambda e: (
            f"当前密钥没有访问权限，请检查权限设置 {e.message}" if lang == 'zh'
            else f"No access permission with current API key {e.message}"
        ),

        # === 频率限制 ===
        RateLimitError: lambda e: (
            f"请求过于频繁，请稍后重试或调大暂停时间 {e.message}" if lang == 'zh'
            else f"Too many requests, please try again later or adjust settings {e.message}"
        ),
        InternalServerError: lambda e: (
            f'{e.status_code} 错误: API服务端内部错误 {e.message}' if lang == 'zh' else f'{e.status_code}: {e.message}'),

        # === 资源不存在问题 ===
        NotFoundError: lambda e: (
            f"请求的资源不存在，请检查模型名称或API地址 {e.message}" if lang == 'zh'
            else f"Requested resource not found, check model name or API address {e.message}"
        ),

        # === 请求参数问题 ===
        BadRequestError: lambda e: (
            f"请求参数不正确:{e.message}" if lang == 'zh'
            else f"Request parameters incorrect, check input or settings {e.message}"
        ),

        APIConnectionError: lambda e: (
            _handle_connection_error_detail(e, lang)
        ),


        # === 服务端问题 ===
        APIError: lambda e: _handle_api_error_detail(e, lang),

        LengthFinishReasonError: lambda e: (
            f'内容太长超出最大允许Token，请减小内容或增大max_token,或者降低每次发送字幕行数\n{e}' if lang == 'zh' else f'{e}'),
        ContentFilterFinishReasonError: lambda
            e: f"内容触发AI风控被过滤 {e}" if lang == 'zh' else f'Content triggers AI risk control and is filtered\n{e}',



        # === 配置和地址问题 ===
        (TooManyRedirects, MissingSchema, InvalidSchema, InvalidURL): lambda e: (
            f"请求地址格式不正确，请检查配置 {e.message}" if lang == 'zh'
            else f"Request URL format is incorrect, check configuration {e.message}"
        ),

        (ProxyError, aiohttp.client_exceptions.ClientProxyConnectionError): lambda e: (
            "代理设置不正确或代理不可用，请检查代理或关闭代理并删掉代理文本框中所填内容" if lang == 'zh'
            else "Proxy configuration issue, check settings or disable proxy"
        ),
        SSLError: lambda e: (
            "安全连接失败，请检查系统时间或网络设置，如果使用了代理，请关闭后重试" if lang == 'zh'
            else "Secure connection failed, check system time or network settings"
        ),

        Timeout: lambda e: (
            _handle_connection_error_detail(e, lang)
        ),

        HTTPError: lambda e: f'{e}',

        RetryError: lambda e: (
            "重试多次后仍然失败，请检查网络连接或服务状态" if lang == 'zh'
            else "Failed after multiple retries, check network connection or service status"
        ),
        # === 网络连接问题 ===
        (httpcore.ConnectTimeout, httpx.ConnectTimeout, httpx.ConnectError, httpx.ReadError): lambda e: (
            _handle_connection_error_detail(e, lang)
        ),


        DeepgramApiError: lambda e: _handle_api_error_detail(e, lang),

        ApiError_11: lambda e: e.body.get('detail',{}).get('message',e.body),


        ConnectionRefusedError: lambda e: (
            _handle_connection_error_detail(e, lang)
        ),

        ConnectionResetError: lambda e: (
            _handle_connection_error_detail(e, lang)
        ),

        ConnectionAbortedError: lambda e: (
            "连接意外中断，请检查网络稳定性" if lang == 'zh'
            else "Connection aborted unexpectedly, check network stability"
        ),
        (ReqConnectionError, ConnectionError): lambda e: (
            _handle_connection_error_detail(e, lang)
        ),
        requests.exceptions.RequestException:lambda e:f'{e}',

        RuntimeError: lambda e: (f"{e}" if lang == 'zh' else f"{e}" ),

        FileNotFoundError: lambda e: (
            f"文件不存在：{getattr(e, 'filename', '')}" if lang == 'zh'
            else f"File not found: {getattr(e, 'filename', '')}"
        ),

        PermissionError: lambda e: (
            f"权限不足，无法访问：{getattr(e, 'filename', '')}" if lang == 'zh'
            else f"Permission denied: {getattr(e, 'filename', '')}"
        ),

        FileExistsError: lambda e: (
            f"文件已存在：{getattr(e, 'filename', '')}" if lang == 'zh'
            else f"File already exists: {getattr(e, 'filename', '')}"
        ),

        # === 操作系统错误 ===
        OSError: lambda e: (
            f"系统错误 ({e.errno})：{e.strerror}" if lang == 'zh'
            else f"System Error ({e.errno}): {e.strerror}"
        ),

        # === 数据处理错误 ===
        KeyError: lambda e: (
            f"处理数据时缺少必需的键：{e}" if lang == 'zh'
            else f"{e}"
        ),

        IndexError: lambda e: (
            f"处理列表或序列时索引越界:{e}" if lang == 'zh'
            else f"{e}"
        ),

        LookupError: lambda e: (
            f"查找错误，指定的键或索引不存在:{e}" if lang == 'zh'
            else f"{e}"
        ),

        UnicodeDecodeError: lambda e: (
            f"文件或数据解码失败，编码格式错误：{e.reason}" if lang == 'zh'
            else f" {e.reason}"
        ),

        ValueError: lambda e: (
            f"无效的值或参数：{e}" if lang == 'zh'
            else f"{e}"
        ),

        # === 程序内部错误 ===
        AttributeError: lambda e: (
            f"程序内部错误：{e}" if lang == 'zh'
            else f"{e}"
        ),

        NameError: lambda e: (
            f"程序内部错误：未定义的变量 '{e.name}'" if lang == 'zh' else f"{e}"
        ),

        TypeError: lambda e: (
            f"程序内部错误：{e}" if lang == 'zh'
            else f"{e}"
        ),

        RecursionError: lambda e: (
            f"程序内部错误：发生无限递归:{e}" if lang == 'zh'
            else f"{e}"
        ),

        ZeroDivisionError: lambda e: (
            f"算术错误：除数为零:{e}" if lang == 'zh'
            else f"{e}"
        ),

        OverflowError: lambda e: (
            f"算术错误：数值超出最大限制:{e}" if lang == 'zh'
            else f"{e}"
        ),

        BrokenPipeError: lambda e: (
            "连接管道损坏，请检查网络连接" if lang == 'zh'
            else "Broken pipe error, check network connection"
        ),
    }

    # 遍历映射，查找匹配的处理器
    for exc_types, handler in exception_handlers.items():
        if isinstance(ex, exc_types):
            return handler(ex)

    # === 后备处理逻辑 ===
    error_str = str(ex)
    if any(keyword in error_str.lower() for keyword in [
        'connection', 'connect', 'refused', 'reset', 'timeout', 'retries',
        '连接', '拒绝', '重置', '超时', '重试', 'host', 'port', 'http', 'tcp','ProxyError'
    ]):
        return _handle_connection_error_detail(ex, lang)

    # 尝试从异常对象中提取更具体的信息
    if hasattr(ex, 'error') and ex.error:
        if isinstance(ex.error, dict):
            error_msg = str(ex.error.get('message', ex.error))
        else:
            error_msg = str(ex.error)
        return (
            f"错误详情：{error_msg}" if lang == 'zh'
            else f"Error details: {error_msg}"
        )

    if hasattr(ex, 'message') and ex.message:
        return str(ex.message)

    if hasattr(ex, 'detail') and ex.detail:
        if isinstance(ex.detail, dict):
            message = ex.detail.get('message')
            if message:
                return str(message)
            error_info = ex.detail.get('error')
            if error_info:
                if isinstance(error_info, dict):
                    return str(error_info.get('message', error_info))
                return str(error_info)
        return str(ex.detail)

    if hasattr(ex, 'body') and ex.body:
        if isinstance(ex.body, dict):
            message = ex.body.get('message')
            if message:
                return str(message)
            error_info = ex.body.get('error')
            if error_info:
                if isinstance(error_info, dict):
                    return str(error_info.get('message', error_info))
                return str(error_info)
        return str(ex.body)

    # 默认错误消息
    return ''
