import logging
import re
import threading

# 配置项名称以这些结尾时视为密钥，max_token 这类数值配置除外
_SECRET_NAME_RE = re.compile(r'(key|secret|secretid|token)$', re.I)
_NOT_SECRET_NAME_RE = re.compile(r'max_?tokens?$', re.I)
_MIN_SECRET_LEN = 6

_PATTERNS = [
    # URL 查询参数中的密钥，如 ?key=xxx、&sk=xxx、&secret=xxx
    (re.compile(r'([?&](?:key|sk|secret|token|api_key|apikey|access_token|auth_key)=)[^&\s\'"<>]+', re.I), r'\1***'),
    # Authorization: Bearer xxx
    (re.compile(r'(Bearer\s+)[A-Za-z0-9._~+/=-]{8,}', re.I), r'\1***'),
    # 常见密钥格式
    (re.compile(r'\bsk-[A-Za-z0-9_-]{16,}'), 'sk-***'),
    (re.compile(r'\bAIza[0-9A-Za-z_-]{30,}'), 'AIza***'),
    (re.compile(r'\bhf_[A-Za-z0-9]{20,}'), 'hf_***'),
]

_local = threading.local()


def _configured_secrets():
    """读取当前配置中已填写的密钥值"""
    secrets = set()
    try:
        from videotrans.configure.config import params, settings
        items = list(params.to_dict().items())
        items.append(('hf_token', settings.get('hf_token', '')))
    except Exception:
        return secrets
    for name, value in items:
        if not isinstance(value, str) or not _SECRET_NAME_RE.search(name) or _NOT_SECRET_NAME_RE.search(name):
            continue
        # gemini_key 等支持逗号分隔多个 Key
        for part in value.split(','):
            part = part.strip()
            if len(part) >= _MIN_SECRET_LEN and not part.isdigit():
                secrets.add(part)
    return secrets


def redact(text):
    """把文本中的密钥替换为 ***"""
    if not text:
        return text
    text = str(text)
    for secret in sorted(_configured_secrets(), key=len, reverse=True):
        if secret in text:
            text = text.replace(secret, '***')
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text


class RedactFilter(logging.Filter):
    def filter(self, record):
        # 读取配置时可能再次写日志，避免递归
        if getattr(_local, 'busy', False):
            return True
        _local.busy = True
        try:
            msg = record.getMessage()
            redacted = redact(msg)
            if redacted != msg:
                record.msg = redacted
                record.args = None
            if record.exc_info and not record.exc_text:
                record.exc_text = redact(logging.Formatter().formatException(record.exc_info))
        except Exception:
            pass
        finally:
            _local.busy = False
        return True
