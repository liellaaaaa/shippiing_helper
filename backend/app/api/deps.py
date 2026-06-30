"""
FastAPI 依赖注入。
将服务层注入到路由中。
"""
from app.services.order_service import OrderService
from app.services.merge_service import MergeService
from app.services.calculation_service import CalculationService
from app.services.save_service import SaveService
from app.database import SessionLocal


def get_order_service() -> OrderService:
    """订单服务依赖注入"""
    return OrderService()


def get_pi_service():
    """PI合同服务依赖注入"""
    from app.services.pi_service import PiService
    return PiService(SessionLocal())


def get_merge_service() -> MergeService:
    """数据关联服务依赖"""
    return MergeService(SessionLocal())


def get_calculation_service() -> CalculationService:
    """包装计算服务依赖"""
    return CalculationService()


def get_save_service() -> SaveService:
    """落库服务依赖"""
    return SaveService(SessionLocal())


def get_audit_service():
    """审计日志服务依赖注入"""
    from app.services.audit_service import AuditService
    return AuditService(SessionLocal())


"""JWT authentication dependency."""
from fastapi import Header, HTTPException, status
from jose import jwt, JWTError
import os

JWT_SECRET = os.getenv("JWT_SECRET", "shipping-helper-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"


async def get_current_user(authorization: str = Header(...)) -> dict:
    """从 Authorization header 提取并验证 JWT token，返回用户信息."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not authorization.startswith("Bearer "):
        raise credentials_exception
    token = authorization[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        name: str = payload.get("sub")
        if name is None:
            raise credentials_exception
        return {"name": name}
    except JWTError:
        raise credentials_exception