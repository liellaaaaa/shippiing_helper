from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class PiContract(Base):
    __tablename__ = "pi_contracts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pi_no = Column(String(100), nullable=False, index=True)
    customer_code = Column(String(100))
    sales_person = Column(String(100))
    pi_date = Column(String(20))
    is_ordered = Column(String(20), default="0")
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    # PI Header 信息
    consignee_name = Column(String(200))      # 收货人名称
    consignee_address = Column(String(500))   # 收货人地址
    destination = Column(String(200))         # 目的港
    loading_port = Column(String(200))         # 装货地
    price_term = Column(String(100))          # 价格条款 (FOB/C&F/CIF等)
    invoice_to = Column(String(200))          # 发票抬头 (另一收货人)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("PiContractItem", back_populates="contract", cascade="all, delete-orphan")


class PiContractItem(Base):
    __tablename__ = "pi_contract_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pi_contract_id = Column(Integer, ForeignKey("pi_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    internal_code = Column(String(100), nullable=True, index=True)
    quantity = Column(Float)
    unit_price = Column(Float)
    total_amount = Column(Float)
    product_color = Column(String(50))
    hs_code = Column(String(20))
    customs_name = Column(String(200))
    customs_composition = Column(Text)
    order_customs_name = Column(String(200))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contract = relationship("PiContract", back_populates="items")


class PiData(Base):
    __tablename__ = "pi_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    internal_code = Column(String(100), unique=True, nullable=False, index=True)
    product_color = Column(String(50))
    hs_code = Column(String(20))
    customs_name = Column(String(200))
    customs_composition = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)