"""Entities pipeline webapp — FastAPI backend."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers import entities, pipeline, proposals


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure detect dir exists
    from .config import DETECT_DIR
    DETECT_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown: nothing to clean up


app = FastAPI(title="Entities Pipeline", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(proposals.router, prefix="/api/proposals", tags=["proposals"])
app.include_router(entities.router, prefix="/api/entities", tags=["entities"])

# In production, serve built frontend
dist = Path(__file__).parent / ".." / "frontend" / "dist"
if dist.is_dir():
    app.mount("/", StaticFiles(directory=str(dist), html=True), name="frontend")
