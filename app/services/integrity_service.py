import hashlib
import uuid
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.entities import EvidenceFile, IntegrityVerification, AuditEvent

def compute_sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 hexadecimal digest for raw bytes."""
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest().lower()

def compute_sha256_file(filepath: Path) -> str:
    """Compute SHA-256 hexadecimal digest for a file on disk."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()

def verify_evidence_file(db: Session, evidence_id: str, actor: str = "Analyst") -> IntegrityVerification:
    """
    Perform a live SHA-256 integrity verification against the recorded baseline.
    Records an append-only IntegrityVerification record in the database.
    """
    evidence = db.query(EvidenceFile).filter(EvidenceFile.evidence_id == evidence_id).first()
    if not evidence:
        raise ValueError(f"Evidence file with ID '{evidence_id}' does not exist.")

    file_path = Path(evidence.stored_path)
    verification_id = f"VER-{uuid.uuid4().hex[:8].upper()}"
    observed_hash = ""
    result = "ERROR"
    error_message = None

    if not file_path.exists():
        result = "FILE_NOT_FOUND"
        observed_hash = "0" * 64
        error_message = f"Stored evidence file missing from disk: {file_path}"
    else:
        try:
            observed_hash = compute_sha256_file(file_path)
            if observed_hash == evidence.sha256_baseline:
                result = "MATCH"
            else:
                result = "MISMATCH"
                error_message = (
                    f"Integrity mismatch detected! Stored baseline: {evidence.sha256_baseline}, "
                    f"Observed on disk: {observed_hash}"
                )
        except Exception as ex:
            result = "ERROR"
            observed_hash = "0" * 64
            error_message = f"Failed to read file for verification: {str(ex)}"

    verification = IntegrityVerification(
        verification_id=verification_id,
        evidence_id=evidence_id,
        verified_at=datetime.now(timezone.utc),
        observed_hash=observed_hash,
        baseline_hash=evidence.sha256_baseline,
        result=result,
        error_message=error_message,
        details_json=None
    )
    db.add(verification)

    # Record audit event
    audit = AuditEvent(
        audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
        timestamp=datetime.now(timezone.utc),
        action="INTEGRITY_VERIFICATION",
        entity_type="EVIDENCE",
        entity_id=evidence_id,
        actor=actor,
        details_json=f'{{"result": "{result}", "observed_hash": "{observed_hash}"}}'
    )
    db.add(audit)
    db.commit()
    db.refresh(verification)

    # If mismatch, trigger Mutation Radar impact check to mark dependent findings for review
    if result == "MISMATCH":
        from app.services.mutation_service import trigger_mutation_impact
        trigger_mutation_impact(db, evidence_id, observed_hash)

    return verification
