from sqlalchemy import Column, Integer, String, Text
from app.database import Base


class MSDSIndex(Base):
    __tablename__ = "msds_indexes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False, unique=True)
    product_name_cn = Column(String(200))
    product_name_en = Column(String(200))
    physical_form = Column(String(100))
    ion_type = Column(String(50))
    ph = Column(String(50))
    composition_summary = Column(Text)
    file_path = Column(String(500), nullable=False)
    loaded = Column(Integer, default=0)