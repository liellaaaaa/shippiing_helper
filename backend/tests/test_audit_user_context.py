# -*- coding: utf-8 -*-
"""审计用户上下文注入与回填归属的回归测试。"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("JWT_SECRET", "test-secret")

from jose import jwt as jose_jwt
from app.core.audit_decorator import (
    _decode_bearer_name,
    _get_client_ip,
    attach_user_from_jwt,
)


class _FakeRequest:
    def __init__(self, headers=None, client_host="10.0.0.1"):
        self.headers = headers or {}
        self.client = type("C", (), {"host": client_host})()


def test_user_from_auth_header_valid():
    token = jose_jwt.encode({"sub": "向嘉倩"}, "test-secret", algorithm="HS256")
    req = _FakeRequest({"authorization": f"Bearer {token}"})
    assert _decode_bearer_name(req) == "向嘉倩"


def test_user_from_auth_header_missing():
    assert _decode_bearer_name(_FakeRequest()) is None
    assert _decode_bearer_name(_FakeRequest({"authorization": "Basic x"})) is None


def test_user_from_auth_header_bad_token():
    req = _FakeRequest({"authorization": "Bearer not-a-jwt"})
    assert _decode_bearer_name(req) is None


def test_get_client_ip_forwarded():
    req = _FakeRequest({"X-Forwarded-For": "192.168.50.248, 10.0.0.1"})
    assert _get_client_ip(req) == "192.168.50.248"


def test_attach_user_from_jwt():
    token = jose_jwt.encode({"sub": "刘洁婷"}, os.environ["JWT_SECRET"], algorithm="HS256")
    req = _FakeRequest({"authorization": f"Bearer {token}"})
    req.state = type("S", (), {})()
    attach_user_from_jwt(req)
    assert req.state.user == {"name": "刘洁婷"}

    # 无效 token 不应写入
    req2 = _FakeRequest({"authorization": "Bearer bad"})
    req2.state = type("S", (), {})()
    attach_user_from_jwt(req2)
    assert getattr(req2.state, "user", None) is None


def test_ip_owner_map_covers_all_unknown_shapes():
    """回填脚本 IP 映射应覆盖月报中的 5 个业务 IP + 开发机。"""
    import importlib.util
    path = os.path.join(
        os.path.dirname(__file__), "..", "migrations", "022_backfill_audit_unknown_user.py"
    )
    spec = importlib.util.spec_from_file_location("backfill", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert set(mod.IP_OWNER) == {
        "192.168.50.248",
        "192.168.50.167",
        "192.168.50.119",
        "192.168.50.102",
        "192.168.50.230",
    }
    assert mod.IP_OWNER["192.168.50.248"] == "向嘉倩"
    assert mod.IP_OWNER["192.168.50.230"] == "肖聪"
