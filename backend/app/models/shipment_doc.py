from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class ShipmentDoc(Base):
    __tablename__ = "shipment_docs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_key = Column(String(100), nullable=False, index=True)
    doc_type = Column(String(20), nullable=False)
    order_id = Column(Integer, nullable=True)
    file_blob = Column(Text, nullable=False)
    content_hash = Column(String(32), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    file_name = Column(String(200), nullable=False)
    change_reason = Column(Text, nullable=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)