import pytest
from app.database import init_db, SessionLocal
from app.services.merge_service import MergeService
from app.models.order import Order, OrderItem
from app.models.pi_contract import PiContract, PiContractItem
import uuid


def test_association_status_full():
    """当订单所有 items 均在 PI 中有匹配 → status = full"""
    init_db()
    db = SessionLocal()
    service = MergeService(db)

    # 创建一个订单，两个 items，均有关联 PI
    order_no = f"TEST-FULL-{uuid.uuid4().hex[:8]}"
    order = Order(order_no=order_no, customer_code="CUST")
    db.add(order)
    db.flush()

    item1 = OrderItem(order_id=order.id, internal_code="SILI-001", quantity_kg=100)
    item2 = OrderItem(order_id=order.id, internal_code="SILI-002", quantity_kg=200)
    db.add_all([item1, item2])

    pi = PiContract(pi_no=f"PI-FULL-{uuid.uuid4().hex[:8]}", customer_code="CUST")
    db.add(pi)
    db.flush()

    pi_item1 = PiContractItem(pi_contract_id=pi.id, internal_code="SILI-001", quantity=100)
    pi_item2 = PiContractItem(pi_contract_id=pi.id, internal_code="SILI-002", quantity=200)
    db.add_all([pi_item1, pi_item2])
    db.commit()

    result = service.get_order_list(tab="all")
    result_dict = result.model_dump()
    # order_no 应显示 partial 或 full
    item = next((o for o in result_dict["orders"] if o["order_no"] == order_no), None)
    assert item is not None
    assert item["association_status"] in ["full", "partial"]

    db.close()


def test_association_status_none():
    """当订单没有任何 items 在 PI 中有匹配 → status = none"""
    init_db()
    db = SessionLocal()
    service = MergeService(db)

    order_no = f"TEST-NONE-{uuid.uuid4().hex[:8]}"
    order = Order(order_no=order_no, customer_code="CUST")
    db.add(order)
    db.flush()

    item = OrderItem(order_id=order.id, internal_code="SILI-999", quantity_kg=100)
    db.add(item)
    db.commit()

    result = service.get_order_list(tab="pending")
    result_dict = result.model_dump()
    item = next((o for o in result_dict["orders"] if o["order_no"] == order_no), None)
    assert item is not None
    assert item["association_status"] == "none"

    db.close()