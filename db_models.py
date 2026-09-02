import datetime
import uuid

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean
from sqlalchemy.orm import relationship

from .database import Base


def gen_id():
    return str(uuid.uuid4())


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String, primary_key=True, default=gen_id)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    missing_values = Column(Integer, default=0)
    duplicate_rows = Column(Integer, default=0)
    numeric_columns = Column(Integer, default=0)
    categorical_columns = Column(Integer, default=0)
    datetime_columns = Column(Integer, default=0)

    # JSON-serialized cached analysis, computed once on upload
    schema_json = Column(Text)  # column -> dtype / role
    quality_json = Column(Text)
    stats_json = Column(Text)
    charts_json = Column(Text)
    trends_json = Column(Text)
    anomalies_json = Column(Text)
    insights_json = Column(Text)
    recommendations_json = Column(Text)

    is_sample = Column(Boolean, default=False)
    status = Column(String, default="ready")  # ready | processing | error
    error_message = Column(Text, nullable=True)
