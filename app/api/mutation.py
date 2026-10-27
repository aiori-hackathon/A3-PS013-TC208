import json
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.mutation_service import get_mutation_summary, get_mutation_impact
from app.services.scenario_service import simulate_file_mutation

router = APIRouter(prefix="/mutation", tags=["Mutation Radar"])

@router.get("/summary")
def get_integrity_summary(db: Session = Depends(get_db)):
    """Provides fleet-wide integrity verification status and count of impacted findings."""
    return get_mutation_summary(db)

@router.get("/impact/{evidence_id}")
def get_impact_map(evidence_id: str, db: Session = Depends(get_db)):
    """
    Computes an impact map tracing from a specific evidence file to its
    source records, timeline events, linked findings, and generated reports.
    """
    try:
        impact = get_mutation_impact(db, evidence_id)
        # Format affected findings
        affected_findings_out = []
        for f in impact["affected_findings"]:
            affected_findings_out.append({
                "finding_id": f.finding_id,
                "investigation_id": f.investigation_id,
                "title": f.title,
                "status": f.status,
                "requires_review": f.requires_review,
                "review_reason": f.review_reason
            })

        return {
            "evidence_id": impact["evidence_id"],
            "has_mismatch": impact["has_mismatch"],
            "baseline_hash": impact["baseline_hash"],
            "observed_hash": impact["observed_hash"],
            "affected_source_records_count": impact["affected_source_records_count"],
            "affected_timeline_events_count": impact["affected_timeline_events_count"],
            "affected_findings": affected_findings_out,
            "affected_reports_count": impact["affected_reports_count"],
            "requires_review_flagged": impact["requires_review_flagged"]
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.post("/simulate/{evidence_id}")
def simulate_mutation(evidence_id: str, actor: str = "TestFixture", db: Session = Depends(get_db)):
    """
    Simulates post-collection modification on a test evidence copy (Scenario 3 demo),
    triggering a real baseline hash mismatch and Mutation Radar review flags.
    """
    try:
        res = simulate_file_mutation(db, evidence_id, actor=actor)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(ex)}")
