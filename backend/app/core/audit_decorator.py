"""
审计装饰器 — 标记路由函数，由 AuditMiddleware 自动记录审计日志。

用法：
    from app.core.audit_decorator import audit_action

    @router.post("/orders")
    @audit_action("order_save", "orders")
    async def save_order(...):
        ...

    @router.delete("/orders/ledger/{order_no}")
    @audit_action("ledger_delete", "orders")
    async def delete_ledger(order_no: str, ...):
        ...
"""
import asyncio
import functools
import inspect
import logging
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


def audit_action(event_type: str, module: str):
    """标记路由函数需要记录审计日志。AuditMiddleware 会在请求完成后自动调用。"""

    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            wrapper = async_wrapper
        else:
            wrapper = sync_wrapper

        wrapper._audit_meta = {"event_type": event_type, "module": module}
        return wrapper

    return decorator


class AuditMiddleware(BaseHTTPMiddleware):
    """中间件：检测带 audit_action 标记的路由，完成后自动写审计日志。

    同时记录失败（HTTP >= 400）以及业务软失败（endpoint 写入
    request.state.audit_detail），便于统计生成失败率、区分重试与失败。
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        try:
            endpoint = request.scope.get("endpoint")
            if endpoint is None:
                return response

            # 解包装饰器获取原始函数
            unwrapped = inspect.unwrap(endpoint)
            meta = getattr(unwrapped, "_audit_meta", None)
            if meta is None:
                meta = getattr(endpoint, "_audit_meta", None)
            if meta is None:
                return response

            # 优先取 auth_middleware 注入的用户；缺失时兜底解析 Authorization
            user = getattr(request.state, "user", None)
            user_name = user.get("name") if user else None
            if not user_name:
                user_name = _decode_bearer_name(request)
            if not user_name:
                user_name = "unknown"

            ip_address = _get_client_ip(request)

            # 结果埋点：HTTP 状态 + endpoint 可选业务结果
            detail = {"http_status": response.status_code}
            extra = getattr(request.state, "audit_detail", None)
            if isinstance(extra, dict):
                detail.update(extra)

            # 业务软失败（HTTP 200 但 body 为 error）由 endpoint 标记 ok=False
            ok = response.status_code < 400 and detail.get("ok", True)
            detail["ok"] = ok

            try:
                from app.database import SessionLocal
                from app.services.audit_service import AuditService

                db = SessionLocal()
                try:
                    svc = AuditService(db)
                    svc.log(
                        event_type=meta["event_type"] if ok else meta["event_type"] + "_failed",
                        user_name=user_name,
                        module=meta["module"],
                        detail=detail,
                        ip_address=ip_address,
                    )
                finally:
                    db.close()
            except Exception as e:
                logger.warning(f"审计日志写入失败: {e}")

        except Exception as e:
            logger.warning(f"审计中间件异常: {e}")

        return response


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _decode_bearer_name(request: Request):
    """从 Authorization Bearer JWT 解析用户名；无效则返回 None。"""
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    try:
        import os
        from jose import jwt

        secret = os.getenv("JWT_SECRET", "shipping-helper-secret-key-change-in-production")
        payload = jwt.decode(auth_header[7:], secret, algorithms=["HS256"])
        return payload.get("sub") or None
    except Exception:
        return None


def attach_user_from_jwt(request: Request) -> None:
    """若请求带合法 JWT，则写入 request.state.user（供审计溯源）。

    白名单路径也会执行：前端本就会上报 Authorization，但此前白名单
    直接 return 导致 user 从未注入，审计日志 user_name 落成 unknown。
    """
    name = _decode_bearer_name(request)
    if name:
        request.state.user = {"name": name}
