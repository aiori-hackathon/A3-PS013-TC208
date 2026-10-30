import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.entities import (
    EvidenceFile, IngestionRun, ParsingLedger, SourceRecord, TimelineEvent, AuditEvent
)
from app.parsers import get_parser
from app.services.normalization_service import normalize_to_utc
from app.services.uncertainty_service import evaluate_timeline_ordering

def run_ingestion(
    db: Session,
    evidence_id: str,
    parser_name: str,
    timezone_assumption: str = "UTC",
    default_year: Optional[int] = 2026,
    clock_uncertainty_seconds: float = 1.0,
    actor: str = "Analyst"
) -> IngestionRun:
    """
    Ingests an evidence file deterministically into SourceRecords and TimelineEvents,
    enforcing strict ledger accounting: TOTAL = PARSED + PARTIAL + AMBIGUOUS + UNPARSED.
    """
    evidence = db.query(EvidenceFile).filter(EvidenceFile.evidence_id == evidence_id).first()
    if not evidence:
        raise ValueError(f"Evidence file '{evidence_id}' not found.")

    file_path = Path(evidence.stored_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Underlying evidence file does not exist on disk: {file_path}")

    # Read raw evidence content
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        raw_lines = f.readlines()

    total_records = len(raw_lines)
    ingestion_id = f"ING-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    parser = get_parser(parser_name)

    started_at = datetime.now(timezone.utc)
    ingestion_run = IngestionRun(
        ingestion_id=ingestion_id,
        evidence_id=evidence_id,
        parser_name=parser.parser_name,
        parser_version=parser.parser_version,
        started_at=started_at,
        status="IN_PROGRESS",
        timezone_assumption=timezone_assumption,
        clock_uncertainty_seconds=clock_uncertainty_seconds,
        total_records=total_records
    )
    db.add(ingestion_run)
    db.flush()

    parsed_count = 0
    partial_count = 0
    ambiguous_count = 0
    unparsed_count = 0

    source_records_to_add: List[SourceRecord] = []
    events_to_add: List[TimelineEvent] = []

    # Parse line by line deterministically
    for idx, line_text in enumerate(raw_lines, start=1):
        parsed = parser.parse_line(
            line_number=idx,
            line_text=line_text,
            timezone_assumption=timezone_assumption,
            default_year=default_year
        )

        status = parsed.parsing_status
        if status == "PARSED":
            parsed_count += 1
        elif status == "PARTIAL":
            partial_count += 1
        elif status == "AMBIGUOUS":
            ambiguous_count += 1
        elif status == "UNPARSED":
            unparsed_count += 1
        else:
            unparsed_count += 1
            status = "UNPARSED"

        # Preserve the raw source record
        src_rec = SourceRecord(
            evidence_id=evidence_id,
            ingestion_id=ingestion_id,
            line_number=idx,
            raw_text=line_text,
            parsing_status=status,
            parser_warnings="; ".join(parsed.warnings) if parsed.warnings else None,
            extracted_data_json=json.dumps(parsed.extracted_data)
        )
        source_records_to_add.append(src_rec)

    # Bulk insert source records to obtain primary keys
    db.add_all(source_records_to_add)
    db.flush()

    # Re-read parsed representations and construct timeline events
    for idx, (line_text, src_rec) in enumerate(zip(raw_lines, source_records_to_add), start=1):
        parsed = parser.parse_line(
            line_number=idx,
            line_text=line_text,
            timezone_assumption=timezone_assumption,
            default_year=default_year
        )

        # Build timeline event for parsed, partial, and ambiguous records
        if parsed.parsing_status in ("PARSED", "PARTIAL", "AMBIGUOUS"):
            utc_dt, earliest_utc, latest_utc = normalize_to_utc(
                parsed.parsed_datetime,
                uncertainty_margin_seconds=clock_uncertainty_seconds,
                timezone_assumption=timezone_assumption
            )

            event = TimelineEvent(
                event_id=f"EVT-{uuid.uuid4().hex[:8].upper()}",
                evidence_id=evidence_id,
                ingestion_id=ingestion_id,
                source_record_id=src_rec.id,
                source_line=idx,
                raw_timestamp=parsed.raw_timestamp,
                parsed_timestamp=parsed.parsed_datetime,
                normalized_utc=utc_dt,
                earliest_utc=earliest_utc,
                latest_utc=latest_utc,
                uncertainty_margin_seconds=clock_uncertainty_seconds,
                time_status=parsed.time_status,
                order_uncertain=False,
                event_type=parsed.event_type,
                hostname=parsed.hostname,
                process_name=parsed.process_name,
                pid=parsed.pid,
                username=parsed.username,
                source_ip=parsed.source_ip,
                source_port=parsed.source_port,
                http_method=parsed.http_method,
                http_target=parsed.http_target,
                http_status=parsed.http_status,
                response_bytes=parsed.response_bytes,
                user_agent=parsed.user_agent,
                summary=parsed.summary,
                full_message=parsed.full_message,
                parsing_status=parsed.parsing_status,
                warnings="; ".join(parsed.warnings) if parsed.warnings else None
            )
            events_to_add.append(event)

    # Sort events by normalized_utc (with None values placed at the end) and evaluate ordering certainty
    events_with_time = [e for e in events_to_add if e.normalized_utc is not None]
    events_with_time.sort(key=lambda e: e.normalized_utc)
    evaluate_timeline_ordering(events_with_time)

    # Events lacking normalized timestamps are marked as order_uncertain
    for e in events_to_add:
        if e.normalized_utc is None:
            e.order_uncertain = True

    db.add_all(events_to_add)

    # Verify accounting invariant: TOTAL = PARSED + PARTIAL + AMBIGUOUS + UNPARSED
    sum_parts = parsed_count + partial_count + ambiguous_count + unparsed_count
    reconciled = (total_records == sum_parts)

    completed_at = datetime.now(timezone.utc)
    ingestion_run.completed_at = completed_at
    ingestion_run.parsed_count = parsed_count
    ingestion_run.partial_count = partial_count
    ingestion_run.ambiguous_count = ambiguous_count
    ingestion_run.unparsed_count = unparsed_count
    ingestion_run.status = "COMPLETED" if reconciled else "FAILED"
    if not reconciled:
        ingestion_run.error_summary = f"Accounting mismatch: total={total_records} != sum={sum_parts}"

    ledger = ParsingLedger(
        ingestion_id=ingestion_id,
        evidence_id=evidence_id,
        total_records=total_records,
        parsed_count=parsed_count,
        partial_count=partial_count,
        ambiguous_count=ambiguous_count,
        unparsed_count=unparsed_count,
        reconciled=reconciled,
        created_at=completed_at
    )
    db.add(ledger)

    audit = AuditEvent(
        audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
        timestamp=completed_at,
        action="INGESTION_COMPLETED",
        entity_type="INGESTION",
        entity_id=ingestion_id,
        actor=actor,
        details_json=json.dumps({
            "evidence_id": evidence_id,
            "parser": parser_name,
            "total": total_records,
            "parsed": parsed_count,
            "partial": partial_count,
            "ambiguous": ambiguous_count,
            "unparsed": unparsed_count,
            "reconciled": reconciled
        })
    )
    db.add(audit)

    db.commit()
    db.refresh(ingestion_run)
    return ingestion_run
