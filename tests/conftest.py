"""
conftest.py — sets up mocks for heavy dependencies so videotrans
modules can be imported without a full PySide6 / torch installation.

Only mocks packages that are genuinely NOT installed.
"""

import importlib
import sys
from unittest.mock import MagicMock


def _is_installed(name):
    """Check if a package is actually importable (not just in sys.modules)."""
    try:
        spec = importlib.util.find_spec(name)
        return spec is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


_HAS_PYSIDE6 = _is_installed("PySide6")
_HAS_TORCH = _is_installed("torch")
_HAS_REQUESTS = _is_installed("requests")
_HAS_TENACITY = _is_installed("tenacity")
_HAS_OPENAI = _is_installed("openai")
_HAS_DEEPGRAM = _is_installed("deepgram")
_HAS_ELEVENLABS = _is_installed("elevenlabs")
_HAS_AIOHTTP = _is_installed("aiohttp")
_HAS_HTTPCORE = _is_installed("httpcore")
_HAS_HTTPX = _is_installed("httpx")
_HAS_HF_HUB = _is_installed("huggingface_hub")
_HAS_TENVAD = _is_installed("ten_vad")
_HAS_PYDUB = _is_installed("pydub")

if not _HAS_PYSIDE6:
    _pyside_mock = MagicMock()
    _pyside_mock.QtCore = MagicMock()
    _pyside_mock.QtCore.QObject = type("QObject", (), {})
    _pyside_mock.QtCore.QThread = type("QThread", (), {})
    _pyside_mock.QtCore.Signal = MagicMock(return_value=MagicMock())
    _pyside_mock.QtCore.QLocale = MagicMock()
    _pyside_mock.QtCore.Qt = MagicMock()
    _pyside_mock.QtCore.Slot = lambda *a, **kw: lambda f: f
    _pyside_mock.QtCore.QSettings = MagicMock()
    _pyside_mock.QtCore.QTimer = MagicMock()
    _pyside_mock.QtCore.QEvent = MagicMock()
    _pyside_mock.QtCore.QCoreApplication = MagicMock()
    _pyside_mock.QtCore.QThreadPool = MagicMock()
    _pyside_mock.QtCore.QThreadPool.globalInstance = MagicMock()
    _pyside_mock.QtGui.QIcon = MagicMock()
    _pyside_mock.QtGui.QPixmap = MagicMock()
    _pyside_mock.QtGui.QGuiApplication = MagicMock()
    _pyside_mock.QtGui.QTextCursor = MagicMock()
    _pyside_mock.QtWidgets.QApplication = MagicMock()
    _pyside_mock.QtWidgets.QMainWindow = type("QMainWindow", (), {})
    _pyside_mock.QtWidgets.QWidget = type("QWidget", (), {})
    _pyside_mock.QtWidgets.QFileDialog = MagicMock()
    _pyside_mock.QtWidgets.QMessageBox = MagicMock()
    _pyside_mock.QtWidgets.QLabel = MagicMock()
    _pyside_mock.QtWidgets.QVBoxLayout = MagicMock()
    _pyside_mock.QtWidgets.QPushButton = MagicMock()

    sys.modules["PySide6"] = _pyside_mock
    sys.modules["PySide6.QtCore"] = _pyside_mock.QtCore
    sys.modules["PySide6.QtGui"] = _pyside_mock.QtGui
    sys.modules["PySide6.QtWidgets"] = _pyside_mock.QtWidgets

# Exception base classes for isinstance() checks in excepts.py
if not _HAS_TENACITY:
    _m = MagicMock()
    _m.RetryError = type("RetryError", (Exception,), {})
    sys.modules["tenacity"] = _m

if not _HAS_OPENAI:
    _m = MagicMock()
    for _n in ("AuthenticationError", "PermissionDeniedError", "NotFoundError",
               "BadRequestError", "RateLimitError", "APIConnectionError",
               "APIError", "ContentFilterFinishReasonError", "InternalServerError",
               "LengthFinishReasonError", "UnprocessableEntityError"):
        setattr(_m, _n, type(_n, (Exception,), {}))
    sys.modules["openai"] = _m

def _make_pkg(name, attrs=None):
    """Create a mock package that supports subpackage imports."""
    import types
    m = types.ModuleType(name)
    if attrs:
        for k, v in attrs.items():
            setattr(m, k, v)
    return m


if not _HAS_DEEPGRAM:
    # Full subpackage chain for: from deepgram.clients.common.v1.errors import DeepgramApiError
    sys.modules["deepgram.clients.common.v1.errors"] = _make_pkg(
        "deepgram.clients.common.v1.errors",
        {"DeepgramApiError": type("DeepgramApiError", (Exception,), {})}
    )
    for _pkg in ("deepgram.clients.common.v1", "deepgram.clients.common", "deepgram.clients"):
        sys.modules[_pkg] = _make_pkg(_pkg)
    sys.modules["deepgram"] = _make_pkg("deepgram")

if not _HAS_ELEVENLABS:
    sys.modules["elevenlabs.core"] = _make_pkg(
        "elevenlabs.core",
        {"ApiError": type("ApiError_11", (Exception,), {})}
    )
    sys.modules["elevenlabs"] = _make_pkg("elevenlabs")

if not _HAS_AIOHTTP:
    _ce = MagicMock()
    _ce.ClientProxyConnectionError = type("ClientProxyConnectionError", (Exception,), {})
    sys.modules["aiohttp.client_exceptions"] = _ce
    _a = MagicMock()
    _a.client_exceptions = _ce
    sys.modules["aiohttp"] = _a

if not _HAS_HTTPCORE:
    _m = MagicMock()
    for _n in ("ConnectTimeout", "ConnectError", "ReadError"):
        setattr(_m, _n, type(_n, (Exception,), {}))
    sys.modules["httpcore"] = _m

if not _HAS_HTTPX:
    _m = MagicMock()
    for _n in ("ProxyError", "ConnectError", "ConnectTimeout", "ReadError",
               "InvalidURL", "LocalProtocolError", "ProtocolError",
               "TooManyRedirects", "UnsupportedProtocol"):
        setattr(_m, _n, type(_n, (Exception,), {}))
    sys.modules["httpx"] = _m

if not _HAS_HF_HUB:
    sys.modules["huggingface_hub"] = MagicMock()

if not _HAS_TENVAD:
    _m = MagicMock()
    _m.TenVad = MagicMock()
    _m.VadOptions = MagicMock()
    sys.modules["ten_vad"] = _m

if not _HAS_PYDUB:
    _m = MagicMock()
    sys.modules["pydub"] = _m
    _ms = MagicMock()
    sys.modules["pydub.playback"] = _ms
