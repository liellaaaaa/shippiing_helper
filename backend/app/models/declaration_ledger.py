from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class HsCodeField(Base):
    """HS Code 字段定义表 - 存储每个 HS Code 应该有哪些申报要素字段"""
    __tablename__ = "hs_code_fields"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hs_code = Column(String(20), nullable=False, index=True)
    field_name = Column(String(100), nullable=False)
    field_type = Column(String(20), default="text")  # text/textarea/select
    sort_order = Column(Integer, default=0)
    is_required = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("hs_code", "field_name", name="uq_hs_code_fields"),
    )


class DeclarationProduct(Base):
    """申报产品表 - 存储每个 HS Code 下的产品"""
    __tablename__ = "declaration_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hs_code = Column(String(20), nullable=False, index=True)
    product_name = Column(String(200), nullable=False)
    website_name = Column(String(200))
    product_description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("hs_code", "product_name", name="uq_declaration_products"),
    )

    values = relationship("DeclarationValue", back_populates="product", cascade="all, delete-orphan")


class DeclarationValue(Base):
    """申报要素值表 - 存储每个产品的申报要素值"""
    __tablename__ = "declaration_values"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("declaration_products.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(100), nullable=False)
    field_value = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("product_id", "field_name", name="uq_declaration_values"),
    )

    product = relationship("DeclarationProduct", back_populates="values")
