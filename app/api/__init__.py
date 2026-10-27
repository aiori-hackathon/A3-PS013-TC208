from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.dashboard import router as dashboard_router
from app.api.evidence import router as evidence_router
from app.api.ingestion import router as ingestion_router
from app.api.timeline import router as timeline_router
from app.api.clock_skew import router as clock_skew_router
from app.api.investigations import router as investigations_router
from app.api.blindlens import router as blindlens_router
from app.api.mutation import router as mutation_router
from app.api.scenarios import router as scenarios_router
from app.api.evaluation import router as evaluation_router
from app.api.reports import router as reports_router
from app.api.settings import router as settings_router

api_router = APIRouter(prefix="/api")

api_router.include_router(health_router)
api_router.include_router(dashboard_router)
api_router.include_router(evidence_router)
api_router.include_router(ingestion_router)
api_router.include_router(timeline_router)
api_router.include_router(clock_skew_router)
api_router.include_router(investigations_router)
api_router.include_router(blindlens_router)
api_router.include_router(mutation_router)
api_router.include_router(scenarios_router)
api_router.include_router(evaluation_router)
api_router.include_router(reports_router)
api_router.include_router(settings_router)

__all__ = ["api_router"]
