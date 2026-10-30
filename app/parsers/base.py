from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class ParsedRecord(BaseModel):
    line_number: int
    raw_text: str
    parsing_status: str  # PARSED, PARTIAL, AMBIGUOUS, UNPARSED
    
    # Timestamp data
    raw_timestamp: Optional[str] = None
    parsed_datetime: Optional[datetime] = None  # Naive or aware datetime before normalization
    timezone_offset_str: Optional[str] = None
    time_status: str = "UNRESOLVED"  # EXACT_OFFSET, INFERRED_OFFSET, AMBIGUOUS, UNRESOLVED
    time_assumptions: Optional[str] = None
    
    # Event attributes
    event_type: Optional[str] = None  # AUTH_FAILURE, AUTH_SUCCESS, HTTP_REQUEST, SESSION_OPEN, etc.
    hostname: Optional[str] = None
    process_name: Optional[str] = None
    pid: Optional[str] = None
    username: Optional[str] = None
    source_ip: Optional[str] = None
    source_port: Optional[int] = None
    
    # Web fields
    http_method: Optional[str] = None
    http_target: Optional[str] = None
    http_protocol: Optional[str] = None
    http_status: Optional[int] = None
    response_bytes: Optional[int] = None
    referer: Optional[str] = None
    user_agent: Optional[str] = None
    
    summary: str
    full_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    extracted_data: Dict[str, Any] = Field(default_factory=dict)

class BaseLogParser(ABC):
    parser_name: str = "base"
    parser_version: str = "1.0.0"

    @abstractmethod
    def parse_line(
        self,
        line_number: int,
        line_text: str,
        timezone_assumption: str = "UTC",
        default_year: Optional[int] = 2026,
        **kwargs
    ) -> ParsedRecord:
        """Parse a single raw log line deterministically into a ParsedRecord."""
        pass

    def parse_lines(
        self,
        lines: List[str],
        timezone_assumption: str = "UTC",
        default_year: Optional[int] = 2026,
        **kwargs
    ) -> List[ParsedRecord]:
        """Parse all lines sequentially preserving order and line numbers."""
        records = []
        for idx, line in enumerate(lines, start=1):
            record = self.parse_line(
                line_number=idx,
                line_text=line,
                timezone_assumption=timezone_assumption,
                default_year=default_year,
                **kwargs
            )
            records.append(record)
        return records
