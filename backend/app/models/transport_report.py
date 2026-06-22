from sqlalchemy import Column, Integer, String
from app.database import Base


class TransportReport(Base):
    """海运鉴定报告索引（来自 references/海运鉴定报告/ 目录）。"""
    __tablename__ = "transport_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False, unique=True)
    file_path = Column(String(500), nullable=False)
    file_format = Column(String(10), default="pdf")
    loaded = Column(Integer, default=0)

    # 扫描 PDF 提取的字段
    report_no = Column(String(100), default="")
    product_name_cn = Column(String(255), default="")
    product_name_en = Column(String(255), default="")
    sample_desc_cn = Column(String(500), default="")
    sample_desc_en = Column(String(500), default="")
