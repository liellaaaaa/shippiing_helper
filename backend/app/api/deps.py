"""
FastAPI 依赖注入。
将服务层注入到路由中。
"""
from app.services.order_service import OrderService
from app.database import SessionLocal


def get_order_service() -> OrderService:
    """订单服务依赖注入"""
    return OrderService()


def get_pi_service():
    """PI合同服务依赖注入"""
    from app.services.pi_service import PiService
    return PiService(SessionLocal())