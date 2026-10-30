from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

# Base & Health
class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    version: str
    environment: str
    database_connected: bool
    evidence_storage_writable: bool

# Evidence Schemas
class EvidenceFileOut(BaseModel):
    id: int
    evidence_id: str
    original_filename: str
    file_size_bytes: int
    mime_type: str
    sha256_baseline: str
    collected_at: datetime
    scenario_tag: Optional[str] = None
    notes: Optional[str] = None
    latest_verification_status: Optional[str] = None
    latest_verification_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class VerificationResultOut(BaseModel):
    verification_id: str
    evidence_id: str
    verified_at: datetime
    baseline_hash: str
    observed_hash: str
    result: str  # MATCH, MISMATCH, FILE_NOT_FOUND, ERROR
    error_message: Optional[str] = None
    has_mismatch: bool

class VerificationHistoryOut(BaseModel):
    evidence_id: str
    verifications: List[VerificationResultOut]

# Ingestion & Parsing Schemas
class IngestionRequest(BaseModel):
    evidence_id: str
    parser_name: str  # "linux_auth" or "nginx_access"
    timezone_assumption: str = "UTC"
    default_year: Optional[int] = 2026
    clock_uncertainty_seconds: float = 1.0

class ParsingLedgerOut(BaseModel):
    ledger_id: int
    ingestion_id: str
    evidence_id: str
    total_records: int
    parsed_count: int
    partial_count: int
    ambiguous_count: int
    unparsed_count: int
    reconciled: bool
    created_at: datetime

    class Config:
        from_attributes = True

class IngestionRunOut(BaseModel):
    ingestion_id: str
    evidence_id: str
    parser_name: str
    parser_version: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_records: int
    parsed_count: int
    partial_count: int
    ambiguous_count: int
    unparsed_count: int
    status: str
    timezone_assumption: str
    clock_uncertainty_seconds: float
    error_summary: Optional[str] = None
    ledger: Optional[ParsingLedgerOut] = None

    class Config:
        from_attributes = True

# Source Record & Gaps
class SourceRecordOut(BaseModel):
    id: int
    evidence_id: str
    ingestion_id: str
    line_number: int
    raw_text: str
    parsing_status: str
    parser_warnings: Optional[str] = None
    extracted_data_json: Optional[str] = None

    class Config:
        from_attributes = True

# Timeline Event Schemas
class TimelineEventOut(BaseModel):
    id: int
    event_id: str
    evidence_id: str
    ingestion_id: str
    source_record_id: int
    source_line: int
    raw_timestamp: Optional[str] = None
    normalized_utc: Optional[datetime] = None
    earliest_utc: Optional[datetime] = None
    latest_utc: Optional[datetime] = None
    uncertainty_margin_seconds: float
    time_status: str
    order_uncertain: bool
    event_type: Optional[str] = None
    hostname: Optional[str] = None
    process_name: Optional[str] = None
    pid: Optional[str] = None
    username: Optional[str] = None
    source_ip: Optional[str] = None
    source_port: Optional[int] = None
    http_method: Optional[str] = None
    http_target: Optional[str] = None
    http_status: Optional[int] = None
    response_bytes: Optional[int] = None
    user_agent: Optional[str] = None
    summary: str
    full_message: Optional[str] = None
    parsing_status: str
    warnings: Optional[str] = None

    class Config:
        from_attributes = True

class TimelineQueryResult(BaseModel):
    total_count: int
    page: int
    page_size: int
    total_pages: int
    events: List[TimelineEventOut]

# Clock Skew
class ClockSkewEstimateOut(BaseModel):
    estimate_id: str
    source_evidence_a_id: str
    source_evidence_b_id: str
    matching_criteria: str
    matched_pairs_count: int
    estimated_offset_seconds: Optional[float] = None
    uncertainty_seconds: Optional[float] = None
    confidence: str
    assumptions: Optional[str] = None
    calculated_at: datetime

    class Config:
        from_attributes = True

# Investigation & Findings
class FindingCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "OPEN"
    rationale: Optional[str] = None
    supporting_events: List[str] = []
    contradictory_events: List[str] = []
    unresolved_questions: Optional[str] = None

class FindingOut(BaseModel):
    id: int
    finding_id: str
    investigation_id: str
    title: str
    description: Optional[str] = None
    status: str
    rationale: Optional[str] = None
    supporting_events: List[str] = []
    contradictory_events: List[str] = []
    unresolved_questions: Optional[str] = None
    requires_review: bool
    review_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class InvestigationCreate(BaseModel):
    title: str
    description: Optional[str] = None
    lead_investigator: Optional[str] = "Analyst"

class InvestigationOut(BaseModel):
    id: int
    investigation_id: str
    title: str
    description: Optional[str] = None
    status: str
    lead_investigator: str
    created_at: datetime
    updated_at: datetime
    notes: Optional[str] = None
    findings_count: int = 0
    requires_review_count: int = 0
    findings: List[FindingOut] = []

    class Config:
        from_attributes = True

# BlindLens Review Schemas
class BlindLensCreate(BaseModel):
    investigation_id: str
    investigator_id: Optional[str] = "Analyst"
    initial_hypothesis: str
    initial_confidence: int = Field(ge=0, le=100)
    initial_evidence_refs: List[str] = []
    initial_unresolved: Optional[str] = None
    # Context items that will be sealed until stage 2 reveal
    context_items: List[Dict[str, Any]] = []

class BlindLensReveal(BaseModel):
    # Triggers stage 2 reveal
    pass

class BlindLensRevision(BaseModel):
    revised_hypothesis: str
    revised_confidence: int = Field(ge=0, le=100)
    reason_for_change: str  # Required if hypothesis or confidence changes
    final_review_status: str = "CONFIRMED"  # CONFIRMED, REVISED, UNRESOLVED

class BlindLensReviewOut(BaseModel):
    id: int
    review_id: str
    investigation_id: str
    investigator_id: str
    stage: str
    initial_hypothesis: str
    initial_confidence: int
    initial_evidence_refs: List[str]
    initial_unresolved: Optional[str] = None
    initial_recorded_at: datetime
    initial_digest: str
    context_items: List[Dict[str, Any]]
    context_revealed_at: Optional[datetime] = None
    revised_hypothesis: Optional[str] = None
    revised_confidence: Optional[int] = None
    reason_for_change: Optional[str] = None
    final_review_status: str
    final_digest: Optional[str] = None
    is_tampered: bool

    class Config:
        from_attributes = True

class BlindLensVerificationOut(BaseModel):
    review_id: str
    initial_digest_match: bool
    final_digest_match: Optional[bool] = None
    is_valid: bool
    calculated_initial_digest: str
    stored_initial_digest: str
    calculated_final_digest: Optional[str] = None
    stored_final_digest: Optional[str] = None
    message: str

# Mutation Radar
class MutationImpactOut(BaseModel):
    evidence_id: str
    has_mismatch: bool
    baseline_hash: str
    observed_hash: Optional[str] = None
    affected_source_records_count: int
    affected_timeline_events_count: int
    affected_findings: List[FindingOut]
    affected_reports_count: int
    requires_review_flagged: bool

class MutationSummaryOut(BaseModel):
    total_evidence_files: int
    verified_files: int
    match_count: int
    mismatch_count: int
    error_count: int
    impacted_findings_count: int
    files: List[Dict[str, Any]]

# Dashboard Summary
class DashboardSummaryOut(BaseModel):
    evidence_files_count: int
    total_source_records: int
    parsed_records: int
    partial_records: int
    ambiguous_records: int
    unparsed_records: int
    timeline_events_count: int
    evidence_mismatches_count: int
    findings_requiring_review_count: int
    investigations_count: int
    blindlens_reviews_count: int
    environment_label: str
    is_synthetic_mode: bool

# Evaluation
class EvaluationRunRequest(BaseModel):
    scenario_name: str = "all"
    record_trial_time_seconds: Optional[float] = None
    is_manual_trial: Optional[bool] = False

class EvaluationResultOut(BaseModel):
    run_id: str
    scenario_name: str
    run_at: datetime
    parsing_accuracy: float
    traceability_rate: float
    mutation_detection_rate: float
    uncertain_order_rate: float
    manual_triage_median_sec: Optional[float] = None
    assisted_triage_median_sec: Optional[float] = None
    metrics: Dict[str, Any]
    notes: Optional[str] = None

# Reports
class ReportCreateRequest(BaseModel):
    investigation_id: Optional[str] = None
    title: str
    format: str = "PDF"  # PDF or CSV
    include_timeline: bool = True
    include_ledger: bool = True
    include_mutation_radar: bool = True
    include_blindlens: bool = True
    include_benchmarks: bool = True
