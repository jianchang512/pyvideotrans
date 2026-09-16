import logging

import pytest

from videotrans.configure._redact import RedactFilter
from videotrans.configure.config import params


def _filtered_message(msg):
    record = logging.LogRecord("test", logging.INFO, __file__, 1, msg, None, None)
    RedactFilter().filter(record)
    return record.getMessage()


@pytest.mark.parametrize("name", ["baidu_miyue", "doubao2_access"])
def test_registered_secret_is_redacted(monkeypatch, name):
    secret = "Sup3rS3cretValue42"
    monkeypatch.setitem(params, name, secret)
    out = _filtered_message(f"request failed, {name}={secret}")
    assert secret not in out
    assert "***" in out


def test_non_secret_ids_are_kept(monkeypatch):
    monkeypatch.setitem(params, "baidu_appid", "20240101000123456")
    out = _filtered_message("appid 20240101000123456")
    assert "20240101000123456" in out
