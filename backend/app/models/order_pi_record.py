from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class OrderPiRecord(Base):
    __tablename__ = "order_pi_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(100), index=True)
    customer_code = Column(String(100))
    customer_name = Column(String(200))
    pi_no = Column(String(100))
    sales_person = Column(String(100))
    order_date = Column(String(20))
    pi_date = Column(String(20))
    delivery_date = Column(String(20))
    internal_code = Column(String(100), index=True)
    product_cn = Column(String(200))
    product_en = Column(String(200))
    spec_kg = Column(Float)
    hs_code = Column(String(20))
    customs_name = Column(String(200))
    quantity_kg = Column(Float)
    unit_price = Column(Float)
    total_amount = Column(Float)
    order_requirement = Column(Text)
    notes = Column(Text)
    packaging_type_id = Column(Integer, ForeignKey("packaging_types.id"))
    pallet_spec = Column(String(20))
    drums_per_pallet = Column(Integer)
    drum_count = Column(Integer)
    pallet_count = Column(Integer)
    net_weight_kg = Column(Float)
    gross_weight_kg = Column(Float)
    volume_cbm = Column(Float)
    fits_20gp = Column(String(20))
    packaging_result_json = Column(Text)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    packaging_type = relationship("PackagingType")