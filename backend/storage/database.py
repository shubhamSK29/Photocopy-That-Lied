"""SQLite persistence for analysis records."""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

from backend import config

_LOCK = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    analysis_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    filename TEXT,
    sha256 TEXT,
    file_size INTEGER,
    format TEXT,
    width INTEGER,
    height INTEGER,
    metadata TEXT,
    manipulation_score REAL,
    coverage_score REAL,
    risk_band TEXT,
    copy_move_result TEXT,
    local_anomaly_result TEXT,
    compression_result TEXT,
    timestamp_result TEXT,
    natural_processing_result TEXT,
    spatial_agreement TEXT,
    heatmap_path TEXT,
    report_path TEXT,
    model_version TEXT,
    dataset_version TEXT,
    warnings TEXT,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses (created_at DESC);
"""

_JSON_COLUMNS = {
    "metadata",
    "copy_move_result",
    "local_anomaly_result",
    "compression_result",
    "timestamp_result",
    "natural_processing_result",
    "spatial_agreement",
    "warnings",
    "payload",
}


def _connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = Path(db_path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    with _LOCK, _connect(db_path) as conn:
        conn.executescript(_SCHEMA)


def _dump(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float)):
        return value
    return json.dumps(value)


def save_analysis(record: dict, db_path: Optional[Path] = None) -> None:
    columns = [
        "analysis_id", "created_at", "filename", "sha256", "file_size", "format",
        "width", "height", "metadata", "manipulation_score", "coverage_score",
        "risk_band", "copy_move_result", "local_anomaly_result", "compression_result",
        "timestamp_result", "natural_processing_result", "spatial_agreement",
        "heatmap_path", "report_path", "model_version", "dataset_version",
        "warnings", "payload",
    ]
    values = []
    for col in columns:
        raw = record.get(col)
        values.append(json.dumps(raw) if col in _JSON_COLUMNS else _dump(raw))
    placeholders = ",".join("?" * len(columns))
    with _LOCK, _connect(db_path) as conn:
        # Keeps direct/library use and test clients safe when the FastAPI
        # lifespan hook has not run yet.
        conn.executescript(_SCHEMA)
        conn.execute(
            f"INSERT OR REPLACE INTO analyses ({','.join(columns)}) VALUES ({placeholders})",
            values,
        )


def get_analysis(analysis_id: str, db_path: Optional[Path] = None) -> Optional[dict]:
    with _LOCK, _connect(db_path) as conn:
        conn.executescript(_SCHEMA)
        row = conn.execute(
            "SELECT payload FROM analyses WHERE analysis_id = ?", (analysis_id,)
        ).fetchone()
    return json.loads(row["payload"]) if row else None


def list_analyses(limit: int = 50, db_path: Optional[Path] = None) -> list[dict]:
    with _LOCK, _connect(db_path) as conn:
        conn.executescript(_SCHEMA)
        rows = conn.execute(
            "SELECT analysis_id, created_at, filename, manipulation_score, coverage_score,"
            " risk_band, sha256 FROM analyses ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
