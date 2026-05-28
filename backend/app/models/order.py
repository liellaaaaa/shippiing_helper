from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(100), unique=True, nullable=False, index=True)
    customer_code = Column(String(100))
    customer_name = Column(String(200))
    pi_no = Column(String(100))
    salesperson = Column(String(100))
    merchandiser = Column(String(100))
    order_date = Column(String(20))
    production_deadline = Column(String(20))
    delivery_date = Column(String(20))
    shipment_date = Column(String(20))
    shipment_channel = Column(String(50))
    shipment_method = Column(String(50))
    order_confirmed = Column(String(20))
    order_status = Column(String(20), default="pending")
    locked_by = Column(String(100))
    locked_at = Column(DateTime)
    sales_area = Column(String(50))
    shipment_title = Column(String(200))
    document_type = Column(String(50))
    has_sample = Column(String(20))
    price_adjusted = Column(String(20))
    order_requirement = Column(Text)
    review_status = Column(String(20))
    spec_abnormal = Column(String(20))
    total_quantity_kg = Column(Float)
    total_gross_weight_kg = Column(Float)
    total_volume_cbm = Column(Float)
    fits_20gp = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    internal_code = Column(String(100), nullable=False)
    product_cn = Column(String(200))
    product_en = Column(String(200))
    spec_kg = Column(Float)
    hs_code = Column(String(20))
    customs_name = Column(String(200))
    customs_ingredients = Column(Text)
    quantity_kg = Column(Float)
    unit_price = Column(Float)
    total_amount = Column(Float)
    packaging_type_id = Column(Integer, ForeignKey("packaging_types.id"))
    pallet_spec = Column(String(20))
    drums_per_pallet = Column(Integer)
    drum_count = Column(Integer)
    pallet_count = Column(Integer)
    net_weight_kg = Column(Float)
    gross_weight_kg = Column(Float)
    volume_cbm = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = relationship("Order", back_populates="items")


class PackagingType(Base):
    __tablename__ = "packaging_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100))
    dims = Column(String(50))
    cbm = Column(Float)
    tare_kg = Column(Float)
    gross_kg = Column(Float)
    net_kg = Column(Float)
    barrel_type = Column(String(50))
    pallet_qty_1x1 = Column(Integer)
    pallet_qty_1_1x1_1 = Column(Integer)
    no_pallet_qty = Column(Integer)


class ProductKnowledge(Base):
    __tablename__ = "products_knowledge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    internal_code = Column(String(100), unique=True, index=True)
    product_name_cn = Column(String(200))
    product_name_en = Column(String(200))
    hs_code = Column(String(20))
    customs_name = Column(String(200))
    customs_ingredients = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)