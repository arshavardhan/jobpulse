import os
import uvicorn
import threading
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.database.db import init_db, SessionLocal
from src.database.models import JobModel
from src.agents.scout import ScoutAgent
from src.api.routes import api_router

logger = logging.getLogger(__name__)

def _background_initial_hunt():
    """Background scout run to populate live jobs without blocking server startup."""
    try:
        logger.info("[Startup] Initiating non-blocking background live job discovery across all role domains...")
        scout = ScoutAgent()
        scout.execute_hunt(limit_per_source=25)
        logger.info("[Startup] Non-blocking background discovery finished.")
    except Exception as e:
        logger.error(f"[Startup] Background live discovery error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables and trigger non-blocking live hunt if DB has low volume."""
    init_db()
    db = SessionLocal()
    try:
        active_count = db.query(JobModel).filter(JobModel.status == "ACTIVE").count()
        if active_count < 150:
            # Non-blocking: starts FastAPI immediately while scout runs in background
            thread = threading.Thread(target=_background_initial_hunt, daemon=True)
            thread.start()
    finally:
        db.close()
    yield


# Initialize FastAPI App
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Production-grade Agentic AI Job Automation, Web Scraping & Market Analytics Platform.",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router)

# Mount Static Files
frontend_dir = Path(__file__).parent / "src" / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

@app.get("/", response_class=FileResponse)
def serve_index():
    return FileResponse(frontend_dir / "index.html")

@app.get("/favicon.ico", include_in_schema=False)
def serve_favicon():
    from fastapi.responses import Response
    return Response(status_code=204)

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
