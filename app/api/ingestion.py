from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.entities import IngestionRun, ParsingLedger, SourceRecord
from app.schemas.schemas import IngestionRequest
from app.services.ingestion_service import run_ingestion

router = APIRouter(prefix="/ingestions", tags=["Ingestion & Parsing"])

@router.post("", status_code=status.HTTP_201_CREATED)
def trigger_ingestion(payload: IngestionRequest, actor: str = "Analyst", db: Session = Depends(get_db)):
    """Triggers deterministic log ingestion, populating source records, timeline events, and ledger."""
    try:
        run = run_ingestion(
            db=db,
            evidence_id=payload.evidence_id,
            parser_name=payload.parser_name,
            timezone_assumption=payload.timezone_assumption,
            default_year=payload.default_year,
            clock_uncertainty_seconds=payload.clock_uncertainty_seconds,
            actor=actor
        )
        return {
            "ingestion_id": run.ingestion_id,
            "evidence_id": run.evidence_id,
            "parser_name": run.parser_name,
            "status": run.status,
            "total_records": run.total_records,
            "parsed_count": run.parsed_count,
            "partial_count": run.partial_count,
            "ambiguous_count": run.ambiguous_count,
            "unparsed_count": run.unparsed_count,
            "reconciled": (run.total_records == (run.parsed_count + run.partial_count + run.ambiguous_count + run.unparsed_count)),
            "message": "Log file successfully ingested and reconciled in parsing ledger."
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(ex)}")

@router.get("")
def list_ingestions(db: Session = Depends(get_db)):
    """Lists all past ingestion runs."""
    runs = db.query(IngestionRun).order_by(desc(IngestionRun.started_at)).all()
    result = []
    for r in runs:
        ledger = db.query(ParsingLedger).filter(ParsingLedger.ingestion_id == r.ingestion_id).first()
        result.append({
            "ingestion_id": r.ingestion_id,
            "evidence_id": r.evidence_id,
            "parser_name": r.parser_name,
            "parser_version": r.parser_version,
            "started_at": r.started_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "status": r.status,
            "total_records": r.total_records,
            "parsed_count": r.parsed_count,
            "partial_count": r.partial_count,
            "ambiguous_count": r.ambiguous_count,
            "unparsed_count": r.unparsed_count,
            "timezone_assumption": r.timezone_assumption,
            "clock_uncertainty_seconds": r.clock_uncertainty_seconds,
            "reconciled": ledger.reconciled if ledger else False
        })
    return result

@router.get("/{ingestion_id}")
def get_ingestion_detail(ingestion_id: str, db: Session = Depends(get_db)):
    """Retrieves metadata and ledger for a specific ingestion run."""
    run = db.query(IngestionRun).filter(IngestionRun.ingestion_id == ingestion_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Ingestion run '{ingestion_id}' not found.")

    ledger = db.query(ParsingLedger).filter(ParsingLedger.ingestion_id == ingestion_id).first()
    return {
        "ingestion_id": run.ingestion_id,
        "evidence_id": run.evidence_id,
        "parser_name": run.parser_name,
        "parser_version": run.parser_version,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "status": run.status,
        "total_records": run.total_records,
        "parsed_count": run.parsed_count,
        "partial_count": run.partial_count,
        "ambiguous_count": run.ambiguous_count,
        "unparsed_count": run.unparsed_count,
        "timezone_assumption": run.timezone_assumption,
        "clock_uncertainty_seconds": run.clock_uncertainty_seconds,
        "error_summary": run.error_summary,
        "ledger": {
            "total": ledger.total_records if ledger else 0,
            "reconciled": ledger.reconciled if ledger else False,
            "parsed": ledger.parsed_count if ledger else 0,
            "partial": ledger.partial_count if ledger else 0,
            "ambiguous": ledger.ambiguous_count if ledger else 0,
            "unparsed": ledger.unparsed_count if ledger else 0
        } if ledger else None
    }

@router.get("/{ingestion_id}/ledger")
def get_ingestion_ledger(ingestion_id: str, db: Session = Depends(get_db)):
    """Retrieves the accounting ledger proving TOTAL = PARSED + PARTIAL + AMBIGUOUS + UNPARSED."""
    ledger = db.query(ParsingLedger).filter(ParsingLedger.ingestion_id == ingestion_id).first()
    if not ledger:
        raise HTTPException(status_code=404, detail=f"Ledger for ingestion '{ingestion_id}' not found.")

    return {
        "ledger_id": ledger.id,
        "ingestion_id": ledger.ingestion_id,
        "evidence_id": ledger.evidence_id,
        "total_records": ledger.total_records,
        "parsed_count": ledger.parsed_count,
        "partial_count": ledger.partial_count,
        "ambiguous_count": ledger.ambiguous_count,
        "unparsed_count": ledger.unparsed_count,
        "reconciled": ledger.reconciled,
        "formula": f"{ledger.total_records} = {ledger.parsed_count} + {ledger.partial_count} + {ledger.ambiguous_count} + {ledger.unparsed_count}",
        "created_at": ledger.created_at.isoformat()
    }

@router.get("/gaps/inspect")
def inspect_parsing_gaps(
    evidence_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Retrieves problematic or non-PARSED records (PARTIAL, AMBIGUOUS, UNPARSED)."""
    query = db.query(SourceRecord)
    if status_filter:
        query = query.filter(SourceRecord.parsing_status == status_filter)
    else:
        query = query.filter(SourceRecord.parsing_status.in_(["PARTIAL", "AMBIGUOUS", "UNPARSED"]))

    if evidence_id:
        query = query.filter(SourceRecord.evidence_id == evidence_id)

    total = query.count()
    records = query.order_by(SourceRecord.id.asc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "records": [
            {
                "id": r.id,
                "evidence_id": r.evidence_id,
                "ingestion_id": r.ingestion_id,
                "line_number": r.line_number,
                "raw_text": r.raw_text,
                "parsing_status": r.parsing_status,
                "parser_warnings": r.parser_warnings
            }
            for r in records
        ]
    }
