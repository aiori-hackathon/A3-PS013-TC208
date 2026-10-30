import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.entities import Investigation, InvestigationFinding
from app.schemas.schemas import InvestigationCreate, FindingCreate
from app.services.investigation_service import (
    create_investigation, get_investigation, list_investigations,
    create_finding, update_finding
)

router = APIRouter(prefix="/investigations", tags=["Investigations & Findings"])

@router.post("", status_code=status.HTTP_201_CREATED)
def new_investigation(payload: InvestigationCreate, db: Session = Depends(get_db)):
    """Creates a new incident investigation workspace."""
    inv = create_investigation(
        db=db,
        title=payload.title,
        description=payload.description,
        lead_investigator=payload.lead_investigator or "Analyst"
    )
    return {
        "investigation_id": inv.investigation_id,
        "title": inv.title,
        "status": inv.status,
        "created_at": inv.created_at.isoformat(),
        "message": "Investigation workspace initialized."
    }

@router.get("")
def get_all_investigations(db: Session = Depends(get_db)):
    """Lists all investigations with findings metrics."""
    invs = list_investigations(db)
    result = []
    for inv in invs:
        findings_count = len(inv.findings)
        review_flags_count = sum(1 for f in inv.findings if f.requires_review)
        result.append({
            "id": inv.id,
            "investigation_id": inv.investigation_id,
            "title": inv.title,
            "description": inv.description,
            "status": inv.status,
            "lead_investigator": inv.lead_investigator,
            "created_at": inv.created_at.isoformat(),
            "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
            "findings_count": findings_count,
            "requires_review_count": review_flags_count
        })
    return result

@router.get("/{investigation_id}")
def get_investigation_detail(investigation_id: str, db: Session = Depends(get_db)):
    """Retrieves full details of an investigation including its linked findings."""
    inv = get_investigation(db, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail=f"Investigation '{investigation_id}' not found.")

    findings_out = []
    for f in inv.findings:
        findings_out.append({
            "id": f.id,
            "finding_id": f.finding_id,
            "investigation_id": f.investigation_id,
            "title": f.title,
            "description": f.description,
            "status": f.status,
            "rationale": f.rationale,
            "supporting_events": json.loads(f.supporting_events_json or "[]"),
            "contradictory_events": json.loads(f.contradictory_events_json or "[]"),
            "unresolved_questions": f.unresolved_questions,
            "requires_review": f.requires_review,
            "review_reason": f.review_reason,
            "created_at": f.created_at.isoformat(),
            "updated_at": f.updated_at.isoformat() if f.updated_at else None
        })

    return {
        "id": inv.id,
        "investigation_id": inv.investigation_id,
        "title": inv.title,
        "description": inv.description,
        "status": inv.status,
        "lead_investigator": inv.lead_investigator,
        "created_at": inv.created_at.isoformat(),
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
        "findings": findings_out
    }

@router.post("/{investigation_id}/findings", status_code=status.HTTP_201_CREATED)
def add_finding(investigation_id: str, payload: FindingCreate, actor: str = "Analyst", db: Session = Depends(get_db)):
    """Records an investigative finding with supporting and contradictory evidence references."""
    try:
        f = create_finding(
            db=db,
            investigation_id=investigation_id,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            rationale=payload.rationale,
            supporting_events=payload.supporting_events,
            contradictory_events=payload.contradictory_events,
            unresolved_questions=payload.unresolved_questions,
            actor=actor
        )
        return {
            "finding_id": f.finding_id,
            "investigation_id": f.investigation_id,
            "title": f.title,
            "status": f.status,
            "created_at": f.created_at.isoformat(),
            "message": "Investigative finding recorded."
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.patch("/findings/{finding_id}")
def update_investigation_finding(
    finding_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    rationale: Optional[str] = None,
    unresolved_questions: Optional[str] = None,
    requires_review: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Updates finding attributes, rationale, or dismisses review flags."""
    f = update_finding(
        db=db,
        finding_id=finding_id,
        title=title,
        description=description,
        status=status,
        rationale=rationale,
        unresolved_questions=unresolved_questions,
        requires_review=requires_review
    )
    if not f:
        raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found.")

    return {
        "finding_id": f.finding_id,
        "title": f.title,
        "status": f.status,
        "requires_review": f.requires_review,
        "review_reason": f.review_reason,
        "updated_at": f.updated_at.isoformat()
    }
