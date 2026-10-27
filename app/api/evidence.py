from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.entities import EvidenceFile, IntegrityVerification
from app.services.evidence_service import collect_evidence_file, get_evidence_file, list_evidence_files
from app.services.integrity_service import verify_evidence_file

router = APIRouter(prefix="/evidence", tags=["Evidence"])

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    file: UploadFile = File(...),
    notes: Optional[str] = Form(None),
    scenario_tag: Optional[str] = Form(None),
    actor: str = Form("Analyst"),
    db: Session = Depends(get_db)
):
    """
    Upload and securely collect an evidence log file into managed storage.
    Computes baseline SHA-256 and records initial verification state.
    """
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        evidence = collect_evidence_file(
            db=db,
            filename=file.filename or "unknown.log",
            file_bytes=content,
            mime_type=file.content_type or "text/plain",
            scenario_tag=scenario_tag,
            notes=notes,
            actor=actor
        )

        return {
            "evidence_id": evidence.evidence_id,
            "filename": evidence.original_filename,
            "file_size_bytes": evidence.file_size_bytes,
            "sha256_baseline": evidence.sha256_baseline,
            "collected_at": evidence.collected_at.isoformat(),
            "message": "Evidence successfully collected and baseline SHA-256 computed."
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Evidence collection failed: {str(ex)}")

@router.get("")
def get_all_evidence(db: Session = Depends(get_db)):
    """Lists all collected evidence files with their latest verification results."""
    files = list_evidence_files(db)
    result = []
    for ev in files:
        latest_v = db.query(IntegrityVerification).filter(
            IntegrityVerification.evidence_id == ev.evidence_id
        ).order_by(desc(IntegrityVerification.verified_at)).first()

        result.append({
            "id": ev.id,
            "evidence_id": ev.evidence_id,
            "original_filename": ev.original_filename,
            "file_size_bytes": ev.file_size_bytes,
            "mime_type": ev.mime_type,
            "sha256_baseline": ev.sha256_baseline,
            "collected_at": ev.collected_at.isoformat(),
            "scenario_tag": ev.scenario_tag,
            "notes": ev.notes,
            "latest_verification_status": latest_v.result if latest_v else "UNVERIFIED",
            "latest_verification_at": latest_v.verified_at.isoformat() if latest_v else None
        })
    return result

@router.get("/{evidence_id}")
def get_evidence_detail(evidence_id: str, db: Session = Depends(get_db)):
    """Retrieves full metadata for a specific collected evidence record."""
    ev = get_evidence_file(db, evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence file '{evidence_id}' not found.")

    latest_v = db.query(IntegrityVerification).filter(
        IntegrityVerification.evidence_id == ev.evidence_id
    ).order_by(desc(IntegrityVerification.verified_at)).first()

    return {
        "id": ev.id,
        "evidence_id": ev.evidence_id,
        "original_filename": ev.original_filename,
        "file_size_bytes": ev.file_size_bytes,
        "mime_type": ev.mime_type,
        "sha256_baseline": ev.sha256_baseline,
        "collected_at": ev.collected_at.isoformat(),
        "scenario_tag": ev.scenario_tag,
        "notes": ev.notes,
        "latest_verification_status": latest_v.result if latest_v else "UNVERIFIED",
        "latest_verification_at": latest_v.verified_at.isoformat() if latest_v else None
    }

@router.post("/{evidence_id}/verify")
def verify_evidence(evidence_id: str, actor: str = "Analyst", db: Session = Depends(get_db)):
    """Performs live SHA-256 verification against the recorded cryptographic baseline."""
    try:
        verification = verify_evidence_file(db, evidence_id, actor=actor)
        return {
            "verification_id": verification.verification_id,
            "evidence_id": verification.evidence_id,
            "verified_at": verification.verified_at.isoformat(),
            "baseline_hash": verification.baseline_hash,
            "observed_hash": verification.observed_hash,
            "result": verification.result,
            "error_message": verification.error_message,
            "has_mismatch": verification.result in ("MISMATCH", "FILE_NOT_FOUND")
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(ex)}")

@router.get("/{evidence_id}/verification-history")
def get_verification_history(evidence_id: str, db: Session = Depends(get_db)):
    """Returns the append-only verification history for this evidence file."""
    ev = get_evidence_file(db, evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence file '{evidence_id}' not found.")

    verifications = db.query(IntegrityVerification).filter(
        IntegrityVerification.evidence_id == evidence_id
    ).order_by(desc(IntegrityVerification.verified_at)).all()

    return {
        "evidence_id": evidence_id,
        "baseline_hash": ev.sha256_baseline,
        "verifications": [
            {
                "verification_id": v.verification_id,
                "verified_at": v.verified_at.isoformat(),
                "observed_hash": v.observed_hash,
                "result": v.result,
                "error_message": v.error_message
            }
            for v in verifications
        ]
    }
