"""
Core deterministic data-analysis engine for InsightForge.
Everything here operates on the ACTUAL uploaded dataset — no fabricated
values. If a computation isn't supported by the data (e.g. no numeric
columns, no dates), the relevant section is returned empty/flagged
rather than invented.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message="Could not infer format")


# ---------------------------------------------------------------------------
# Schema detection
# ---------------------------------------------------------------------------

def detect_schema(df: pd.DataFrame) -> dict:
    """Classify each column as numeric, categorical, or datetime."""
    schema = {}
    for col in df.columns:
        series = df[col]

        if pd.api.types.is_datetime64_any_dtype(series):
            schema[col] = "datetime"
            continue

        # Try datetime detection on any non-numeric column (string/object/etc.),
        # but skip plain integer-like strings (e.g. IDs) which dateutil can
        # otherwise misparse as dates.
        if not pd.api.types.is_numeric_dtype(series):
            sample = series.dropna().astype(str).head(50)
            looks_numeric = sample.str.fullmatch(r"-?\d+(\.\d+)?").mean() > 0.9 if len(sample) else False
            if not looks_numeric:
                parsed = pd.to_datetime(series, errors="coerce")
                non_null = series.notna().sum()
                parsed_ok = parsed.notna().sum()
                if non_null > 0 and parsed_ok / max(non_null, 1) > 0.85:
                    schema[col] = "datetime"
                    continue

        if pd.api.types.is_numeric_dtype(series):
            schema[col] = "numeric"
        else:
            schema[col] = "categorical"
    return schema


def coerce_types(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    df = df.copy()
    for col, kind in schema.items():
        if kind == "datetime":
            df[col] = pd.to_datetime(df[col], errors="coerce")
        elif kind == "numeric":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# Data quality
# ---------------------------------------------------------------------------

def data_quality_report(df: pd.DataFrame, schema: dict) -> dict:
    total_rows = len(df)
    total_cols = len(df.columns)
    missing_by_col = df.isna().sum()
    total_missing = int(missing_by_col.sum())
    duplicate_rows = int(df.duplicated().sum())

    columns = []
    for col in df.columns:
        n_missing = int(missing_by_col[col])
        pct_missing = round((n_missing / total_rows) * 100, 2) if total_rows else 0.0
        columns.append({
            "name": col,
            "dtype": schema.get(col, "categorical"),
            "missing_count": n_missing,
            "missing_pct": pct_missing,
            "unique_values": int(df[col].nunique(dropna=True)),
        })

    problems = []
    if duplicate_rows > 0:
        problems.append(f"{duplicate_rows} duplicate row(s) detected.")
    high_missing = [c["name"] for c in columns if c["missing_pct"] > 30]
    if high_missing:
        problems.append(
            f"High missing-value rate (>30%) in: {', '.join(high_missing)}."
        )
    constant_cols = [c["name"] for c in columns if c["unique_values"] <= 1]
    if constant_cols:
        problems.append(f"Constant / single-value column(s): {', '.join(constant_cols)}.")

    return {
        "total_rows": total_rows,
        "total_columns": total_cols,
        "total_missing_values": total_missing,
        "missing_pct_overall": round((total_missing / (total_rows * total_cols)) * 100, 2) if total_rows and total_cols else 0.0,
        "duplicate_rows": duplicate_rows,
        "columns": columns,
        "problems": problems,
    }


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def statistical_summary(df: pd.DataFrame, schema: dict) -> dict:
    numeric_cols = [c for c, k in schema.items() if k == "numeric"]
    stats = {}
    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty:
            continue
        q1, q2, q3 = series.quantile([0.25, 0.5, 0.75])
        stats[col] = {
            "mean": round(float(series.mean()), 4),
            "median": round(float(q2), 4),
            "min": round(float(series.min()), 4),
            "max": round(float(series.max()), 4),
            "std": round(float(series.std()) if len(series) > 1 else 0.0, 4),
            "q1": round(float(q1), 4),
            "q3": round(float(q3), 4),
            "count": int(series.count()),
        }

    correlations = []
    if len(numeric_cols) >= 2:
        corr_df = df[numeric_cols].corr(numeric_only=True)
        seen = set()
        for a in numeric_cols:
            for b in numeric_cols:
                if a == b or (b, a) in seen:
                    continue
                seen.add((a, b))
                val = corr_df.loc[a, b]
                if pd.isna(val):
                    continue
                correlations.append({
                    "column_a": a,
                    "column_b": b,
                    "correlation": round(float(val), 4),
                    "strength": _corr_strength(val),
                })
        correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)

    categorical_cols = [c for c, k in schema.items() if k == "categorical"]
    categorical_summary = {}
    for col in categorical_cols:
        vc = df[col].value_counts(dropna=True).head(10)
        categorical_summary[col] = [
            {"value": str(k), "count": int(v)} for k, v in vc.items()
        ]

    return {
        "numeric_stats": stats,
        "correlations": correlations[:15],
        "categorical_summary": categorical_summary,
    }


def _corr_strength(v: float) -> str:
    av = abs(v)
    if av >= 0.7:
        return "strong"
    if av >= 0.4:
        return "moderate"
    if av >= 0.2:
        return "weak"
    return "negligible"


# ---------------------------------------------------------------------------
# Charts (data payloads only -- frontend renders with Recharts)
# ---------------------------------------------------------------------------

def build_charts(df: pd.DataFrame, schema: dict) -> dict:
    numeric_cols = [c for c, k in schema.items() if k == "numeric"]
    categorical_cols = [c for c, k in schema.items() if k == "categorical"]
    datetime_cols = [c for c, k in schema.items() if k == "datetime"]

    charts = {"bar": None, "pie": None, "histogram": None, "scatter": None, "line": None}

    # Bar chart: first categorical column's top categories vs count
    if categorical_cols:
        col = categorical_cols[0]
        vc = df[col].value_counts(dropna=True).head(10)
        charts["bar"] = {
            "column": col,
            "data": [{"name": str(k), "value": int(v)} for k, v in vc.items()],
        }

    # Pie/donut chart: second categorical column (or first if only one), top 6
    if categorical_cols:
        col = categorical_cols[1] if len(categorical_cols) > 1 else categorical_cols[0]
        vc = df[col].value_counts(dropna=True).head(6)
        charts["pie"] = {
            "column": col,
            "data": [{"name": str(k), "value": int(v)} for k, v in vc.items()],
        }

    # Histogram: first numeric column binned
    if numeric_cols:
        col = numeric_cols[0]
        series = df[col].dropna()
        if not series.empty:
            counts, bin_edges = np.histogram(series, bins=min(10, max(3, series.nunique())))
            charts["histogram"] = {
                "column": col,
                "data": [
                    {
                        "bin": f"{round(bin_edges[i], 2)}\u2013{round(bin_edges[i + 1], 2)}",
                        "count": int(counts[i]),
                    }
                    for i in range(len(counts))
                ],
            }

    # Scatter: first two numeric columns
    if len(numeric_cols) >= 2:
        x_col, y_col = numeric_cols[0], numeric_cols[1]
        sample = df[[x_col, y_col]].dropna()
        if len(sample) > 500:
            sample = sample.sample(500, random_state=42)
        charts["scatter"] = {
            "x_column": x_col,
            "y_column": y_col,
            "data": [
                {"x": float(r[x_col]), "y": float(r[y_col])}
                for _, r in sample.iterrows()
            ],
        }

    # Line chart: datetime column vs first numeric column (also feeds trend detection)
    if datetime_cols and numeric_cols:
        d_col, n_col = datetime_cols[0], numeric_cols[0]
        ts = df[[d_col, n_col]].dropna().sort_values(d_col)
        if not ts.empty:
            grouped = ts.groupby(pd.Grouper(key=d_col, freq=_infer_freq(ts[d_col])))[n_col].mean().dropna()
            charts["line"] = {
                "x_column": d_col,
                "y_column": n_col,
                "data": [
                    {"date": idx.strftime("%Y-%m-%d"), "value": round(float(val), 4)}
                    for idx, val in grouped.items()
                ],
            }
    elif numeric_cols:
        # No dates: show value progression by row index as a fallback line chart
        col = numeric_cols[0]
        series = df[col].dropna().reset_index(drop=True)
        step = max(1, len(series) // 200)
        charts["line"] = {
            "x_column": "row_index",
            "y_column": col,
            "data": [
                {"date": str(i), "value": round(float(series[i]), 4)}
                for i in range(0, len(series), step)
            ],
        }

    return charts


def _infer_freq(dt_series: pd.Series) -> str:
    span_days = (dt_series.max() - dt_series.min()).days
    if span_days <= 3:
        return "H"
    if span_days <= 120:
        return "D"
    if span_days <= 900:
        return "W"
    return "MS"


# ---------------------------------------------------------------------------
# Trend detection
# ---------------------------------------------------------------------------

def detect_trends(df: pd.DataFrame, schema: dict) -> dict:
    datetime_cols = [c for c, k in schema.items() if k == "datetime"]
    numeric_cols = [c for c, k in schema.items() if k == "numeric"]

    if not datetime_cols or not numeric_cols:
        return {"available": False, "reason": "No datetime + numeric column pair found.", "trends": []}

    d_col = datetime_cols[0]
    trends = []
    for n_col in numeric_cols[:5]:
        ts = df[[d_col, n_col]].dropna().sort_values(d_col)
        if len(ts) < 4:
            continue
        grouped = ts.groupby(pd.Grouper(key=d_col, freq=_infer_freq(ts[d_col])))[n_col].mean().dropna()
        if len(grouped) < 3:
            continue

        x = np.arange(len(grouped))
        y = grouped.values
        slope, intercept = np.polyfit(x, y, 1)
        first_val, last_val = float(y[0]), float(y[-1])
        pct_change = ((last_val - first_val) / abs(first_val) * 100) if first_val != 0 else None

        direction = "flat"
        if slope > 0 and abs(pct_change or 0) > 1:
            direction = "increasing"
        elif slope < 0 and abs(pct_change or 0) > 1:
            direction = "decreasing"

        trends.append({
            "column": n_col,
            "direction": direction,
            "slope": round(float(slope), 6),
            "start_value": round(first_val, 4),
            "end_value": round(last_val, 4),
            "pct_change": round(pct_change, 2) if pct_change is not None else None,
            "periods": len(grouped),
            "summary": _trend_summary(n_col, direction, pct_change),
        })

    return {"available": bool(trends), "reason": None if trends else "Not enough time-ordered data points.", "trends": trends}


def _trend_summary(col: str, direction: str, pct_change) -> str:
    if direction == "flat" or pct_change is None:
        return f"{col} remained relatively stable over the observed period."
    verb = "increased" if direction == "increasing" else "decreased"
    return f"{col} {verb} by {abs(pct_change):.1f}% from the start to the end of the observed period."
