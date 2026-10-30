import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.entities import Investigation, InvestigationFinding, AuditEvent

def create_investigation(
    db: Session,
    title: str,
    description: Optional[str] = None,
    lead_investigator: str = "Analyst"
) -> Investigation:
    investigation_id = f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    inv = Investigation(
        investigation_id=investigation_id,
        title=title.strip(),
        description=description,
        status="OPEN",
        lead_investigator=lead_investigator,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(inv)
    audit = AuditEvent(
        audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
        timestamp=datetime.now(timezone.utc),
        action="INVESTIGATION_CREATED",
        entity_type="INVESTIGATION",
        entity_id=investigation_id,
        actor=lead_investigator,
        details_json=json.dumps({"title": title})
    )
    db.add(audit)
    db.commit()
    db.refresh(inv)
    return inv

def get_investigation(db: Session, investigation_id: str) -> Optional[Investigation]:
    return db.query(Investigation).filter(Investigation.investigation_id == investigation_id).first()

def list_investigations(db: Session) -> List[Investigation]:
    return db.query(Investigation).order_by(desc(Investigation.created_at)).all()

def create_finding(
    db: Session,
    investigation_id: str,
    title: str,
    description: Optional[str] = None,
    status: str = "OPEN",
    rationale: Optional[str] = None,
    supporting_events: Optional[List[str]] = None,
    contradictory_events: Optional[List[str]] = None,
    unresolved_questions: Optional[str] = None,
    actor: str = "Analyst"
) -> InvestigationFinding:
    inv = get_investigation(db, investigation_id)
    if not inv:
        raise ValueError(f"Investigation '{investigation_id}' does not exist.")

    finding_id = f"FND-{uuid.uuid4().hex[:8].upper()}"
    finding = InvestigationFinding(
        finding_id=finding_id,
        investigation_id=investigation_id,
        title=title.strip(),
        description=description,
        status=status,
        rationale=rationale,
        supporting_events_json=json.dumps(supporting_events or []),
        contradictory_events_json=json.dumps(contradictory_events or []),
        unresolved_questions=unresolved_questions,
        requires_review=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding

def update_finding(
    db: Session,
    finding_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    rationale: Optional[str] = None,
    supporting_events: Optional[List[str]] = None,
    contradictory_events: Optional[List[str]] = None,
    unresolved_questions: Optional[str] = None,
    requires_review: Optional[bool] = None,
    review_reason: Optional[str] = None
) -> Optional[InvestigationFinding]:
    finding = db.query(InvestigationFinding).filter(InvestigationFinding.finding_id == finding_id).first()
    if not finding:
        return None

    if title is not None:
        finding.title = title
    if description is not None:
        finding.description = description
    if status is not None:
        finding.status = status
    if rationale is not None:
        finding.rationale = rationale
    if supporting_events is not None:
        finding.supporting_events_json = json.dumps(supporting_events)
    if contradictory_events is not None:
        finding.contradictory_events_json = json.dumps(contradictory_events)
    if unresolved_questions is not None:
        finding.unresolved_questions = unresolved_questions
    if requires_review is not None:
        finding.requires_review = requires_review
    if review_reason is not None:
        finding.review_reason = review_reason

    finding.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(finding)
    return finding
