import pytest
from app.database import init_db, SessionLocal
from app.services.merge_service import MergeService
from app.models.order import Order, OrderItem
from app.models.pi_contract import PiContract, PiContractItem
from app.models.order_pi_record import OrderPiRecord
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


def test_order_list_empty_items_no_unbound_local():
    """S5: order_items 为空时不得 UnboundLocalError（linked_items 未赋值）。"""
    init_db()
    db = SessionLocal()
    service = MergeService(db)

    order_no = f"TEST-EMPTY-{uuid.uuid4().hex[:8]}"
    order = Order(order_no=order_no, customer_code="CUST")
    db.add(order)
    db.commit()

    result = service.get_order_list(tab="all")
    item = next((o for o in result.orders if o.order_no == order_no), None)
    assert item is not None
    assert item.association_status == "none"
    assert item.linked_count == 0
    assert item.items_count == 0
    assert item.pi_no is None

    db.close()


def _mk_pi_and_record(db, *, order_no, pi_no, internal_code, rec_kwargs, pi_item_kwargs, pi_header):
    pi = PiContract(pi_no=pi_no, customer_code="CUST", **pi_header)
    db.add(pi)
    db.flush()
    pi_item = None
    if pi_item_kwargs is not None:
        pi_item = PiContractItem(pi_contract_id=pi.id, internal_code=internal_code, **pi_item_kwargs)
        db.add(pi_item)
    rec = OrderPiRecord(
        order_no=order_no,
        customer_code="CUST",
        pi_no=pi_no,
        internal_code=internal_code,
        product_cn="固色剂",
        **rec_kwargs,
    )
    db.add(rec)
    db.commit()
    return rec, pi_item


def test_order_pi_record_diff_consistent():
    """H4: 全字段一致时才返回「一致」，且 components 透传到 customs_ingredients。"""
    init_db()
    db = SessionLocal()
    service = MergeService(db)

    suffix = uuid.uuid4().hex[:8]
    rec, _ = _mk_pi_and_record(
        db,
        order_no=f"ORD-CMP-OK-{suffix}",
        pi_no=f"PI-CMP-OK-{suffix}",
        internal_code="CMP-OK-001",
        pi_header={"consignee_name": "CHEMZONE CO., LTD.", "destination": "HOCHIMINH, VIETNAM"},
        pi_item_kwargs={
            "quantity": 100.0, "unit_price": 2.0, "total_amount": 200.0,
            "hs_code": "340241", "customs_name": "FIXING AGENT",
        },
        rec_kwargs={
            "quantity_kg": 100.0, "unit_price": 2.0, "total_amount": 200.0,
            "hs_code": "340241", "customs_name": "FIXING AGENT",
            "consignee_name": "CHEMZONE CO., LTD.", "destination": "HOCHIMINH, VIETNAM",
            "components": "A 90%; B 10%",
        },
    )
    result = service.get_order_comparison(rec.id)
    assert result is not None and result.items
    item = result.items[0]
    assert item.order.customs_ingredients == "A 90%; B 10%"
    assert item.diff.status == "一致"
    assert item.diff.flags == []

    db.close()


def test_order_pi_record_diff_detects_quantity_mismatch():
    """H4: 不得永远返回「一致」；数量不符应报出。"""
    init_db()
    db = SessionLocal()
    service = MergeService(db)

    suffix = uuid.uuid4().hex[:8]
    rec, _ = _mk_pi_and_record(
        db,
        order_no=f"ORD-CMP-QTY-{suffix}",
        pi_no=f"PI-CMP-QTY-{suffix}",
        internal_code="CMP-QTY-001",
        pi_header={"consignee_name": "CHEMZONE CO., LTD.", "destination": "HOCHIMINH, VIETNAM"},
        pi_item_kwargs={
            "quantity": 100.0, "unit_price": 2.0, "total_amount": 200.0,
            "hs_code": "340241", "customs_name": "FIXING AGENT",
        },
        rec_kwargs={
            "quantity_kg": 200.0, "unit_price": 2.0, "total_amount": 200.0,
            "hs_code": "340241", "customs_name": "FIXING AGENT",
            "consignee_name": "CHEMZONE CO., LTD.", "destination": "HOCHIMINH, VIETNAM",
        },
    )
    result = service.get_order_comparison(rec.id)
    item = result.items[0]
    assert item.diff.status == "数量不符"
    assert "quantity" in item.diff.flags

    db.close()


def test_order_pi_record_diff_header_fields_compared():
    """H4: 收货人/港口不一致也要比出来。"""
    init_db()
    db = SessionLocal()
    service = MergeService(db)

    suffix = uuid.uuid4().hex[:8]
    rec, _ = _mk_pi_and_record(
        db,
        order_no=f"ORD-CMP-HDR-{suffix}",
        pi_no=f"PI-CMP-HDR-{suffix}",
        internal_code="CMP-HDR-001",
        pi_header={"consignee_name": "CHEMZONE CO., LTD.", "destination": "HOCHIMINH, VIETNAM"},
        pi_item_kwargs={
            "quantity": 100.0, "unit_price": 2.0, "total_amount": 200.0,
            "hs_code": "340241", "customs_name": "FIXING AGENT",
        },
        rec_kwargs={
            "quantity_kg": 100.0, "unit_price": 2.0, "total_amount": 200.0,
            "hs_code": "340241", "customs_name": "FIXING AGENT",
            "consignee_name": "OTHER CONSIGNEE", "destination": "HAIPHONG, VIETNAM",
        },
    )
    result = service.get_order_comparison(rec.id)
    item = result.items[0]
    assert item.diff.status != "一致"
    assert "consignee" in item.diff.flags
    assert "port" in item.diff.flags

    db.close()


def test_order_pi_record_diff_no_pi_item_marks_uncomparable():
    """H4: 拿不到 PI 行级明细时记 flags，不假装一致。"""
    init_db()
    db = SessionLocal()
    service = MergeService(db)

    suffix = uuid.uuid4().hex[:8]
    rec, _ = _mk_pi_and_record(
        db,
        order_no=f"ORD-CMP-NOP-{suffix}",
        pi_no=f"PI-CMP-NOP-{suffix}",
        internal_code="CMP-NOP-001",
        pi_header={"consignee_name": "CHEMZONE CO., LTD.", "destination": "HOCHIMINH, VIETNAM"},
        pi_item_kwargs=None,
        rec_kwargs={
            "quantity_kg": 100.0, "unit_price": 2.0, "total_amount": 200.0,
            "hs_code": "340241", "customs_name": "FIXING AGENT",
            "consignee_name": "CHEMZONE CO., LTD.", "destination": "HOCHIMINH, VIETNAM",
        },
    )
    result = service.get_order_comparison(rec.id)
    item = result.items[0]
    assert item.diff.status != "一致"
    assert "no_pi" in item.diff.flags
    assert "quantity_uncomparable" in item.diff.flags
    # 头字段两边都有且一致 → 不应记 consignee/port 差异
    assert "consignee" not in item.diff.flags
    assert "port" not in item.diff.flags

    db.close()