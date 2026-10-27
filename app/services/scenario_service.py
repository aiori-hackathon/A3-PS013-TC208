import json
import uuid
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.config import settings
from app.models.entities import EvidenceFile, Investigation, InvestigationFinding, AuditEvent
from app.services.evidence_service import collect_evidence_file
from app.services.ingestion_service import run_ingestion
from app.services.clock_skew_service import estimate_clock_skew
from app.services.integrity_service import verify_evidence_file

SCENARIOS = {
    "scenario-01": {
        "id": "scenario-01",
        "folder": "scenario-01-normal",
        "title": "Scenario 1: Normal Operations & Baseline Authentication",
        "description": "Baseline operational telemetry with web reconnaissance, failed SSH probes, and authorized analyst login."
    },
    "scenario-02": {
        "id": "scenario-02",
        "folder": "scenario-02-clock-skew",
        "title": "Scenario 2: Clock Skew & Overlapping Uncertainty",
        "description": "Simulated incident across two servers where web proxy has +180s clock offset and overlapping intervals."
    },
    "scenario-03": {
        "id": "scenario-03",
        "folder": "scenario-03-changed-file",
        "title": "Scenario 3: Changed File Integrity Mutation",
        "description": "Evidence tampering simulation with baseline mismatch detection and Mutation Radar impact mapping."
    }
}

def list_available_scenarios() -> List[Dict[str, Any]]:
    return list(SCENARIOS.values())

def load_scenario(db: Session, scenario_id: str, actor: str = "Analyst") -> Dict[str, Any]:
    """
    Loads and ingests a synthetic scenario deterministically.
    """
    if scenario_id not in SCENARIOS:
        raise ValueError(f"Unknown scenario ID '{scenario_id}'. Available: {list(SCENARIOS.keys())}")

    scenario_info = SCENARIOS[scenario_id]
    scenario_path = settings.SAMPLE_DATA_DIR / scenario_info["folder"]
    meta_path = scenario_path / "metadata.json"

    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    loaded_evidence_ids = []
    ingestion_ids = []

    # 1. Collect and ingest each source
    for src in metadata.get("sources", []):
        filename = src["filename"]
        parser_name = src["parser"]
        file_path = scenario_path / filename

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        ev = collect_evidence_file(
            db=db,
            filename=f"{scenario_id}_{filename}",
            file_bytes=file_bytes,
            scenario_tag=scenario_id,
            notes=f"Synthetic demonstration file for {metadata['name']}",
            actor=actor
        )
        loaded_evidence_ids.append(ev.evidence_id)

        ing_run = run_ingestion(
            db=db,
            evidence_id=ev.evidence_id,
            parser_name=parser_name,
            timezone_assumption=metadata.get("timezone_assumption", "UTC"),
            default_year=metadata.get("default_year", 2026),
            clock_uncertainty_seconds=metadata.get("uncertainty_seconds", 1.0),
            actor=actor
        )
        ingestion_ids.append(ing_run.ingestion_id)

    # 2. Scenario-specific setup
    investigation_id = None
    if scenario_id == "scenario-01":
        inv = Investigation(
            investigation_id=f"INV-{uuid.uuid4().hex[:6].upper()}",
            title="Investigation: Reconnaissance and Authentication Triage",
            description="Reconstruction of external reconnaissance followed by authenticated analyst access.",
            status="UNDER REVIEW",
            lead_investigator="Lead Analyst"
        )
        db.add(inv)
        db.flush()
        investigation_id = inv.investigation_id

        # Add sample finding linked to evidence
        fnd = InvestigationFinding(
            finding_id=f"FND-{uuid.uuid4().hex[:8].upper()}",
            investigation_id=inv.investigation_id,
            title="External brute force probe from 192.0.2.10",
            description="Rapid consecutive SSH failures for admin and guest users following web reconnaissance.",
            status="LIKELY",
            rationale="Observed 3 failed SSH attempts within 5 seconds after GET /login 401.",
            supporting_events_json="[]",
            requires_review=False
        )
        db.add(fnd)
        db.commit()

    elif scenario_id == "scenario-02" and len(loaded_evidence_ids) >= 2:
        # Run clock skew estimation between the two ingested sources
        estimate_clock_skew(
            db=db,
            evidence_a_id=loaded_evidence_ids[0],
            evidence_b_id=loaded_evidence_ids[1],
            matching_criteria="source_ip_and_username",
            actor=actor
        )

    elif scenario_id == "scenario-03":
        # Create an investigation with a dependent finding
        inv = Investigation(
            investigation_id=f"INV-{uuid.uuid4().hex[:6].upper()}",
            title="Investigation: Tampering & Integrity Verification Demonstration",
            description="Investigation referencing baseline evidence to demonstrate Mutation Radar reactive review flagging.",
            status="OPEN",
            lead_investigator="Forensic Auditor"
        )
        db.add(inv)
        db.flush()
        investigation_id = inv.investigation_id

        # Link finding to the first evidence's events
        fnd = InvestigationFinding(
            finding_id=f"FND-{uuid.uuid4().hex[:8].upper()}",
            investigation_id=inv.investigation_id,
            title="Authentication baseline for host01",
            description="Baseline login activity established from collected auth.log evidence.",
            status="OPEN",
            rationale="Source records show auditor login session 210 at 11:00:12.",
            supporting_events_json="[]",
            requires_review=False
        )
        db.add(fnd)
        db.commit()

    return {
        "scenario_id": scenario_id,
        "name": metadata.get("name"),
        "evidence_ids": loaded_evidence_ids,
        "ingestion_ids": ingestion_ids,
        "investigation_id": investigation_id,
        "message": f"Successfully loaded scenario '{metadata.get('name')}'"
    }

def simulate_file_mutation(db: Session, evidence_id: str, actor: str = "TestFixture") -> Dict[str, Any]:
    """
    Controlled modification of a stored evidence file for demonstration/testing of Scenario 3.
    Appends an unauthorized line to trigger SHA-256 mismatch and Mutation Radar impact.
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.evidence_id == evidence_id).first()
    if not ev:
        raise ValueError(f"Evidence file '{evidence_id}' not found.")

    target_path = Path(ev.stored_path)
    if not target_path.exists():
        raise FileNotFoundError(f"File '{target_path}' does not exist.")

    # Append controlled mutation
    tamper_line = b"Oct 27 11:00:25 host01 sshd[35109]: Accepted password for root from 203.0.113.80 port 55104 ssh2\n"
    with open(target_path, "ab") as f:
        f.write(tamper_line)

    # Re-verify integrity immediately to demonstrate mismatch detection
    verification = verify_evidence_file(db, evidence_id, actor=actor)

    return {
        "evidence_id": evidence_id,
        "mutation_applied": True,
        "verification_result": verification.result,
        "baseline_hash": verification.baseline_hash,
        "observed_hash": verification.observed_hash,
        "message": "Controlled modification applied. Mutation Radar alert triggered."
    }
