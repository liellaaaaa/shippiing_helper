from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class MSDSCorrection(Base):
    """Keeps history when a user uploads a corrected MSDS file."""
    __tablename__ = "msds_corrections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    msds_index_id = Column(Integer, ForeignKey("msds_indexes.id"), nullable=False)
    file_format = Column(String(10))   # "pdf" or "doc"
    upload_timestamp = Column(DateTime, default=func.now())
    product_name = Column(String(200))   # extracted from uploaded file
    corrected_by = Column(String(100))   # user identifier
    original_filename = Column(String(255))   # the file being corrected
    new_filename = Column(String(255))   # timestamped copy saved to disk