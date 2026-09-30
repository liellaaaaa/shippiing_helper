"""SaveService — H3：PI 单值不覆盖多品，多品缺失字段留空。"""
import uuid

from app.database import init_db, SessionLocal
from app.models.order_pi_record import OrderPiRecord
from app.schemas.order_pi_record import OrderData, OrderDataItem, PiData, SaveRecordRequest
from app.services.save_service import SaveService


def _save(order_items, pi_data=None):
    init_db()
    db = SessionLocal()
    try:
        service = SaveService(db)
        suffix = uuid.uuid4().hex[:8]
        request = SaveRecordRequest(
            order_data=OrderData(
                order_no=f"SO-H3-{suffix}",
                customer_code="CUST",
                items=order_items,
            ),
            pi_data=pi_data,
        )
        first_id = service.save_record(request)
        records = (
            db.query(OrderPiRecord)
            .filter(OrderPiRecord.id >= first_id)
            .order_by(OrderPiRecord.id.asc())
            .all()
        )
        return records
    finally:
        db.close()


def test_multi_item_missing_fields_stay_none_no_pi_fallback():
    """H3：多产品订单某行为 0/None 时，不得回退订单级 PI 单值。"""
    pi = PiData(
        pi_no="PI-H3-MULTI",
        internal_code="A",
        quantity=999.0,
        unit_price=9.0,
        total_amount=9999.0,
    )
    records = _save(
        [
            OrderDataItem(
                internal_code="A",
                product_cn="产品A",
                quantity_kg=100.0,
                unit_price=2.0,
                total_amount=200.0,
            ),
            OrderDataItem(
                internal_code="B",
                product_cn="产品B",
                quantity_kg=None,
                unit_price=0,
                total_amount=None,
            ),
        ],
        pi_data=pi,
    )
    assert len(records) == 2
    by_code = {r.internal_code: r for r in records}

    # 有值的行保留自己的值
    assert by_code["A"].quantity_kg == 100.0
    assert by_code["A"].unit_price == 2.0
    assert by_code["A"].total_amount == 200.0

    # 缺失行留空 None，不回退 PI 的 999/9/9999
    assert by_code["B"].quantity_kg is None
    assert by_code["B"].unit_price is None
    assert by_code["B"].total_amount is None


def test_multi_item_zero_values_stay_none():
    pi = PiData(pi_no="PI-H3-ZERO", internal_code="A", quantity=50.0, unit_price=5.0, total_amount=50.0)
    records = _save(
        [
            OrderDataItem(internal_code="A", quantity_kg=10.0, unit_price=1.0, total_amount=10.0),
            OrderDataItem(internal_code="B", quantity_kg=0, unit_price=0, total_amount=0),
        ],
        pi_data=pi,
    )
    by_code = {r.internal_code: r for r in records}
    assert by_code["B"].quantity_kg is None
    assert by_code["B"].unit_price is None
    assert by_code["B"].total_amount is None


def test_single_item_still_falls_back_to_pi():
    """单品订单：缺失值仍回退 PI 单值（原行为保留）。"""
    pi = PiData(
        pi_no="PI-H3-SINGLE",
        internal_code="A",
        quantity=500.0,
        unit_price=3.5,
        total_amount=1750.0,
    )
    records = _save(
        [OrderDataItem(internal_code="A", quantity_kg=None, unit_price=0, total_amount=None)],
        pi_data=pi,
    )
    assert len(records) == 1
    assert records[0].quantity_kg == 500.0
    assert records[0].unit_price == 3.5
    assert records[0].total_amount == 1750.0


def test_multi_item_no_pi_missing_stays_none():
    """多品且无 PI：缺失字段也留空，不抛错。"""
    records = _save(
        [
            OrderDataItem(internal_code="A", quantity_kg=10.0, unit_price=1.0, total_amount=10.0),
            OrderDataItem(internal_code="B", quantity_kg=None, unit_price=None, total_amount=None),
        ],
        pi_data=None,
    )
    by_code = {r.internal_code: r for r in records}
    assert by_code["B"].quantity_kg is None
    assert by_code["B"].unit_price is None
    assert by_code["B"].total_amount is None
