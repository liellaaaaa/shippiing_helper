from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from app.database import Base


class OrderItemTransportReport(Base):
    """订单产品 ↔ 运输鉴定报告关联表（多对多）。"""
    __tablename__ = "order_item_transport_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_item_id = Column(Integer, nullable=False)
    transport_report_id = Column(Integer, ForeignKey("transport_reports.id"), nullable=False)
    link_order = Column(Integer, default=0)      # 同一 order_item 下的第几个报告（1-based）
    linked_at = Column(DateTime, nullable=False)
