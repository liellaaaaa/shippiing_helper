"""运输报告关联契约测试：POST /link 要求 JSON body（LinkRequest），link_order 取 func.max+1。"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal, init_db
from app.main import app
from app.models.order_item_transport_report import OrderItemTransportReport
from app.models.transport_report import TransportReport

client = TestClient(app)

# 测试用的固定 order_item_id（该接口不校验订单项是否存在）
ORDER_ITEM_ID = 990001


@pytest.fixture()
def report_ids():
    """创建 3 条运输鉴定报告，测试后清理。"""
    init_db()
    db = SessionLocal()
    tag = uuid.uuid4().hex[:8]
    ids = []
    try:
        for i in range(3):
            r = TransportReport(
                filename=f"TEST-LINK-{tag}-{i}.pdf",
                file_path=f"/tmp/TEST-LINK-{tag}-{i}.pdf",
            )
            db.add(r)
            db.flush()
            ids.append(r.id)
        # 清理该 order_item 可能残留的旧关联
        db.query(OrderItemTransportReport).filter(
            OrderItemTransportReport.order_item_id == ORDER_ITEM_ID
        ).delete()
        db.commit()
        yield ids
        db.query(OrderItemTransportReport).filter(
            OrderItemTransportReport.order_item_id == ORDER_ITEM_ID
        ).delete()
        db.query(TransportReport).filter(
            TransportReport.filename.like(f"TEST-LINK-{tag}-%")
        ).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def link(report_id: int, order_item_id: int = ORDER_ITEM_ID) -> dict:
    resp = client.post(
        "/api/v1/transport-reports/link",
        json={"order_item_id": order_item_id, "transport_report_id": report_id},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestLinkContract:
    def test_link_accepts_json_body(self, report_ids):
        """契约：JSON body {order_item_id, transport_report_id}，首条 link_order=1"""
        data = link(report_ids[0])
        assert data["link_id"]
        assert data["link_order"] == 1

    def test_link_rejects_query_params_without_body(self, report_ids):
        """旧前端写法（query + null body）必须被拒绝，避免静默写坏数据"""
        resp = client.post(
            "/api/v1/transport-reports/link",
            params={
                "order_item_id": ORDER_ITEM_ID,
                "transport_report_id": report_ids[0],
            },
        )
        assert resp.status_code == 422

    def test_link_order_uses_max_not_first_row(self, report_ids):
        """多条关联时 link_order = max+1。

        旧实现用 Query.scalar() 取单值：同 order_item 有多条关联时抛
        MultipleResultsFound；即使只返回第一行，遇到 link_order 乱序也会写错。
        """
        first = link(report_ids[0])
        second = link(report_ids[1])
        assert first["link_order"] == 1
        assert second["link_order"] == 2

        # 把第一条 link_order 改成 10，制造 max(10, 2) != first-row 的场景
        db = SessionLocal()
        try:
            db.query(OrderItemTransportReport).filter(
                OrderItemTransportReport.id == first["link_id"]
            ).update({"link_order": 10})
            db.commit()
        finally:
            db.close()

        third = link(report_ids[2])
        assert third["link_order"] == 11  # max(10, 2) + 1

    def test_link_duplicate_is_noop(self, report_ids):
        """重复关联返回已有关联，不新增 link_order"""
        first = link(report_ids[0])
        again = link(report_ids[0])
        assert again["link_id"] == first["link_id"]
        db = SessionLocal()
        try:
            count = db.query(OrderItemTransportReport).filter(
                OrderItemTransportReport.order_item_id == ORDER_ITEM_ID
            ).count()
            assert count == 1
        finally:
            db.close()
