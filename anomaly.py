from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


def detect_anomalies(df: pd.DataFrame, schema: dict, max_rows: int = 200_000) -> dict:
    numeric_cols = [c for c, k in schema.items() if k == "numeric"]

    if not numeric_cols:
        return {
            "available": False,
            "reason": "No numeric columns available for anomaly detection.",
            "methods": {},
            "affected_columns": [],
            "affected_record_count": 0,
            "sample_anomalies": [],
        }

    work_df = df[numeric_cols].copy()
    if len(work_df) > max_rows:
        work_df = work_df.sample(max_rows, random_state=42)

    methods = {}
    all_anomaly_indices: set[int] = set()
    affected_columns: set[str] = set()

    # --- IQR method (per column) ---
    iqr_flags = pd.DataFrame(index=work_df.index)
    for col in numeric_cols:
        series = work_df[col].dropna()
        if series.empty or series.nunique() <= 1:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        flags = (work_df[col] < lower) | (work_df[col] > upper)
        iqr_flags[col] = flags.fillna(False)
        col_anomalies = int(flags.sum())
        if col_anomalies > 0:
            affected_columns.add(col)
            all_anomaly_indices.update(work_df.index[flags.fillna(False)].tolist())

    methods["iqr"] = {
        "total_flagged": int(iqr_flags.any(axis=1).sum()) if not iqr_flags.empty else 0,
        "per_column": {c: int(iqr_flags[c].sum()) for c in iqr_flags.columns} if not iqr_flags.empty else {},
    }

    # --- Z-score method ---
    z_flags = pd.DataFrame(index=work_df.index)
    for col in numeric_cols:
        series = work_df[col]
        std = series.std()
        if not std or np.isnan(std) or std == 0:
            continue
        z = (series - series.mean()) / std
        flags = z.abs() > 3
        z_flags[col] = flags.fillna(False)
        if flags.fillna(False).sum() > 0:
            affected_columns.add(col)
            all_anomaly_indices.update(work_df.index[flags.fillna(False)].tolist())

    methods["z_score"] = {
        "total_flagged": int(z_flags.any(axis=1).sum()) if not z_flags.empty else 0,
        "per_column": {c: int(z_flags[c].sum()) for c in z_flags.columns} if not z_flags.empty else {},
    }

    # --- Isolation Forest (multivariate) ---
    iso_scores = {}
    clean = work_df.dropna()
    if len(clean) >= 10 and len(numeric_cols) >= 1:
        try:
            model = IsolationForest(n_estimators=150, contamination=0.05, random_state=42)
            preds = model.fit_predict(clean.values)
            scores = model.decision_function(clean.values)
            flagged_idx = clean.index[preds == -1]
            all_anomaly_indices.update(flagged_idx.tolist())
            if len(flagged_idx) > 0:
                affected_columns.update(numeric_cols)
            iso_scores = {int(idx): round(float(score), 4) for idx, score in zip(clean.index, scores)}
            methods["isolation_forest"] = {
                "total_flagged": int((preds == -1).sum()),
                "note": "Multivariate anomaly detection across all numeric columns.",
            }
        except Exception as e:  # pragma: no cover
            methods["isolation_forest"] = {"total_flagged": 0, "note": f"Skipped: {e}"}
    else:
        methods["isolation_forest"] = {
            "total_flagged": 0,
            "note": "Not enough rows for reliable multivariate detection.",
        }

    sample_indices = sorted(all_anomaly_indices)[:25]
    sample_anomalies = []
    for idx in sample_indices:
        row = df.loc[idx, numeric_cols].to_dict()
        row_clean = {k: (round(float(v), 4) if pd.notna(v) else None) for k, v in row.items()}
        sample_anomalies.append({
            "row_index": int(idx),
            "values": row_clean,
            "isolation_score": iso_scores.get(int(idx)),
        })

    return {
        "available": True,
        "reason": None,
        "methods": methods,
        "affected_columns": sorted(affected_columns),
        "affected_record_count": len(all_anomaly_indices),
        "sample_anomalies": sample_anomalies,
    }
