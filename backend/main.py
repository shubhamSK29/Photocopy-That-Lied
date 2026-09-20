"""FastAPI application entrypoint for Photocopy That Lied."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import config
from backend.api import analyze, health, reports
from backend.storage import database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="Photocopy That Lied",
    description=(
        "AI-assisted image forensics for crop-insurance review. "
        "The system produces screening evidence for a human reviewer; it does not determine fraud."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in config.CORS_ORIGINS if o.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(reports.router)


@app.on_event("startup")
def _startup() -> None:
    database.init_db()
    logging.getLogger("ptl").info("database ready at %s", config.DB_PATH)


@app.get("/")
def root() -> dict:
    return {"name": "Photocopy That Lied", "docs": "/docs", "health": "/api/health"}
