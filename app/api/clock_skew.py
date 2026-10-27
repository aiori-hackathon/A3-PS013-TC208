from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.entities import ClockSkewEstimate
from app.services.clock_skew_service import estimate_clock_skew

router = APIRouter(prefix="/clock-skew", tags=["Clock Skew Estimation"])

class SkewRequest(BaseModel):
    evidence_a_id: str
    evidence_b_id: str
    matching_criteria: str = "source_ip_and_username"

@router.post("/estimate", status_code=status.HTTP_201_CREATED)
def run_clock_skew_estimate(payload: SkewRequest, actor: str = "Analyst", db: Session = Depends(get_db)):
    """Computes explainable clock-skew offset and uncertainty bounds between two evidence sources."""
    try:
        est = estimate_clock_skew(
            db=db,
            evidence_a_id=payload.evidence_a_id,
            evidence_b_id=payload.evidence_b_id,
            matching_criteria=payload.matching_criteria,
            actor=actor
        )
        return {
            "estimate_id": est.estimate_id,
            "source_evidence_a_id": est.source_evidence_a_id,
            "source_evidence_b_id": est.source_evidence_b_id,
            "matching_criteria": est.matching_criteria,
            "matched_pairs_count": est.matched_pairs_count,
            "estimated_offset_seconds": est.estimated_offset_seconds,
            "uncertainty_seconds": est.uncertainty_seconds,
            "confidence": est.confidence,
            "assumptions": est.assumptions,
            "calculated_at": est.calculated_at.isoformat()
        }
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Clock skew calculation failed: {str(ex)}")

@router.get("")
def list_skew_estimates(db: Session = Depends(get_db)):
    """Lists all clock-skew estimation sessions."""
    estimates = db.query(ClockSkewEstimate).order_by(desc(ClockSkewEstimate.calculated_at)).all()
    return [
        {
            "estimate_id": e.estimate_id,
            "source_evidence_a_id": e.source_evidence_a_id,
            "source_evidence_b_id": e.source_evidence_b_id,
            "matching_criteria": e.matching_criteria,
            "matched_pairs_count": e.matched_pairs_count,
            "estimated_offset_seconds": e.estimated_offset_seconds,
            "uncertainty_seconds": e.uncertainty_seconds,
            "confidence": e.confidence,
            "assumptions": e.assumptions,
            "calculated_at": e.calculated_at.isoformat()
        }
        for e in estimates
    ]
