from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..db_models import Dataset
from ..schemas import DatasetSummary
from ..config import UPLOAD_DIR
from pathlib import Path

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=list[DatasetSummary])
def get_history(
    db: Session = Depends(get_db),
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    q = db.query(Dataset)
    if search:
        q = q.filter(Dataset.original_filename.ilike(f"%{search}%"))
    if status:
        q = q.filter(Dataset.status == status)
    return q.order_by(Dataset.uploaded_at.desc()).all()


@router.delete("/{dataset_id}")
def delete_history_item(dataset_id: str, db: Session = Depends(get_db)):
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    try:
        file_path = Path(ds.file_path)
        if file_path.exists() and file_path.is_relative_to(UPLOAD_DIR):
            file_path.unlink()
    except Exception:
        pass

    db.delete(ds)
    db.commit()
    return {"deleted": True, "id": dataset_id}
