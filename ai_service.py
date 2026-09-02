"""
AI service abstraction layer.

InsightForge generates insights and recommendations from the dataset's
ACTUAL computed statistics (quality report, stats, trends, anomalies) --
never invented numbers. Two backends are supported:

  1. "local"     -- deterministic, rule-based Local Analysis Engine.
                     Always available, no API key required. Default.
  2. "anthropic" -- if ANTHROPIC_API_KEY is set and AI_PROVIDER=anthropic,
                     the same computed facts are handed to the model to
                     phrase natural-language insights. The model is
                     instructed to use ONLY the provided facts.

Every insight/recommendation is tagged with its `source` field so the
frontend can clearly label AI-generated vs deterministic content.
"""
from __future__ import annotations

import json
from typing import Any

from .. import config


ENGINE_LABEL = {
    "local": "Local Analysis Engine (deterministic, rule-based)",
    "anthropic": "AI-Generated (Claude)",
}


def _facts_bundle(quality: dict, stats: dict, trends: dict, anomalies: dict) -> dict:
    """Compact, structured facts pulled straight from real computed analysis."""
    return {
        "quality": {
            "total_rows": quality["total_rows"],
            "total_columns": quality["total_columns"],
            "missing_pct_overall": quality["missing_pct_overall"],
            "duplicate_rows": quality["duplicate_rows"],
            "problems": quality["problems"],
        },
        "top_correlations": stats.get("correlations", [])[:5],
        "numeric_columns_sample": {
            k: v for i, (k, v) in enumerate(stats.get("numeric_stats", {}).items()) if i < 5
        },
        "trends": trends.get("trends", [])[:5] if trends.get("available") else [],
        "anomalies": {
            "affected_record_count": anomalies.get("affected_record_count", 0),
            "affected_columns": anomalies.get("affected_columns", []),
            "available": anomalies.get("available", False),
        },
    }


# ---------------------------------------------------------------------------
# Local deterministic engine
# ---------------------------------------------------------------------------

def _local_insights(quality: dict, stats: dict, trends: dict, anomalies: dict) -> list[dict]:
    insights = []

    # Data quality insights
    if quality["duplicate_rows"] > 0:
        insights.append({
            "category": "data_quality",
            "title": "Duplicate records detected",
            "detail": (
                f"{quality['duplicate_rows']} duplicate row(s) were found "
                f"({round(quality['duplicate_rows'] / max(quality['total_rows'],1) * 100, 1)}% of the dataset). "
                "Deduplicating before downstream analysis is recommended."
            ),
        })
    if quality["missing_pct_overall"] > 5:
        insights.append({
            "category": "data_quality",
            "title": "Notable missing data",
            "detail": (
                f"Roughly {quality['missing_pct_overall']}% of all cells are missing across the dataset. "
                "This may bias statistics unless handled explicitly (imputation or exclusion)."
            ),
        })
    if not quality["problems"] and quality["missing_pct_overall"] == 0 and quality["duplicate_rows"] == 0:
        insights.append({
            "category": "data_quality",
            "title": "Clean dataset",
            "detail": "No missing values or duplicate rows were detected -- the dataset passed baseline quality checks.",
        })

    # Correlation insights
    for corr in stats.get("correlations", [])[:3]:
        if corr["strength"] in ("strong", "moderate"):
            direction = "positive" if corr["correlation"] > 0 else "negative"
            insights.append({
                "category": "correlations",
                "title": f"{corr['strength'].capitalize()} {direction} correlation",
                "detail": (
                    f"'{corr['column_a']}' and '{corr['column_b']}' show a {corr['strength']} {direction} "
                    f"correlation (r = {corr['correlation']}). Changes in one tend to move with the other."
                ),
            })

    # Trend insights
    if trends.get("available"):
        for t in trends["trends"][:3]:
            if t["direction"] != "flat":
                insights.append({
                    "category": "trends",
                    "title": f"{t['column']} is {t['direction']}",
                    "detail": t["summary"],
                })

    # Anomaly insights
    if anomalies.get("available") and anomalies.get("affected_record_count", 0) > 0:
        pct = round(anomalies["affected_record_count"] / max(quality["total_rows"], 1) * 100, 2)
        insights.append({
            "category": "outliers",
            "title": "Outliers detected",
            "detail": (
                f"{anomalies['affected_record_count']} record(s) ({pct}% of rows) were flagged as anomalous "
                f"in column(s): {', '.join(anomalies['affected_columns']) or 'n/a'}."
            ),
        })

    # Distribution insights
    for col, s in list(stats.get("numeric_stats", {}).items())[:3]:
        if s["std"] and s["mean"]:
            cv = abs(s["std"] / s["mean"]) if s["mean"] != 0 else None
            if cv is not None and cv > 1:
                insights.append({
                    "category": "distributions",
                    "title": f"High variability in {col}",
                    "detail": (
                        f"'{col}' has high relative variability (std/mean = {round(cv, 2)}), "
                        f"ranging from {s['min']} to {s['max']}."
                    ),
                })

    if not insights:
        insights.append({
            "category": "data_quality",
            "title": "Baseline analysis complete",
            "detail": "The dataset was analyzed but no strong patterns, trends, or anomalies stood out beyond baseline statistics.",
        })

    return insights


def _local_recommendations(quality: dict, stats: dict, trends: dict, anomalies: dict) -> list[dict]:
    recs = []

    if quality["duplicate_rows"] > 0:
        recs.append({
            "recommendation": "Remove duplicate records before further analysis or reporting.",
            "reason": "Duplicates can inflate counts and skew aggregate statistics.",
            "supporting_metric": f"{quality['duplicate_rows']} duplicate rows ({round(quality['duplicate_rows']/max(quality['total_rows'],1)*100,1)}%)",
            "priority": "high" if quality["duplicate_rows"] / max(quality["total_rows"], 1) > 0.05 else "medium",
        })

    high_missing_cols = [c for c in quality["columns"] if c["missing_pct"] > 30]
    if high_missing_cols:
        names = ", ".join(c["name"] for c in high_missing_cols)
        recs.append({
            "recommendation": f"Investigate or impute missing values in: {names}.",
            "reason": "Columns with over 30% missing data reduce the reliability of any analysis that depends on them.",
            "supporting_metric": f"{len(high_missing_cols)} column(s) with >30% missing values",
            "priority": "high",
        })

    for corr in stats.get("correlations", [])[:2]:
        if corr["strength"] == "strong":
            recs.append({
                "recommendation": (
                    f"Consider consolidating or monitoring '{corr['column_a']}' and '{corr['column_b']}' together, "
                    "since they move closely in tandem."
                ),
                "reason": "Strongly correlated variables often carry redundant information or share a common driver.",
                "supporting_metric": f"r = {corr['correlation']}",
                "priority": "medium",
            })

    if anomalies.get("available") and anomalies.get("affected_record_count", 0) > 0:
        pct = anomalies["affected_record_count"] / max(quality["total_rows"], 1) * 100
        recs.append({
            "recommendation": f"Review the {anomalies['affected_record_count']} flagged outlier record(s) for data entry errors or genuine edge cases.",
            "reason": "Unreviewed outliers can distort averages, models, and business decisions built on this data.",
            "supporting_metric": f"{round(pct, 2)}% of records flagged as anomalous",
            "priority": "high" if pct > 5 else "medium",
        })

    if trends.get("available"):
        for t in trends["trends"]:
            if t["direction"] == "decreasing" and t.get("pct_change") and t["pct_change"] < -10:
                recs.append({
                    "recommendation": f"Investigate the sustained decline in '{t['column']}'.",
                    "reason": "A consistent downward trend may indicate a business or operational issue worth addressing.",
                    "supporting_metric": f"{t['pct_change']}% change over the observed period",
                    "priority": "high",
                })
            elif t["direction"] == "increasing" and t.get("pct_change") and t["pct_change"] > 10:
                recs.append({
                    "recommendation": f"Capitalize on the upward trend in '{t['column']}' -- identify and reinforce its drivers.",
                    "reason": "A sustained increase may reflect a successful initiative worth scaling.",
                    "supporting_metric": f"{t['pct_change']}% change over the observed period",
                    "priority": "medium",
                })

    if not recs:
        recs.append({
            "recommendation": "No urgent data issues found -- proceed with standard analysis.",
            "reason": "Data quality, correlation, trend, and anomaly checks did not surface material concerns.",
            "supporting_metric": f"{quality['total_rows']} rows analyzed, {quality['missing_pct_overall']}% missing overall",
            "priority": "low",
        })

    return recs


# ---------------------------------------------------------------------------
# Anthropic-backed engine (optional, only used if configured)
# ---------------------------------------------------------------------------

def _anthropic_insights(facts: dict) -> list[dict] | None:
    if config.AI_PROVIDER != "anthropic" or not config.ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic  # type: ignore

        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        prompt = (
            "You are a data analyst. Using ONLY the JSON facts below (do not invent "
            "numbers not present here), produce 4-6 concise insights as a JSON array "
            "of objects with fields: category (one of data_quality, trends, "
            "correlations, outliers, distributions), title, detail.\n\n"
            f"FACTS:\n{json.dumps(facts)}\n\nRespond with ONLY the JSON array."
        )
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if hasattr(b, "text"))
        text = text.strip().strip("`")
        if text.startswith("json"):
            text = text[4:]
        return json.loads(text)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_insights(quality: dict, stats: dict, trends: dict, anomalies: dict) -> dict:
    facts = _facts_bundle(quality, stats, trends, anomalies)

    if config.AI_PROVIDER == "anthropic" and config.ANTHROPIC_API_KEY:
        ai_result = _anthropic_insights(facts)
        if ai_result:
            return {"engine": "anthropic", "engine_label": ENGINE_LABEL["anthropic"], "insights": ai_result}

    insights = _local_insights(quality, stats, trends, anomalies)
    return {"engine": "local", "engine_label": ENGINE_LABEL["local"], "insights": insights}


def generate_recommendations(quality: dict, stats: dict, trends: dict, anomalies: dict) -> dict:
    recs = _local_recommendations(quality, stats, trends, anomalies)
    return {"engine": "local", "engine_label": ENGINE_LABEL["local"], "recommendations": recs}
