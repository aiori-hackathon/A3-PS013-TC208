import re
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from app.config import settings
from app.models.entities import EvidenceFile, AuditEvent, IntegrityVerification
from app.services.integrity_service import compute_sha256_bytes

def sanitize_filename(filename: str) -> str:
    """Sanitize user-provided filename to prevent path traversal and shell injection."""
    # Strip any directory path components
    base_name = Path(filename).name
    # Retain only safe alphanumeric characters, dashes, underscores, and dots
    safe_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", base_name)
    if not safe_name:
        safe_name = "unnamed_evidence.log"
    return safe_name

def collect_evidence_file(
    db: Session,
    filename: str,
    file_bytes: bytes,
    mime_type: str = "text/plain",
    scenario_tag: Optional[str] = None,
    notes: Optional[str] = None,
    actor: str = "Analyst"
) -> EvidenceFile:
    """
    Preserve raw evidence file bytes into managed storage with SHA-256 baseline.
    Enforces immutability: never rewrites existing files.
    """
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise ValueError(f"File size exceeds maximum allowed threshold of {settings.MAX_UPLOAD_SIZE_BYTES} bytes.")

    safe_name = sanitize_filename(filename)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_uuid = uuid.uuid4().hex[:6].upper()
    evidence_id = f"EV-{date_str}-{short_uuid}"

    # Target storage path using server-generated identifier
    stored_filename = f"{evidence_id}_{safe_name}"
    target_path = settings.EVIDENCE_DIR / stored_filename

    # Prevent collision
    if target_path.exists():
        stored_filename = f"{evidence_id}_{uuid.uuid4().hex[:4]}_{safe_name}"
        target_path = settings.EVIDENCE_DIR / stored_filename

    # Compute baseline SHA-256 over exact collected bytes
    sha256_baseline = compute_sha256_bytes(file_bytes)

    # Write exact bytes to managed evidence store
    with open(target_path, "wb") as f:
        f.write(file_bytes)

    # Persist metadata to database
    evidence = EvidenceFile(
        evidence_id=evidence_id,
        original_filename=safe_name,
        stored_path=str(target_path),
        file_size_bytes=len(file_bytes),
        mime_type=mime_type,
        sha256_baseline=sha256_baseline,
        collected_at=datetime.now(timezone.utc),
        scenario_tag=scenario_tag,
        notes=notes,
        is_active=True
    )
    db.add(evidence)

    # Record initial baseline verification
    verification = IntegrityVerification(
        verification_id=f"VER-INIT-{short_uuid}",
        evidence_id=evidence_id,
        verified_at=datetime.now(timezone.utc),
        observed_hash=sha256_baseline,
        baseline_hash=sha256_baseline,
        result="MATCH",
        error_message=None,
        details_json='{"event": "INITIAL_BASELINE_COLLECTION"}'
    )
    db.add(verification)

    # Record audit event
    audit = AuditEvent(
        audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
        timestamp=datetime.now(timezone.utc),
        action="EVIDENCE_COLLECTED",
        entity_type="EVIDENCE",
        entity_id=evidence_id,
        actor=actor,
        details_json=f'{{"filename": "{safe_name}", "bytes": {len(file_bytes)}, "sha256": "{sha256_baseline}"}}'
    )
    db.add(audit)

    db.commit()
    db.refresh(evidence)
    return evidence

def get_evidence_file(db: Session, evidence_id: str) -> Optional[EvidenceFile]:
    return db.query(EvidenceFile).filter(EvidenceFile.evidence_id == evidence_id).first()

def list_evidence_files(db: Session) -> List[EvidenceFile]:
    return db.query(EvidenceFile).order_by(EvidenceFile.collected_at.desc()).all()
