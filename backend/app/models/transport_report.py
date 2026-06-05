from sqlalchemy import Column, Integer, String
from app.database import Base


class TransportReport(Base):
    """海运鉴定报告索引（来自 references/海运鉴定报告/ 目录）。"""
    __tablename__ = "transport_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False, unique=True)
    file_path = Column(String(500), nullable=False)
    file_format = Column(String(10), default="pdf")  # 固定是 pdf
    loaded = Column(Integer, default=0)
