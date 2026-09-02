import datetime
from typing import Any, Optional

from pydantic import BaseModel


class DatasetSummary(BaseModel):
    id: str
    original_filename: str
    uploaded_at: datetime.datetime
    row_count: int
    column_count: int
    missing_values: int
    duplicate_rows: int
    numeric_columns: int
    categorical_columns: int
    datetime_columns: int
    is_sample: bool
    status: str
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class DatasetDetail(DatasetSummary):
    schema_: dict[str, Any] = {}

    class Config:
        from_attributes = True
        populate_by_name = True
