from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.config import settings

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
def get_health_status(db: Session = Depends(get_db)):
    """Health check endpoint confirming database and storage readiness."""
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    storage_writable = False
    try:
        test_file = settings.STORAGE_DIR / ".health_check"
        test_file.write_text("ok")
        if test_file.exists():
            test_file.unlink()
            storage_writable = True
    except Exception:
        storage_writable = False

    return {
        "status": "ok" if (db_ok and storage_writable) else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database_connected": db_ok,
        "evidence_storage_writable": storage_writable
    }
