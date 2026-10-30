import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.entities import (
    EvidenceFile, IntegrityVerification, SourceRecord, TimelineEvent,
    InvestigationFinding, GeneratedReport, AuditEvent
)

def get_mutation_summary(db: Session) -> Dict[str, Any]:
    """Provides a fleet-wide integrity and mutation summary across all collected evidence."""
    evidence_list = db.query(EvidenceFile).all()
    
    total = len(evidence_list)
    verified = 0
    matches = 0
    mismatches = 0
    errors = 0
    impacted_findings = db.query(InvestigationFinding).filter(InvestigationFinding.requires_review == True).count()

    files_summary = []
    for ev in evidence_list:
        latest_ver = db.query(IntegrityVerification).filter(
            IntegrityVerification.evidence_id == ev.evidence_id
        ).order_by(desc(IntegrityVerification.verified_at)).first()

        status = "UNVERIFIED"
        last_verified_at = None
        obs_hash = None

        if latest_ver:
            verified += 1
            status = latest_ver.result
            last_verified_at = latest_ver.verified_at.isoformat()
            obs_hash = latest_ver.observed_hash
            if status == "MATCH":
                matches += 1
            elif status == "MISMATCH":
                mismatches += 1
            else:
                errors += 1

        files_summary.append({
            "evidence_id": ev.evidence_id,
            "filename": ev.original_filename,
            "baseline_hash": ev.sha256_baseline,
            "observed_hash": obs_hash,
            "status": status,
            "last_verified_at": last_verified_at,
            "scenario_tag": ev.scenario_tag
        })

    return {
        "total_evidence_files": total,
        "verified_files": verified,
        "match_count": matches,
        "mismatch_count": mismatches,
        "error_count": errors,
        "impacted_findings_count": impacted_findings,
        "files": files_summary
    }

def get_mutation_impact(db: Session, evidence_id: str) -> Dict[str, Any]:
    """
    Computes an impact map tracing from a specific evidence file to its
    source records, timeline events, linked findings, and generated reports.
    """
    evidence = db.query(EvidenceFile).filter(EvidenceFile.evidence_id == evidence_id).first()
    if not evidence:
        raise ValueError(f"Evidence file '{evidence_id}' does not exist.")

    latest_ver = db.query(IntegrityVerification).filter(
        IntegrityVerification.evidence_id == evidence_id
    ).order_by(desc(IntegrityVerification.verified_at)).first()

    has_mismatch = latest_ver and (latest_ver.result in ("MISMATCH", "FILE_NOT_FOUND"))
    observed_hash = latest_ver.observed_hash if latest_ver else None

    # Count affected records & events
    source_count = db.query(SourceRecord).filter(SourceRecord.evidence_id == evidence_id).count()
    event_ids = [e.event_id for e in db.query(TimelineEvent.event_id).filter(TimelineEvent.evidence_id == evidence_id).all()]
    events_count = len(event_ids)

    # Find affected findings that reference any of these event IDs
    all_findings = db.query(InvestigationFinding).all()
    affected_findings: List[InvestigationFinding] = []

    event_id_set = set(event_ids)
    for f in all_findings:
        supporting = json.loads(f.supporting_events_json or "[]")
        contradictory = json.loads(f.contradictory_events_json or "[]")
        cited_events = set(supporting + contradictory)
        if cited_events.intersection(event_id_set):
            affected_findings.append(f)

    # Dependent reports
    reports_count = db.query(GeneratedReport).count()

    return {
        "evidence_id": evidence_id,
        "has_mismatch": bool(has_mismatch),
        "baseline_hash": evidence.sha256_baseline,
        "observed_hash": observed_hash,
        "affected_source_records_count": source_count,
        "affected_timeline_events_count": events_count,
        "affected_findings": affected_findings,
        "affected_reports_count": reports_count,
        "requires_review_flagged": has_mismatch
    }

def trigger_mutation_impact(db: Session, evidence_id: str, observed_hash: str):
    """
    When an evidence file mismatch is detected, automatically flags all findings
    that cite events from this evidence as requiring review.
    Does NOT rewrite the investigator's conclusion.
    """
    impact = get_mutation_impact(db, evidence_id)
    affected_findings = impact["affected_findings"]

    reason = f"Mutation Radar alert: Evidence '{evidence_id}' failed SHA-256 verification (Observed: {observed_hash[:16]}...)"
    flagged_count = 0

    for f in affected_findings:
        f.requires_review = True
        f.review_reason = reason
        f.updated_at = datetime.now(timezone.utc)
        flagged_count += 1

    if flagged_count > 0:
        audit = AuditEvent(
            audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
            timestamp=datetime.now(timezone.utc),
            action="MUTATION_RADAR_FLAGGED_FINDINGS",
            entity_type="EVIDENCE",
            entity_id=evidence_id,
            actor="MutationRadar",
            details_json=json.dumps({
                "flagged_findings_count": flagged_count,
                "evidence_id": evidence_id,
                "observed_hash": observed_hash
            })
        )
        db.add(audit)
        db.commit()
