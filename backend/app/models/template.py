from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func

from app.database import Base


class DocumentTemplate(Base):
    __tablename__ = "document_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # booking|msds
    file_path = Column(String(500), nullable=False)
    placeholders = Column(JSON, default=list)
    version = Column(Integer, default=1)
    updated_at = Column(DateTime, default=func.now())