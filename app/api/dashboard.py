from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.config import settings
from app.models.entities import (
    EvidenceFile, IngestionRun, SourceRecord, TimelineEvent,
    IntegrityVerification, Investigation, InvestigationFinding,
    BlindLensReview, AuditEvent
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Computes empirical summary metrics directly from SQLite database."""
    evidence_count = db.query(EvidenceFile).count()
    
    # Source record aggregates
    total_records = db.query(SourceRecord).count()
    parsed_records = db.query(SourceRecord).filter(SourceRecord.parsing_status == "PARSED").count()
    partial_records = db.query(SourceRecord).filter(SourceRecord.parsing_status == "PARTIAL").count()
    ambiguous_records = db.query(SourceRecord).filter(SourceRecord.parsing_status == "AMBIGUOUS").count()
    unparsed_records = db.query(SourceRecord).filter(SourceRecord.parsing_status == "UNPARSED").count()

    timeline_events_count = db.query(TimelineEvent).count()
    
    # Integrity mismatches: count distinct evidence files whose latest verification is MISMATCH
    all_evidence = db.query(EvidenceFile).all()
    mismatches_count = 0
    for ev in all_evidence:
        latest = db.query(IntegrityVerification).filter(
            IntegrityVerification.evidence_id == ev.evidence_id
        ).order_by(desc(IntegrityVerification.verified_at)).first()
        if latest and latest.result in ("MISMATCH", "FILE_NOT_FOUND"):
            mismatches_count += 1

    findings_requiring_review = db.query(InvestigationFinding).filter(
        InvestigationFinding.requires_review == True
    ).count()

    investigations_count = db.query(Investigation).count()
    blindlens_reviews_count = db.query(BlindLensReview).count()

    return {
        "evidence_files_count": evidence_count,
        "total_source_records": total_records,
        "parsed_records": parsed_records,
        "partial_records": partial_records,
        "ambiguous_records": ambiguous_records,
        "unparsed_records": unparsed_records,
        "timeline_events_count": timeline_events_count,
        "evidence_mismatches_count": mismatches_count,
        "findings_requiring_review_count": findings_requiring_review,
        "investigations_count": investigations_count,
        "blindlens_reviews_count": blindlens_reviews_count,
        "environment_label": settings.ENVIRONMENT,
        "is_synthetic_mode": True
    }

@router.get("/activity")
def get_recent_activity(db: Session = Depends(get_db), limit: int = 20):
    """Retrieves chronological recent activity from append-only audit trail."""
    activities = db.query(AuditEvent).order_by(desc(AuditEvent.timestamp)).limit(limit).all()
    return [
        {
            "audit_id": a.audit_id,
            "timestamp": a.timestamp.isoformat(),
            "action": a.action,
            "entity_type": a.entity_type,
            "entity_id": a.entity_id,
            "actor": a.actor,
            "details": a.details_json
        }
        for a in activities
    ]
