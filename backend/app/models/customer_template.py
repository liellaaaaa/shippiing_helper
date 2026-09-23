"""客户定制清关模板 — 一客一单据类型一模板（录音方案 Phase C）"""
from sqlalchemy import Column, DateTime, Integer, LargeBinary, String, Text
from sqlalchemy.sql import func

from app.database import Base


class CustomerTemplate(Base):
    __tablename__ = "customer_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_code = Column(String(50), nullable=False, index=True)
    doc_type = Column(String(20), nullable=False)  # ci|pl|coa|si
    company_code = Column(String(20), nullable=True)
    # xlsx 模板（含 {{占位符}}；允许该客户加行、改固定文案）
    template_blob = Column(LargeBinary, nullable=False)
    # JSON：show_bank_block / ph_label / package_unit / extra_note_lines 等
    options_json = Column(Text, nullable=True)
    file_name = Column(String(200), nullable=True)
    version = Column(Integer, default=1)
    is_active = Column(Integer, default=1)
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
