from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from ..database import Base


class ExcelData(Base):
    __tablename__ = "excel_data"

    id = Column(Integer, primary_key=True, index=True)
    dataset = Column(String, nullable=False, index=True)
    sheet_name = Column(String, nullable=True)
    row_key = Column(String, nullable=True, index=True)
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
