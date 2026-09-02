import json

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..db_models import Dataset
from ..services import dataset_service
from ..schemas import DatasetSummary

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


def _get_dataset_or_404(db: Session, dataset_id: str) -> Dataset:
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return ds


def _require_ready(ds: Dataset):
    if ds.status == "processing":
        raise HTTPException(status_code=409, detail="Dataset is still processing.")
    if ds.status == "error":
        raise HTTPException(status_code=422, detail=ds.error_message or "Dataset failed to process.")


@router.post("/upload", response_model=DatasetSummary)
async def upload_dataset(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        ds = dataset_service.process_and_store(db, raw, file.filename)
    except dataset_service.DatasetProcessingError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if ds.status == "error":
        raise HTTPException(status_code=422, detail=ds.error_message)

    return ds


@router.get("", response_model=list[DatasetSummary])
def list_datasets(db: Session = Depends(get_db)):
    return db.query(Dataset).order_by(Dataset.uploaded_at.desc()).all()


@router.get("/{dataset_id}", response_model=DatasetSummary)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    return _get_dataset_or_404(db, dataset_id)


@router.get("/{dataset_id}/preview")
def get_preview(dataset_id: str, rows: int = 25, db: Session = Depends(get_db)):
    ds = _get_dataset_or_404(db, dataset_id)
    _require_ready(ds)
    return dataset_service.dataset_preview(ds, rows=rows)


@router.get("/{dataset_id}/quality")
def get_quality(dataset_id: str, db: Session = Depends(get_db)):
    ds = _get_dataset_or_404(db, dataset_id)
    _require_ready(ds)
    return json.loads(ds.quality_json)


@router.get("/{dataset_id}/statistics")
def get_statistics(dataset_id: str, db: Session = Depends(get_db)):
    ds = _get_dataset_or_404(db, dataset_id)
    _require_ready(ds)
    return json.loads(ds.stats_json)


@router.get("/{dataset_id}/charts")
def get_charts(dataset_id: str, db: Session = Depends(get_db)):
    ds = _get_dataset_or_404(db, dataset_id)
    _require_ready(ds)
    return json.loads(ds.charts_json)


@router.get("/{dataset_id}/trends")
def get_trends(dataset_id: str, db: Session = Depends(get_db)):
    ds = _get_dataset_or_404(db, dataset_id)
    _require_ready(ds)
    return json.loads(ds.trends_json)


@router.get("/{dataset_id}/anomalies")
def get_anomalies(dataset_id: str, db: Session = Depends(get_db)):
    ds = _get_dataset_or_404(db, dataset_id)
    _require_ready(ds)
    return json.loads(ds.anomalies_json)


@router.get("/{dataset_id}/insights")
def get_insights(dataset_id: str, db: Session = Depends(get_db)):
    ds = _get_dataset_or_404(db, dataset_id)
    _require_ready(ds)
    return json.loads(ds.insights_json)


@router.get("/{dataset_id}/recommendations")
def get_recommendations(dataset_id: str, db: Session = Depends(get_db)):
    ds = _get_dataset_or_404(db, dataset_id)
    _require_ready(ds)
    return json.loads(ds.recommendations_json)


@router.get("/{dataset_id}/schema")
def get_schema(dataset_id: str, db: Session = Depends(get_db)):
    ds = _get_dataset_or_404(db, dataset_id)
    _require_ready(ds)
    return json.loads(ds.schema_json)
