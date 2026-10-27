import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.entities import EvaluationRun
from app.schemas.schemas import EvaluationRunRequest
from app.services.evaluation_service import run_evaluation_benchmark, get_latest_evaluation, list_evaluations

router = APIRouter(prefix="/evaluation", tags=["Evaluation & Benchmarks"])

@router.post("/run", status_code=status.HTTP_201_CREATED)
def trigger_benchmark(payload: EvaluationRunRequest, actor: str = "Analyst", db: Session = Depends(get_db)):
    """Runs empirical benchmark evaluating parsing accuracy, traceability, mutation detection, and triage times."""
    try:
        run = run_evaluation_benchmark(
            db=db,
            scenario_name=payload.scenario_name,
            record_trial_time_seconds=payload.record_trial_time_seconds,
            is_manual_trial=bool(payload.is_manual_trial),
            actor=actor
        )
        return {
            "run_id": run.run_id,
            "scenario_name": run.scenario_name,
            "run_at": run.run_at.isoformat(),
            "parsing_accuracy": run.parsing_accuracy,
            "traceability_rate": run.traceability_rate,
            "mutation_detection_rate": run.mutation_detection_rate,
            "uncertain_order_rate": run.uncertain_order_rate,
            "manual_triage_median_sec": run.manual_triage_median_sec,
            "assisted_triage_median_sec": run.assisted_triage_median_sec,
            "metrics": json.loads(run.metrics_json or "{}"),
            "notes": run.notes
        }
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Benchmark execution failed: {str(ex)}")

@router.get("/results")
def get_evaluation_history(db: Session = Depends(get_db)):
    """Lists all benchmark runs."""
    runs = list_evaluations(db)
    result = []
    for r in runs:
        result.append({
            "run_id": r.run_id,
            "scenario_name": r.scenario_name,
            "run_at": r.run_at.isoformat(),
            "parsing_accuracy": r.parsing_accuracy,
            "traceability_rate": r.traceability_rate,
            "mutation_detection_rate": r.mutation_detection_rate,
            "uncertain_order_rate": r.uncertain_order_rate,
            "manual_triage_median_sec": r.manual_triage_median_sec,
            "assisted_triage_median_sec": r.assisted_triage_median_sec,
            "metrics": json.loads(r.metrics_json or "{}")
        })
    return result

@router.get("/latest")
def get_latest_result(db: Session = Depends(get_db)):
    """Retrieves the most recent benchmark run."""
    run = get_latest_evaluation(db)
    if not run:
        return {"status": "NOT YET MEASURED", "message": "No benchmark runs executed yet. Run benchmark to measure metrics."}

    return {
        "status": "MEASURED",
        "run_id": run.run_id,
        "scenario_name": run.scenario_name,
        "run_at": run.run_at.isoformat(),
        "parsing_accuracy": run.parsing_accuracy,
        "traceability_rate": run.traceability_rate,
        "mutation_detection_rate": run.mutation_detection_rate,
        "uncertain_order_rate": run.uncertain_order_rate,
        "manual_triage_median_sec": run.manual_triage_median_sec,
        "assisted_triage_median_sec": run.assisted_triage_median_sec,
        "metrics": json.loads(run.metrics_json or "{}"),
        "notes": run.notes
    }
