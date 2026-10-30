import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.entities import BlindLensReview
from app.schemas.schemas import BlindLensCreate, BlindLensRevision
from app.services.blindlens_service import (
    create_blindlens_review, reveal_blindlens_context,
    record_blindlens_revision, verify_blindlens_review
)

router = APIRouter(prefix="/blindlens", tags=["BlindLens Staged Review"])

@router.post("/reviews", status_code=status.HTTP_201_CREATED)
def new_blindlens_review(payload: BlindLensCreate, actor: str = "Analyst", db: Session = Depends(get_db)):
    """Stage 1: Records initial hypothesis prior to context reveal with canonical cryptographic digest."""
    try:
        review = create_blindlens_review(
            db=db,
            investigation_id=payload.investigation_id,
            initial_hypothesis=payload.initial_hypothesis,
            initial_confidence=payload.initial_confidence,
            initial_evidence_refs=payload.initial_evidence_refs,
            initial_unresolved=payload.initial_unresolved,
            context_items=payload.context_items,
            investigator_id=actor
        )
        return {
            "review_id": review.review_id,
            "investigation_id": review.investigation_id,
            "stage": review.stage,
            "initial_hypothesis": review.initial_hypothesis,
            "initial_confidence": review.initial_confidence,
            "initial_digest": review.initial_digest,
            "message": "Stage 1 initial assessment recorded and sealed with SHA-256 canonical digest."
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.get("/reviews")
def list_blindlens_reviews(db: Session = Depends(get_db)):
    """Lists all BlindLens reviews."""
    reviews = db.query(BlindLensReview).order_by(desc(BlindLensReview.initial_recorded_at)).all()
    result = []
    for r in reviews:
        result.append({
            "id": r.id,
            "review_id": r.review_id,
            "investigation_id": r.investigation_id,
            "investigator_id": r.investigator_id,
            "stage": r.stage,
            "initial_hypothesis": r.initial_hypothesis,
            "initial_confidence": r.initial_confidence,
            "initial_recorded_at": r.initial_recorded_at.isoformat(),
            "initial_digest": r.initial_digest,
            "context_revealed_at": r.context_revealed_at.isoformat() if r.context_revealed_at else None,
            "revised_hypothesis": r.revised_hypothesis,
            "revised_confidence": r.revised_confidence,
            "reason_for_change": r.reason_for_change,
            "final_review_status": r.final_review_status,
            "final_digest": r.final_digest,
            "is_tampered": r.is_tampered
        })
    return result

@router.get("/reviews/{review_id}")
def get_blindlens_review_detail(review_id: str, db: Session = Depends(get_db)):
    """Retrieves full details of a BlindLens review, including context items if revealed."""
    r = db.query(BlindLensReview).filter(BlindLensReview.review_id == review_id).first()
    if not r:
        raise HTTPException(status_code=404, detail=f"BlindLens review '{review_id}' not found.")

    context_items = json.loads(r.context_items_json or "[]")
    # If in Stage 1, do not disclose context details to enforce blind evaluation
    visible_context = context_items if r.stage == "REVEALED" else [{"status": "SEALED", "count": len(context_items)}]

    return {
        "id": r.id,
        "review_id": r.review_id,
        "investigation_id": r.investigation_id,
        "investigator_id": r.investigator_id,
        "stage": r.stage,
        "initial_hypothesis": r.initial_hypothesis,
        "initial_confidence": r.initial_confidence,
        "initial_evidence_refs": json.loads(r.initial_evidence_refs_json or "[]"),
        "initial_unresolved": r.initial_unresolved,
        "initial_recorded_at": r.initial_recorded_at.isoformat(),
        "initial_digest": r.initial_digest,
        "context_items": visible_context,
        "context_revealed_at": r.context_revealed_at.isoformat() if r.context_revealed_at else None,
        "revised_hypothesis": r.revised_hypothesis,
        "revised_confidence": r.revised_confidence,
        "reason_for_change": r.reason_for_change,
        "final_review_status": r.final_review_status,
        "final_digest": r.final_digest,
        "is_tampered": r.is_tampered
    }

@router.post("/reviews/{review_id}/reveal")
def reveal_context(review_id: str, actor: str = "Analyst", db: Session = Depends(get_db)):
    """Stage 2: Reveals configured context while preserving Stage 1 baseline intact."""
    try:
        r = reveal_blindlens_context(db=db, review_id=review_id, actor=actor)
        return {
            "review_id": r.review_id,
            "stage": r.stage,
            "context_revealed_at": r.context_revealed_at.isoformat() if r.context_revealed_at else None,
            "context_items": json.loads(r.context_items_json or "[]"),
            "message": "Context revealed. Investigator may now record a revised assessment."
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.post("/reviews/{review_id}/revision")
def submit_revision(review_id: str, payload: BlindLensRevision, actor: str = "Analyst", db: Session = Depends(get_db)):
    """Stage 2: Records revised hypothesis, confidence, and required rationale for change."""
    try:
        r = record_blindlens_revision(
            db=db,
            review_id=review_id,
            revised_hypothesis=payload.revised_hypothesis,
            revised_confidence=payload.revised_confidence,
            reason_for_change=payload.reason_for_change,
            final_review_status=payload.final_review_status,
            actor=actor
        )
        return {
            "review_id": r.review_id,
            "stage": r.stage,
            "revised_hypothesis": r.revised_hypothesis,
            "revised_confidence": r.revised_confidence,
            "final_review_status": r.final_review_status,
            "final_digest": r.final_digest,
            "message": "Revision recorded with canonical final digest."
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.post("/reviews/{review_id}/verify")
def verify_review_integrity(review_id: str, db: Session = Depends(get_db)):
    """Verifies review record cryptographic digests against canonical serialization."""
    try:
        res = verify_blindlens_review(db=db, review_id=review_id)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
