from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class AuditLog(Base):
    """用户行为日志模型"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False, index=True)
    user_name = Column(String(100), nullable=False, index=True)
    module = Column(String(50), nullable=True)
    action_time = Column(DateTime, nullable=False, index=True)
    detail = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
