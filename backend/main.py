"""FastAPI application entrypoint for Photocopy That Lied."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

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
    allow_origins=["*"],  # Allow all origins temporarily for debugging
    allow_credentials=False,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(reports.router)

# Serve React frontend if production build exists
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/app", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    logging.getLogger("ptl").info("React frontend mounted at /app")

    # Redirect root to /app when frontend is available
    @app.get("/")
    def redirect_to_frontend() -> Response:
        return RedirectResponse(url="/app")
else:
    # Root route when no frontend is available
    @app.get("/")
    def root() -> dict:
        return {"name": "Photocopy That Lied", "docs": "/docs", "health": "/api/health"}
    logging.getLogger("ptl").info("React frontend not found, serving API only")


@app.on_event("startup")
def _startup() -> None:
    database.init_db()
    logging.getLogger("ptl").info("database ready at %s", config.DB_PATH)



