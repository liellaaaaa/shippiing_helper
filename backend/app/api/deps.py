"""
FastAPI 依赖注入。
将服务层注入到路由中。
"""
from app.services.order_service import OrderService


def get_order_service() -> OrderService:
    """订单服务依赖注入"""
    return OrderService()