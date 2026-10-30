from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class EvidenceFile(Base):
    __tablename__ = "evidence_files"
    
    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(String(64), unique=True, index=True, nullable=False)
    original_filename = Column(String(255), nullable=False)
    stored_path = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(128), default="text/plain")
    sha256_baseline = Column(String(64), nullable=False, index=True)
    collected_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    scenario_tag = Column(String(64), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    verifications = relationship("IntegrityVerification", back_populates="evidence", cascade="all, delete-orphan")
    ingestions = relationship("IngestionRun", back_populates="evidence", cascade="all, delete-orphan")
    source_records = relationship("SourceRecord", back_populates="evidence", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="evidence", cascade="all, delete-orphan")


class IntegrityVerification(Base):
    __tablename__ = "integrity_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    verification_id = Column(String(64), unique=True, index=True, nullable=False)
    evidence_id = Column(String(64), ForeignKey("evidence_files.evidence_id", ondelete="CASCADE"), nullable=False, index=True)
    verified_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    observed_hash = Column(String(64), nullable=False)
    baseline_hash = Column(String(64), nullable=False)
    result = Column(String(32), nullable=False)  # MATCH, MISMATCH, FILE_NOT_FOUND, ERROR
    error_message = Column(Text, nullable=True)
    details_json = Column(Text, nullable=True)
    
    evidence = relationship("EvidenceFile", back_populates="verifications")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    ingestion_id = Column(String(64), unique=True, index=True, nullable=False)
    evidence_id = Column(String(64), ForeignKey("evidence_files.evidence_id", ondelete="CASCADE"), nullable=False, index=True)
    parser_name = Column(String(64), nullable=False)
    parser_version = Column(String(32), default="1.0.0")
    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    total_records = Column(Integer, default=0)
    parsed_count = Column(Integer, default=0)
    partial_count = Column(Integer, default=0)
    ambiguous_count = Column(Integer, default=0)
    unparsed_count = Column(Integer, default=0)
    status = Column(String(32), default="IN_PROGRESS")  # IN_PROGRESS, COMPLETED, FAILED
    timezone_assumption = Column(String(64), default="UTC")
    clock_uncertainty_seconds = Column(Float, default=1.0)
    error_summary = Column(Text, nullable=True)
    
    evidence = relationship("EvidenceFile", back_populates="ingestions")
    ledger = relationship("ParsingLedger", back_populates="ingestion", uselist=False, cascade="all, delete-orphan")
    source_records = relationship("SourceRecord", back_populates="ingestion", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="ingestion", cascade="all, delete-orphan")


class ParsingLedger(Base):
    __tablename__ = "parsing_ledgers"
    
    id = Column(Integer, primary_key=True, index=True)
    ingestion_id = Column(String(64), ForeignKey("ingestion_runs.ingestion_id", ondelete="CASCADE"), unique=True, nullable=False)
    evidence_id = Column(String(64), nullable=False, index=True)
    total_records = Column(Integer, nullable=False)
    parsed_count = Column(Integer, nullable=False)
    partial_count = Column(Integer, nullable=False)
    ambiguous_count = Column(Integer, nullable=False)
    unparsed_count = Column(Integer, nullable=False)
    reconciled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    ingestion = relationship("IngestionRun", back_populates="ledger")


class SourceRecord(Base):
    __tablename__ = "source_records"
    
    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(String(64), ForeignKey("evidence_files.evidence_id", ondelete="CASCADE"), nullable=False, index=True)
    ingestion_id = Column(String(64), ForeignKey("ingestion_runs.ingestion_id", ondelete="CASCADE"), nullable=False, index=True)
    line_number = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=False)
    parsing_status = Column(String(32), nullable=False)  # PARSED, PARTIAL, AMBIGUOUS, UNPARSED
    parser_warnings = Column(Text, nullable=True)
    extracted_data_json = Column(Text, nullable=True)
    
    evidence = relationship("EvidenceFile", back_populates="source_records")
    ingestion = relationship("IngestionRun", back_populates="source_records")
    timeline_events = relationship("TimelineEvent", back_populates="source_record", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_source_evidence_line", "evidence_id", "line_number"),
    )


class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64), unique=True, index=True, nullable=False)
    evidence_id = Column(String(64), ForeignKey("evidence_files.evidence_id", ondelete="CASCADE"), nullable=False, index=True)
    ingestion_id = Column(String(64), ForeignKey("ingestion_runs.ingestion_id", ondelete="CASCADE"), nullable=False, index=True)
    source_record_id = Column(Integer, ForeignKey("source_records.id", ondelete="CASCADE"), nullable=False)
    source_line = Column(Integer, nullable=False)
    
    raw_timestamp = Column(String(128), nullable=True)
    parsed_timestamp = Column(DateTime(timezone=True), nullable=True)
    normalized_utc = Column(DateTime(timezone=True), nullable=True, index=True)
    earliest_utc = Column(DateTime(timezone=True), nullable=True, index=True)
    latest_utc = Column(DateTime(timezone=True), nullable=True, index=True)
    uncertainty_margin_seconds = Column(Float, default=1.0)
    time_status = Column(String(32), default="EXACT_OFFSET")  # EXACT_OFFSET, INFERRED_OFFSET, AMBIGUOUS, UNRESOLVED
    order_uncertain = Column(Boolean, default=False, index=True)
    
    event_type = Column(String(64), nullable=True, index=True)  # AUTH_FAILURE, AUTH_SUCCESS, HTTP_REQUEST, etc.
    hostname = Column(String(128), nullable=True, index=True)
    process_name = Column(String(64), nullable=True)
    pid = Column(String(32), nullable=True)
    username = Column(String(128), nullable=True, index=True)
    source_ip = Column(String(64), nullable=True, index=True)
    source_port = Column(Integer, nullable=True)
    
    http_method = Column(String(16), nullable=True)
    http_target = Column(String(1024), nullable=True)
    http_status = Column(Integer, nullable=True, index=True)
    response_bytes = Column(Integer, nullable=True)
    user_agent = Column(String(512), nullable=True)
    
    summary = Column(String(512), nullable=False)
    full_message = Column(Text, nullable=True)
    parsing_status = Column(String(32), nullable=False)
    warnings = Column(Text, nullable=True)
    
    evidence = relationship("EvidenceFile", back_populates="timeline_events")
    ingestion = relationship("IngestionRun", back_populates="timeline_events")
    source_record = relationship("SourceRecord", back_populates="timeline_events")


class ClockSkewEstimate(Base):
    __tablename__ = "clock_skew_estimates"
    
    id = Column(Integer, primary_key=True, index=True)
    estimate_id = Column(String(64), unique=True, index=True, nullable=False)
    source_evidence_a_id = Column(String(64), nullable=False)
    source_evidence_b_id = Column(String(64), nullable=False)
    matching_criteria = Column(String(255), nullable=False)
    matched_pairs_count = Column(Integer, default=0)
    estimated_offset_seconds = Column(Float, nullable=True)
    uncertainty_seconds = Column(Float, nullable=True)
    confidence = Column(String(32), default="INSUFFICIENT_MATCHES")  # HIGH, MEDIUM, LOW, INSUFFICIENT_MATCHES
    assumptions = Column(Text, nullable=True)
    calculated_at = Column(DateTime(timezone=True), default=utc_now)


class Investigation(Base):
    __tablename__ = "investigations"
    
    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(String(64), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), default="OPEN")  # OPEN, UNDER REVIEW, LIKELY, UNRESOLVED, CLOSED
    lead_investigator = Column(String(128), default="Analyst")
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    notes = Column(Text, nullable=True)
    
    findings = relationship("InvestigationFinding", back_populates="investigation", cascade="all, delete-orphan")
    reviews = relationship("BlindLensReview", back_populates="investigation", cascade="all, delete-orphan")


class InvestigationFinding(Base):
    __tablename__ = "investigation_findings"
    
    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(String(64), unique=True, index=True, nullable=False)
    investigation_id = Column(String(64), ForeignKey("investigations.investigation_id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), default="OPEN")  # OPEN, UNDER REVIEW, LIKELY, UNRESOLVED, CLOSED
    rationale = Column(Text, nullable=True)
    supporting_events_json = Column(Text, default="[]")
    contradictory_events_json = Column(Text, default="[]")
    unresolved_questions = Column(Text, nullable=True)
    requires_review = Column(Boolean, default=False, index=True)
    review_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    investigation = relationship("Investigation", back_populates="findings")


class BlindLensReview(Base):
    __tablename__ = "blindlens_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(String(64), unique=True, index=True, nullable=False)
    investigation_id = Column(String(64), ForeignKey("investigations.investigation_id", ondelete="CASCADE"), nullable=False, index=True)
    investigator_id = Column(String(128), default="Analyst")
    stage = Column(String(32), default="INITIAL")  # INITIAL, REVEALED
    
    # Stage 1: Initial Assessment (Prior to Context Reveal)
    initial_hypothesis = Column(Text, nullable=False)
    initial_confidence = Column(Integer, nullable=False)  # 0 - 100
    initial_evidence_refs_json = Column(Text, default="[]")
    initial_unresolved = Column(Text, nullable=True)
    initial_recorded_at = Column(DateTime(timezone=True), default=utc_now)
    initial_digest = Column(String(64), nullable=False)  # SHA-256 of canonical initial payload
    
    # Stage 2: Context Reveal & Re-Assessment
    context_items_json = Column(Text, default="[]")
    context_revealed_at = Column(DateTime(timezone=True), nullable=True)
    revised_hypothesis = Column(Text, nullable=True)
    revised_confidence = Column(Integer, nullable=True)
    reason_for_change = Column(Text, nullable=True)
    final_review_status = Column(String(32), default="IN_PROGRESS")  # IN_PROGRESS, CONFIRMED, REVISED, UNRESOLVED
    final_digest = Column(String(64), nullable=True)  # SHA-256 of canonical full review record
    is_tampered = Column(Boolean, default=False)
    
    investigation = relationship("Investigation", back_populates="reviews")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    
    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(String(64), unique=True, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utc_now, index=True)
    action = Column(String(64), nullable=False)  # EVIDENCE_UPLOAD, VERIFICATION, INGESTION, FINDING_UPDATE, etc.
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(64), nullable=False)
    actor = Column(String(128), default="System")
    details_json = Column(Text, nullable=True)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(64), unique=True, index=True, nullable=False)
    scenario_name = Column(String(128), nullable=False)
    run_at = Column(DateTime(timezone=True), default=utc_now)
    parsing_accuracy = Column(Float, nullable=True)
    traceability_rate = Column(Float, nullable=True)
    mutation_detection_rate = Column(Float, nullable=True)
    uncertain_order_rate = Column(Float, nullable=True)
    manual_triage_median_sec = Column(Float, nullable=True)
    assisted_triage_median_sec = Column(Float, nullable=True)
    metrics_json = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)


class GeneratedReport(Base):
    __tablename__ = "generated_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(64), unique=True, index=True, nullable=False)
    investigation_id = Column(String(64), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_format = Column(String(16), default="PDF")
    sha256_digest = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    record_count = Column(Integer, default=0)
    metadata_json = Column(Text, nullable=True)
