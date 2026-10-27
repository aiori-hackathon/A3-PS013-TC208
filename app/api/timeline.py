from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.timeline_service import query_timeline, get_event_with_source, get_related_events
from app.models.entities import TimelineEvent

router = APIRouter(prefix="/events", tags=["Incident Timeline"])

@router.get("")
def list_timeline_events(
    evidence_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    source_ip: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    http_status: Optional[int] = Query(None),
    parsing_status: Optional[str] = Query(None),
    uncertainty_filter: Optional[str] = Query("all"),  # all, uncertain_only, certain_only
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_desc: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Search, filter, and paginate timeline events.
    Displays UTC timestamps, uncertainty intervals [t-Δ, t+Δ], and order certainty flags.
    """
    total_count, events = query_timeline(
        db=db,
        evidence_id=evidence_id,
        search=search,
        source_ip=source_ip,
        username=username,
        event_type=event_type,
        http_status=http_status,
        parsing_status=parsing_status,
        uncertainty_filter=uncertainty_filter,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
        sort_desc=sort_desc
    )

    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    return {
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "events": [
            {
                "id": e.id,
                "event_id": e.event_id,
                "evidence_id": e.evidence_id,
                "ingestion_id": e.ingestion_id,
                "source_record_id": e.source_record_id,
                "source_line": e.source_line,
                "raw_timestamp": e.raw_timestamp,
                "normalized_utc": e.normalized_utc.isoformat() if e.normalized_utc else None,
                "earliest_utc": e.earliest_utc.isoformat() if e.earliest_utc else None,
                "latest_utc": e.latest_utc.isoformat() if e.latest_utc else None,
                "uncertainty_margin_seconds": e.uncertainty_margin_seconds,
                "time_status": e.time_status,
                "order_uncertain": e.order_uncertain,
                "event_type": e.event_type,
                "hostname": e.hostname,
                "process_name": e.process_name,
                "pid": e.pid,
                "username": e.username,
                "source_ip": e.source_ip,
                "source_port": e.source_port,
                "http_method": e.http_method,
                "http_target": e.http_target,
                "http_status": e.http_status,
                "response_bytes": e.response_bytes,
                "user_agent": e.user_agent,
                "summary": e.summary,
                "full_message": e.full_message,
                "parsing_status": e.parsing_status,
                "warnings": e.warnings
            }
            for e in events
        ]
    }

@router.get("/{event_id}")
def get_single_event(event_id: str, db: Session = Depends(get_db)):
    """Retrieves full details for a single timeline event."""
    event = db.query(TimelineEvent).filter(TimelineEvent.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail=f"Timeline event '{event_id}' not found.")

    return {
        "event_id": event.event_id,
        "evidence_id": event.evidence_id,
        "source_line": event.source_line,
        "raw_timestamp": event.raw_timestamp,
        "normalized_utc": event.normalized_utc.isoformat() if event.normalized_utc else None,
        "earliest_utc": event.earliest_utc.isoformat() if event.earliest_utc else None,
        "latest_utc": event.latest_utc.isoformat() if event.latest_utc else None,
        "uncertainty_margin_seconds": event.uncertainty_margin_seconds,
        "time_status": event.time_status,
        "order_uncertain": event.order_uncertain,
        "event_type": event.event_type,
        "summary": event.summary,
        "full_message": event.full_message,
        "username": event.username,
        "source_ip": event.source_ip,
        "source_port": event.source_port,
        "http_method": event.http_method,
        "http_target": event.http_target,
        "http_status": event.http_status,
        "parsing_status": event.parsing_status,
        "warnings": event.warnings
    }

@router.get("/{event_id}/source")
def get_event_source(event_id: str, db: Session = Depends(get_db)):
    """
    Returns exact raw source log line, line number, extracted fields,
    and evidence file baseline hash, enforcing 100% source traceability.
    """
    data = get_event_with_source(db, event_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Event or source record for '{event_id}' not found.")

    event = data["event"]
    src = data["source_record"]
    evidence = data["evidence_file"]

    return {
        "event_id": event.event_id,
        "evidence_id": event.evidence_id,
        "original_filename": evidence.original_filename if evidence else "unknown",
        "sha256_baseline": evidence.sha256_baseline if evidence else "unknown",
        "source_line": event.source_line,
        "raw_text": src.raw_text if src else "",
        "parsing_status": src.parsing_status if src else event.parsing_status,
        "parser_warnings": src.parser_warnings if src else None,
        "extracted_data": src.extracted_data_json if src else None
    }

@router.get("/{event_id}/related")
def get_event_related(event_id: str, window_seconds: int = Query(60, ge=1, le=3600), db: Session = Depends(get_db)):
    """Retrieves related events within temporal proximity or sharing same IP/username."""
    related = get_related_events(db, event_id, window_seconds=window_seconds)
    return [
        {
            "event_id": r.event_id,
            "evidence_id": r.evidence_id,
            "source_line": r.source_line,
            "normalized_utc": r.normalized_utc.isoformat() if r.normalized_utc else None,
            "order_uncertain": r.order_uncertain,
            "source_ip": r.source_ip,
            "username": r.username,
            "summary": r.summary
        }
        for r in related
    ]
