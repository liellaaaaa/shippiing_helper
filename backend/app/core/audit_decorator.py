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
    """中间件：检测带 audit_action 标记的路由，成功后自动写审计日志。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # 只记录成功的写操作（2xx）
        if response.status_code >= 400:
            return response

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

            # 从 request.state.user 获取用户名（auth_middleware 已设置）
            user = getattr(request.state, "user", None)
            user_name = user.get("name", "unknown") if user else "unknown"

            # 获取客户端 IP
            ip_address = _get_client_ip(request)

            try:
                from app.database import SessionLocal
                from app.services.audit_service import AuditService

                db = SessionLocal()
                try:
                    svc = AuditService(db)
                    svc.log(
                        event_type=meta["event_type"],
                        user_name=user_name,
                        module=meta["module"],
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
