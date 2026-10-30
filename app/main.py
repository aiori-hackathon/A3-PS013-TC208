from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.config import settings
from app.database import init_db
from app.api import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    init_db()
    if settings.IS_VERCEL:
        from app.database import SessionLocal
        from app.models.entities import EvidenceFile
        from app.services.scenario_service import load_scenario
        db = SessionLocal()
        try:
            if db.query(EvidenceFile).count() == 0:
                load_scenario(db, "scenario-01", actor="VercelBoot")
        except Exception:
            pass
        finally:
            db.close()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "TraceLens: Lightweight, explainable incident timeline reconstruction "
        "and digital evidence collection application for small security teams. "
        "AIORI-3 Problem Statement PS-013 (A3-PS013-TC208). Team: Threat Tracers."
    ),
    lifespan=lifespan
)

# CORS configuration restricted to local demonstration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# Mount API routes
app.include_router(api_router)

# Mount static files and templates
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """Serves the single-page application shell."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION,
            "tagline": settings.TAGLINE,
            "team_name": settings.TEAM_NAME,
            "problem_statement": settings.PROBLEM_STATEMENT,
            "environment": settings.ENVIRONMENT
        }
    )
