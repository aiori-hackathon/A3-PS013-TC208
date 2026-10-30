import os
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config import settings
from app.database import get_db, Base, engine
from app.models.entities import AuditEvent, EvidenceFile

router = APIRouter(prefix="/settings", tags=["Settings & Audit"])

class ResetRequest(BaseModel):
    confirm_reset: bool
    actor: str = "Administrator"

@router.get("")
def get_app_settings():
    """Returns application configuration, standards alignment, and environment parameters."""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "tagline": settings.TAGLINE,
        "team_name": settings.TEAM_NAME,
        "problem_statement": settings.PROBLEM_STATEMENT,
        "environment": settings.ENVIRONMENT,
        "default_timezone": settings.DEFAULT_TIMEZONE,
        "default_uncertainty_margin_seconds": settings.DEFAULT_UNCERTAINTY_MARGIN_SECONDS,
        "default_syslog_year": settings.DEFAULT_SYSLOG_YEAR,
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024),
        "storage_paths": {
            "evidence_dir": str(settings.EVIDENCE_DIR),
            "reports_dir": str(settings.REPORTS_DIR),
            "database_url": settings.DATABASE_URL
        },
        "standards_adherence": [
            "NIST SP 800-92: Guide to Computer Security Log Management",
            "NIST SP 800-86: Guide to Integrating Forensic Techniques into Incident Response",
            "RFC 3227: Guidelines for Evidence Collection and Archiving",
            "RFC 3339: Date and Time on the Internet: Timestamps",
            "NIST FIPS 180-4: Secure Hash Standard (SHA-256)",
            "Sunde and Dror (2019): Cognitive and human factors in digital forensics"
        ]
    }

@router.get("/audit")
def get_audit_trail(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    """Retrieves the system append-only audit trail."""
    query = db.query(AuditEvent).order_by(desc(AuditEvent.timestamp))
    total = query.count()
    events = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "events": [
            {
                "audit_id": e.audit_id,
                "timestamp": e.timestamp.isoformat(),
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "actor": e.actor,
                "details": e.details_json
            }
            for e in events
        ]
    }

@router.post("/reset-demo", status_code=status.HTTP_200_OK)
def reset_demonstration_database(payload: ResetRequest, db: Session = Depends(get_db)):
    """
    Safely resets the demonstration SQLite database tables and removes collected test files.
    Requires explicit confirmation flag.
    """
    if not payload.confirm_reset:
        raise HTTPException(status_code=400, detail="Confirmation flag 'confirm_reset' must be true to execute demonstration reset.")

    # Drop and recreate all tables safely
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Clean storage directories
    for f in settings.EVIDENCE_DIR.glob("*"):
        if f.is_file() and not f.name.startswith("."):
            try:
                f.unlink()
            except Exception:
                pass

    for f in settings.REPORTS_DIR.glob("*"):
        if f.is_file() and not f.name.startswith("."):
            try:
                f.unlink()
            except Exception:
                pass

    return {
        "status": "RESET_SUCCESSFUL",
        "message": "Demonstration database and managed storage have been reset to clean initial state."
    }
