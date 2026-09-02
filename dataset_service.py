from __future__ import annotations

import json
import uuid
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from .. import config
from ..db_models import Dataset
from . import analysis, anomaly, ai_service


class DatasetProcessingError(Exception):
    pass


def save_upload_file(raw_bytes: bytes, original_filename: str) -> Path:
    if len(raw_bytes) > config.MAX_UPLOAD_BYTES:
        raise DatasetProcessingError(
            f"File exceeds max upload size of {config.MAX_UPLOAD_MB}MB."
        )
    safe_name = f"{uuid.uuid4().hex}_{Path(original_filename).name}"
    dest = config.UPLOAD_DIR / safe_name
    dest.write_bytes(raw_bytes)
    return dest


def load_dataframe(path: Path) -> pd.DataFrame:
    if path.suffix.lower() != ".csv":
        raise DatasetProcessingError("Only .csv files are supported.")
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        raise DatasetProcessingError("The uploaded CSV file is empty.")
    except pd.errors.ParserError as e:
        raise DatasetProcessingError(f"Could not parse CSV file: {e}")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(path, encoding="latin-1")
        except Exception as e:
            raise DatasetProcessingError(f"Could not decode CSV file: {e}")

    if df.shape[0] == 0:
        raise DatasetProcessingError("The uploaded CSV file has no data rows.")
    if df.shape[1] == 0:
        raise DatasetProcessingError("The uploaded CSV file has no columns.")

    # Drop fully-empty unnamed index columns some exports include
    unnamed = [c for c in df.columns if str(c).startswith("Unnamed:")]
    if unnamed and df[unnamed].isna().all().all():
        df = df.drop(columns=unnamed)

    return df


def process_and_store(
    db: Session,
    raw_bytes: bytes,
    original_filename: str,
    is_sample: bool = False,
) -> Dataset:
    file_path = save_upload_file(raw_bytes, original_filename)

    ds = Dataset(
        filename=file_path.name,
        original_filename=original_filename,
        file_path=str(file_path),
        status="processing",
        is_sample=is_sample,
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)

    try:
        df = load_dataframe(file_path)
        schema = analysis.detect_schema(df)
        df = analysis.coerce_types(df, schema)

        quality = analysis.data_quality_report(df, schema)
        stats = analysis.statistical_summary(df, schema)
        charts = analysis.build_charts(df, schema)
        trends = analysis.detect_trends(df, schema)
        anomalies = anomaly.detect_anomalies(df, schema, max_rows=config.MAX_ROWS_FOR_HEAVY_COMPUTE)
        insights = ai_service.generate_insights(quality, stats, trends, anomalies)
        recommendations = ai_service.generate_recommendations(quality, stats, trends, anomalies)

        numeric_count = sum(1 for k in schema.values() if k == "numeric")
        categorical_count = sum(1 for k in schema.values() if k == "categorical")
        datetime_count = sum(1 for k in schema.values() if k == "datetime")

        ds.row_count = quality["total_rows"]
        ds.column_count = quality["total_columns"]
        ds.missing_values = quality["total_missing_values"]
        ds.duplicate_rows = quality["duplicate_rows"]
        ds.numeric_columns = numeric_count
        ds.categorical_columns = categorical_count
        ds.datetime_columns = datetime_count

        ds.schema_json = json.dumps(schema)
        ds.quality_json = json.dumps(quality)
        ds.stats_json = json.dumps(stats)
        ds.charts_json = json.dumps(charts)
        ds.trends_json = json.dumps(trends)
        ds.anomalies_json = json.dumps(anomalies)
        ds.insights_json = json.dumps(insights)
        ds.recommendations_json = json.dumps(recommendations)
        ds.status = "ready"
        ds.error_message = None

    except DatasetProcessingError as e:
        ds.status = "error"
        ds.error_message = str(e)
    except Exception as e:  # noqa: BLE001
        ds.status = "error"
        ds.error_message = f"Unexpected processing error: {e}"

    db.commit()
    db.refresh(ds)
    return ds


def dataset_preview(ds: Dataset, rows: int = 25) -> dict:
    df = pd.read_csv(ds.file_path)
    preview_df = df.head(rows)
    return {
        "columns": list(df.columns),
        "rows": json.loads(preview_df.to_json(orient="records")),
        "total_rows": len(df),
    }
