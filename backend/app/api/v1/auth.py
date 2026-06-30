"""Authentication API routes."""
from fastapi import APIRouter, HTTPException, status, Request
from datetime import datetime

from app.models.user import LoginRequest, TokenResponse
from app.services.auth_service import authenticate
from app.services.audit_service import AuditService
from app.database import SessionLocal

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


def get_client_ip(request: Request) -> str:
    """从请求中提取客户端 IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    """用户登录，写入 user_login 日志"""
    try:
        result = authenticate(body.name, body.password)

        # 记录登录日志
        audit = AuditService(SessionLocal())
        audit.log(
            event_type="user_login",
            user_name=body.name,
            action_time=datetime.now(),
            ip_address=get_client_ip(request),
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败: {str(e)}"
        )
