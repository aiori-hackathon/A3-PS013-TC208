from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc

from app.models.entities import TimelineEvent, SourceRecord, EvidenceFile

def query_timeline(
    db: Session,
    evidence_id: Optional[str] = None,
    search: Optional[str] = None,
    source_ip: Optional[str] = None,
    username: Optional[str] = None,
    event_type: Optional[str] = None,
    http_status: Optional[int] = None,
    parsing_status: Optional[str] = None,
    uncertainty_filter: Optional[str] = None,  # "all", "uncertain_only", "certain_only"
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 50,
    sort_desc: bool = False
) -> Tuple[int, List[TimelineEvent]]:
    """
    Query, filter, and paginate timeline events with multi-parameter criteria.
    """
    query = db.query(TimelineEvent)

    if evidence_id:
        query = query.filter(TimelineEvent.evidence_id == evidence_id)

    if source_ip:
        query = query.filter(TimelineEvent.source_ip == source_ip)

    if username:
        query = query.filter(TimelineEvent.username.ilike(f"%{username}%"))

    if event_type:
        query = query.filter(TimelineEvent.event_type == event_type)

    if http_status:
        query = query.filter(TimelineEvent.http_status == http_status)

    if parsing_status:
        query = query.filter(TimelineEvent.parsing_status == parsing_status)

    if uncertainty_filter == "uncertain_only":
        query = query.filter(TimelineEvent.order_uncertain == True)
    elif uncertainty_filter == "certain_only":
        query = query.filter(TimelineEvent.order_uncertain == False)

    if start_time:
        query = query.filter(TimelineEvent.normalized_utc >= start_time)

    if end_time:
        query = query.filter(TimelineEvent.normalized_utc <= end_time)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                TimelineEvent.summary.ilike(search_pattern),
                TimelineEvent.full_message.ilike(search_pattern),
                TimelineEvent.http_target.ilike(search_pattern),
                TimelineEvent.source_ip.ilike(search_pattern),
                TimelineEvent.username.ilike(search_pattern)
            )
        )

    total_count = query.count()

    # Sort primarily by normalized_utc. For events with null normalized_utc, place them at the end.
    if sort_desc:
        query = query.order_by(TimelineEvent.normalized_utc.desc().nullslast(), TimelineEvent.id.desc())
    else:
        query = query.order_by(TimelineEvent.normalized_utc.asc().nullsfirst(), TimelineEvent.id.asc())

    offset = (page - 1) * page_size
    events = query.offset(offset).limit(page_size).all()

    return total_count, events

def get_event_with_source(db: Session, event_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns the event details joined with its original raw source record and evidence metadata.
    Enforces 100% source traceability.
    """
    event = db.query(TimelineEvent).filter(TimelineEvent.event_id == event_id).first()
    if not event:
        return None

    source = db.query(SourceRecord).filter(SourceRecord.id == event.source_record_id).first()
    evidence = db.query(EvidenceFile).filter(EvidenceFile.evidence_id == event.evidence_id).first()

    return {
        "event": event,
        "source_record": source,
        "evidence_file": evidence
    }

def get_related_events(db: Session, event_id: str, window_seconds: int = 60) -> List[TimelineEvent]:
    """Finds related events based on shared IP, username, or close temporal proximity."""
    target = db.query(TimelineEvent).filter(TimelineEvent.event_id == event_id).first()
    if not target or not target.normalized_utc:
        return []

    t_start = target.normalized_utc - timedelta(seconds=window_seconds)
    t_end = target.normalized_utc + timedelta(seconds=window_seconds)

    criteria = []
    if target.source_ip:
        criteria.append(TimelineEvent.source_ip == target.source_ip)
    if target.username:
        criteria.append(TimelineEvent.username == target.username)
    criteria.append(
        and_(
            TimelineEvent.normalized_utc >= t_start,
            TimelineEvent.normalized_utc <= t_end
        )
    )

    related = db.query(TimelineEvent).filter(
        TimelineEvent.event_id != event_id,
        or_(*criteria)
    ).order_by(TimelineEvent.normalized_utc.asc()).limit(30).all()

    return related
