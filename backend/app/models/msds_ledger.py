"""MSDS product ledger model."""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.sqlite import JSON
from app.database import Base


class MsdsLedger(Base):
    __tablename__ = "msds_product_ledger"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customs_name = Column(String(200), nullable=False, index=True)
    appearance = Column(String(500), nullable=False)
    ion_type = Column(String(50), nullable=False)
    ph = Column(String(50), nullable=False)
    composition = Column(JSON, nullable=False)
    product_name_en = Column(String(200))
    appearance_en = Column(String(500))
    ion_type_en = Column(String(50))
    version = Column(Integer, default=1)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
