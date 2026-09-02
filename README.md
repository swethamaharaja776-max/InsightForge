# InsightForge

**AI-Powered Data Intelligence** — *Forge Insights. Drive Decisions.*

InsightForge converts raw CSV datasets into understandable analytics: statistical
summaries, visualizations, trend detection, anomaly detection, grounded AI insights,
and actionable recommendations — all computed from the data you actually upload.

---

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Solution](#solution)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Running Locally](#running-locally)
- [API Documentation](#api-documentation)
- [Usage](#usage)
- [Sample Data](#sample-data)
- [Deployment](#deployment)
- [Screenshots](#screenshots)
- [Future Enhancements](#future-enhancements)
- [License](#license)

---

## Overview

InsightForge is a full-stack data-intelligence platform built as a portfolio /
hackathon project. Upload a CSV and it runs through a complete pipeline —
validation, preview, statistical analysis, visualization, trend detection,
anomaly detection, AI-assisted insight generation, and recommendation
generation — then lets you save, revisit, and export the results.

## Problem Statement

Non-technical users and time-constrained analysts often have a CSV full of
useful information but no fast way to understand it: is the data clean? What
does it actually say? Are there outliers worth investigating? What should we
do about it? Spreadsheet tools require manual work; full BI platforms are
heavyweight. InsightForge sits in between: point it at a CSV and get a
grounded, explainable analysis in seconds.

## Solution

InsightForge pairs a Python analysis engine (Pandas/NumPy/Scikit-learn) with a
FastAPI backend and a React/TypeScript dashboard. Every number shown in the UI
is computed directly from the uploaded dataset — nothing is fabricated. Where
the AI/insights layer speaks in natural language, it is explicitly grounded in
the same computed facts and clearly labeled by which engine produced it (a
deterministic **Local Analysis Engine** by default, or an LLM if configured).

## Features

- **CSV Upload** — drag-and-drop or browse, with file type/size validation,
  row/column/type detection, missing-value and duplicate-row detection.
- **Data Quality Report** — missing values, duplicates, dtypes, unique
  values, missing-value percentage, and flagged problems.
- **Analytics Dashboard** — dynamic KPI cards and five real chart types (bar,
  line, pie/donut, histogram, scatter) rendered from the actual dataset.
- **Statistical Analysis** — mean, median, min, max, std dev, quartiles for
  every numeric column, plus pairwise correlations with strength labels.
- **Trend Detection** — if a datetime column exists, detects increasing /
  decreasing / flat trends per numeric column with % change.
- **Anomaly Detection** — IQR, Z-score, and Isolation Forest, with affected
  columns/records and sample flagged rows.
- **AI / Data Insights** — insights grouped by category (data quality,
  trends, correlations, outliers, distributions), generated only from
  computed statistics.
- **Recommendations** — each with a recommendation, reason, supporting
  metric, and priority (high/medium/low).
- **Analysis History** — searchable, filterable list of past uploads; open or
  delete any analysis.
- **Report Export** — download a self-contained, styled HTML report
  (dataset summary, quality, statistics, trends, anomalies, insights,
  recommendations) — printable to PDF from any browser.

## Architecture

```
┌─────────────────┐      REST/JSON       ┌──────────────────────┐
│  React + TS SPA  │ ───────────────────▶ │      FastAPI          │
│  (Vite, Tailwind,│ ◀─────────────────── │  (Pandas / NumPy /     │
│   Recharts)      │                      │   Scikit-learn)        │
└─────────────────┘                      └──────────┬────────────┘
                                                      │
                                          ┌───────────▼────────────┐
                                          │   SQLite (SQLAlchemy)   │
                                          │  datasets + cached      │
                                          │  analysis results (JSON)│
                                          └─────────────────────────┘
```

Analysis is computed **once**, at upload time, and cached as JSON on the
`Dataset` row — subsequent page loads (statistics, charts, insights, etc.)
are simple reads, not recomputation.

## Tech Stack

**Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Recharts, Lucide React, React Router, Axios

**Backend:** Python, FastAPI, Pandas, NumPy, Scikit-learn, Pydantic

**Database:** SQLite, SQLAlchemy

**AI:** Pluggable AI service abstraction — deterministic Local Analysis Engine
by default; optional Anthropic LLM integration via environment variable, using
only the same computed facts (no free-form fabrication).

## Project Structure

```
insightforge/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app entrypoint
│   │   ├── config.py              # env-driven configuration
│   │   ├── database.py            # SQLAlchemy engine/session
│   │   ├── db_models.py           # Dataset ORM model
│   │   ├── schemas.py             # Pydantic response models
│   │   ├── routers/
│   │   │   ├── datasets.py        # upload, statistics, charts, insights...
│   │   │   ├── history.py         # list/search/delete history
│   │   │   └── reports.py         # JSON + downloadable HTML report
│   │   ├── services/
│   │   │   ├── analysis.py        # schema detection, quality, stats, charts, trends
│   │   │   ├── anomaly.py         # IQR / Z-score / Isolation Forest
│   │   │   ├── ai_service.py      # local engine + optional LLM abstraction
│   │   │   └── dataset_service.py # upload → process → persist pipeline
│   │   └── storage/                # uploaded files + sqlite db (gitignored)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/                 # Landing, Dashboard, Upload, Preview,
│   │   │                          # Analytics, Insights, Recommendations,
│   │   │                          # History, Reports, Settings
│   │   ├── components/            # Layout, DatasetSelector, Common (Card, KPI...)
│   │   ├── context/                # DatasetContext (selected dataset state)
│   │   ├── api/                    # typed Axios client
│   │   └── types/                  # shared TypeScript types
│   ├── package.json
│   └── .env.example
├── sample_data/                    # synthetic CSVs for testing
├── README.md
├── .gitignore
└── LICENSE
```

## Installation

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm

### 1. Clone and enter the project

```bash
git clone https://github.com/<your-username>/insightforge.git
cd insightforge
```

### 2. Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # edit if needed
```

### 3. Frontend setup

```bash
cd ../frontend
npm install
cp .env.example .env             # optional for local dev
```

## Environment Variables

**Backend** (`backend/.env`, see `backend/.env.example`):

| Variable | Default | Description |
|---|---|---|
| `AI_PROVIDER` | `local` | `local` (deterministic engine) or `anthropic` |
| `ANTHROPIC_API_KEY` | *(empty)* | Required only if `AI_PROVIDER=anthropic` |
| `DATABASE_URL` | `sqlite:///./app/storage/db/insightforge.db` | SQLAlchemy connection string |
| `MAX_UPLOAD_MB` | `25` | Max CSV upload size |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed origins |

**Frontend** (`frontend/.env`, see `frontend/.env.example`):

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | *(uses Vite proxy)* | Only needed if backend is on a different origin in production |

If no AI API key is configured, InsightForge automatically and transparently
uses its built-in **Local Analysis Engine** — this is the default and fully
functional path; no external key is required to use the app.

## Running Locally

**Terminal 1 — backend:**

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Backend runs at `http://localhost:8000` (interactive API docs at `/docs`).

**Terminal 2 — frontend:**

```bash
cd frontend
npm run dev
```

Frontend runs at `http://localhost:5173` and proxies `/api` requests to the
backend automatically (see `vite.config.ts`).

Open `http://localhost:5173`, click **Upload a Dataset**, and try one of the
CSVs in `sample_data/`.

## API Documentation

Interactive Swagger UI is available at `http://localhost:8000/docs` once the
backend is running. Key endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/datasets/upload` | Upload a CSV, run the full analysis pipeline |
| `GET`  | `/api/datasets` | List all datasets |
| `GET`  | `/api/datasets/{id}` | Dataset summary/status |
| `GET`  | `/api/datasets/{id}/preview` | First N rows |
| `GET`  | `/api/datasets/{id}/quality` | Data quality report |
| `GET`  | `/api/datasets/{id}/statistics` | Numeric stats + correlations |
| `GET`  | `/api/datasets/{id}/charts` | Bar/line/pie/histogram/scatter data |
| `GET`  | `/api/datasets/{id}/trends` | Time-series trend detection |
| `GET`  | `/api/datasets/{id}/anomalies` | IQR/Z-score/Isolation Forest results |
| `GET`  | `/api/datasets/{id}/insights` | AI/local-engine insights |
| `GET`  | `/api/datasets/{id}/recommendations` | Prioritized recommendations |
| `GET`  | `/api/history` | Search/filter analysis history |
| `DELETE` | `/api/history/{id}` | Delete an analysis |
| `GET`  | `/api/reports/{id}` | Full report as JSON |
| `GET`  | `/api/reports/{id}/download` | Downloadable HTML report |

All endpoints return structured JSON error messages (`{"detail": "..."}`) with
appropriate HTTP status codes (400, 404, 409, 422, 500) for invalid CSVs,
missing datasets, unready analyses, and unexpected errors.

## Usage

1. **Upload** a CSV on the Upload page (or drag-and-drop).
2. InsightForge validates the file, infers column types, and runs the full
   analysis pipeline — you're redirected to the **Dashboard** automatically.
3. Explore **Analytics** for full statistics, correlations, histograms,
   scatter plots, trends, and anomaly detail.
4. Check **AI Insights** and **Recommendations** for grounded, prioritized
   takeaways.
5. Revisit past work in **History**, or delete analyses you no longer need.
6. Export a shareable report from **Reports**.

## Sample Data

`sample_data/` contains three **synthetic, clearly-labeled** CSVs for testing:

- `ecommerce_sales.csv` — daily sales with category/region breakdowns, a
  revenue trend, injected anomalies, missing values, and duplicate rows.
- `employee_hr_data.csv` — HR dataset with department/salary correlations
  and injected salary outliers.
- `website_analytics.csv` — daily traffic/conversion time series with
  injected traffic spikes.

All three exercise every feature of the pipeline (quality issues, trends,
anomalies, correlations).

## Deployment

**Backend:** any ASGI-capable host (Render, Railway, Fly.io, a VM with
`uvicorn`/`gunicorn`). Set the environment variables above; ensure the
`backend/app/storage/` directory is on persistent (not ephemeral) storage, or
point `DATABASE_URL` at a managed Postgres/SQLite volume.

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Frontend:** build a static bundle and deploy to any static host (Vercel,
Netlify, Cloudflare Pages, S3+CloudFront):

```bash
npm run build   # outputs to frontend/dist
```

Set `VITE_API_BASE_URL` to your deployed backend's URL before building if
frontend and backend are on different origins, and add that frontend origin
to the backend's `CORS_ORIGINS`.

## Screenshots

*(Add screenshots of the Dashboard, Analytics, and Insights pages here after
running the app locally — e.g. `docs/screenshots/dashboard.png`.)*

## Future Enhancements

- Multi-file / multi-sheet Excel support
- User accounts and per-user dataset isolation
- Scheduled re-analysis for periodically-updated datasets
- PDF export in addition to HTML
- Configurable anomaly-detection sensitivity from the UI
- Column-level custom chart builder

## License

Released under the [MIT License](./LICENSE).
