"""
FastAPI entry point — mirrors valtown's app.ts structure.

Mounts all API routes under /api/v1/, serves static front-end files,
and serves the /results page.
"""

import logging
from pathlib import Path

# Load .env before any app code reads os.getenv (single source of truth for local dev)
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from app.routes import init, exchange, callbacks, ping, pong, stream

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ZenPay HCP Demo — Python FastAPI")

# --- Static files (front-end) ---
static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# --- Health check ---
@app.get("/healthz")
async def healthz():
    return {"ok": True}


# --- Root — serve checkout page ---
@app.get("/", response_class=HTMLResponse)
async def root_page():
    index_path = static_dir / "index.html"
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


# --- Results page ---
@app.get("/results", response_class=HTMLResponse)
async def results_page():
    results_path = static_dir / "results.html"
    return HTMLResponse(results_path.read_text(encoding="utf-8"))


# --- API routes (matching valtown's basePath + route structure) ---
app.include_router(init.router, prefix="/api/v1/init")
app.include_router(exchange.router, prefix="/api/v1/exchange")
app.include_router(callbacks.router, prefix="/api/v1/callbacks")
app.include_router(ping.router, prefix="/api/v1/ping")
app.include_router(pong.router, prefix="/api/v1/pong")
app.include_router(stream.router, prefix="/api/v1/stream")
