import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app.parsers.base import BaseLogParser, ParsedRecord

class NginxAccessParser(BaseLogParser):
    parser_name: str = "nginx_access"
    parser_version: str = "1.0.0"

    # Robust regex for Nginx combined log format with escaped quote handling
    NGINX_COMBINED_REGEX = re.compile(
        r"^(?P<ip>\S+)\s+"
        r"(?P<ident>\S+)\s+"
        r"(?P<user>\S+)\s+"
        r"\[(?P<time>[^\]]+)\]\s+"
        r'"(?P<request>(?:[^"\\]|\\.)*)"\s+'
        r"(?P<status>\d{3})\s+"
        r"(?P<bytes>\S+)\s+"
        r'"(?P<referer>(?:[^"\\]|\\.)*)"\s+'
        r'"(?P<agent>(?:[^"\\]|\\.)*)"'
    )

    REQUEST_SPLIT_REGEX = re.compile(r"^(?P<method>[A-Z]+)\s+(?P<target>\S+)(?:\s+(?P<proto>HTTP/\d\.\d))?$")

    def parse_line(
        self,
        line_number: int,
        line_text: str,
        timezone_assumption: str = "UTC",
        default_year: Optional[int] = 2026,
        **kwargs
    ) -> ParsedRecord:
        clean_text = line_text.strip()

        # Blank line accounting
        if not clean_text:
            return ParsedRecord(
                line_number=line_number,
                raw_text=line_text,
                parsing_status="UNPARSED",
                time_status="UNRESOLVED",
                summary="Empty or whitespace line",
                warnings=["Blank line in input stream"]
            )

        match = self.NGINX_COMBINED_REGEX.match(clean_text)
        if not match:
            # Check if this might be a partial/corrupted HTTP access line (e.g. quotes missing or truncated)
            if re.match(r"^\S+\s+\S+\s+\S+\s+\[", clean_text):
                return ParsedRecord(
                    line_number=line_number,
                    raw_text=line_text,
                    parsing_status="PARTIAL",
                    time_status="UNRESOLVED",
                    summary="Malformed Nginx combined record (unclosed quotes or truncated fields)",
                    warnings=["Line starts like combined access log but failed strict quote/field validation"]
                )
            return ParsedRecord(
                line_number=line_number,
                raw_text=line_text,
                parsing_status="UNPARSED",
                time_status="UNRESOLVED",
                summary="Unrecognized log format (not standard Nginx combined)",
                warnings=["Line does not match Nginx combined access log structure"]
            )

        groups = match.groupdict()
        client_ip = groups["ip"]
        raw_user = groups["user"]
        raw_time = groups["time"]
        raw_request = groups["request"]
        raw_status = groups["status"]
        raw_bytes = groups["bytes"]
        referer = groups["referer"]
        user_agent = groups["agent"]

        username = None if raw_user == "-" else raw_user
        http_status = int(raw_status)
        response_bytes = int(raw_bytes) if raw_bytes.isdigit() else 0

        # Parse request string
        http_method = None
        http_target = None
        http_protocol = None
        req_match = self.REQUEST_SPLIT_REGEX.match(raw_request)
        if req_match:
            http_method = req_match.group("method")
            http_target = req_match.group("target")
            http_protocol = req_match.group("proto")
        else:
            http_target = raw_request

        warnings: List[str] = []
        parsed_dt: Optional[datetime] = None
        time_status = "EXACT_OFFSET"
        tz_offset_str = None

        # Parse timestamp e.g. "27/Oct/2026:10:30:01 +0000"
        try:
            parsed_dt = datetime.strptime(raw_time, "%d/%b/%Y:%H:%M:%S %z")
            tz_offset_str = raw_time.split(" ")[-1] if " " in raw_time else "+0000"
        except Exception as ex:
            time_status = "AMBIGUOUS"
            warnings.append(f"Failed to parse Nginx timestamp '{raw_time}': {str(ex)}")

        parsing_status = "PARSED"
        if not http_method:
            parsing_status = "PARTIAL"
            warnings.append(f"Could not parse valid HTTP method from request line: '{raw_request}'")
        if time_status == "AMBIGUOUS":
            parsing_status = "AMBIGUOUS"

        # Event type
        event_type = "HTTP_REQUEST"
        if http_status in (401, 403):
            event_type = "HTTP_AUTH_FAILURE"
        elif http_status >= 500:
            event_type = "HTTP_SERVER_ERROR"

        summary = f"HTTP {http_method or 'REQ'} {http_target or '-'} -> {http_status} from {client_ip}"
        if username:
            summary += f" (user: {username})"

        extracted = {
            "client_ip": client_ip,
            "username": username,
            "raw_time": raw_time,
            "method": http_method,
            "target": http_target,
            "protocol": http_protocol,
            "status": http_status,
            "bytes_sent": response_bytes,
            "referer": referer,
            "user_agent": user_agent
        }

        return ParsedRecord(
            line_number=line_number,
            raw_text=line_text,
            parsing_status=parsing_status,
            raw_timestamp=raw_time,
            parsed_datetime=parsed_dt,
            timezone_offset_str=tz_offset_str,
            time_status=time_status,
            time_assumptions="Extracted exact timezone offset from ISO/Nginx timestamp format" if time_status == "EXACT_OFFSET" else None,
            event_type=event_type,
            hostname=None,
            process_name="nginx",
            pid=None,
            username=username,
            source_ip=client_ip,
            source_port=None,
            http_method=http_method,
            http_target=http_target,
            http_protocol=http_protocol,
            http_status=http_status,
            response_bytes=response_bytes,
            referer=referer,
            user_agent=user_agent,
            summary=summary,
            full_message=f"{raw_request} [{raw_status}] {user_agent}",
            warnings=warnings,
            extracted_data=extracted
        )
