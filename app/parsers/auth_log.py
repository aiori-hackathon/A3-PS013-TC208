import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional, List, Dict, Any
from app.parsers.base import BaseLogParser, ParsedRecord

class LinuxAuthParser(BaseLogParser):
    parser_name: str = "linux_auth"
    parser_version: str = "1.0.0"

    # RFC 3164 Syslog header regex: e.g. "Oct 27 10:30:01 host01 sshd[1234]: message"
    SYSLOG_REGEX = re.compile(
        r"^(?P<month>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+"
        r"(?P<hostname>[a-zA-Z0-9_\-\.]+)\s+"
        r"(?P<process>[a-zA-Z0-9_\-\./]+)(?:\[(?P<pid>\d+)\])?:\s+"
        r"(?P<message>.*)$"
    )

    # Sub-patterns for authentication messages
    RE_FAILED_INVALID = re.compile(r"^Failed password for invalid user\s+(?P<user>\S+)\s+from\s+(?P<ip>[0-9a-fA-F\.\:]+)\s+port\s+(?P<port>\d+)(?:\s+(?P<proto>\S+))?")
    RE_FAILED_NORMAL = re.compile(r"^Failed password for\s+(?P<user>\S+)\s+from\s+(?P<ip>[0-9a-fA-F\.\:]+)\s+port\s+(?P<port>\d+)(?:\s+(?P<proto>\S+))?")
    RE_ACCEPTED = re.compile(r"^Accepted\s+(?P<auth_method>publickey|password|keyboard-interactive)\s+for\s+(?P<user>\S+)\s+from\s+(?P<ip>[0-9a-fA-F\.\:]+)\s+port\s+(?P<port>\d+)(?:\s+(?P<proto>\S+))?")
    RE_INVALID_USER = re.compile(r"^Invalid user\s+(?P<user>\S+)\s+from\s+(?P<ip>[0-9a-fA-F\.\:]+)\s+port\s+(?P<port>\d+)")
    RE_PAM_FAILURE = re.compile(r"pam_unix\((?P<pam_app>[^)]+)\): authentication failure;.*")
    RE_PAM_SESSION_OPEN = re.compile(r"pam_unix\((?P<pam_app>[^)]+)\): session opened for user\s+(?P<user>\S+)(?:\s+by\s+\(uid=\d+\))?")
    RE_PAM_SESSION_CLOSE = re.compile(r"pam_unix\((?P<pam_app>[^)]+)\): session closed for user\s+(?P<user>\S+)")
    RE_CONN_CLOSED = re.compile(r"^Connection closed by (?:authenticating user (?P<user>\S+) )?(?P<ip>[0-9a-fA-F\.\:]+)\s+port\s+(?P<port>\d+)")

    MONTH_MAP = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
    }

    def parse_line(
        self,
        line_number: int,
        line_text: str,
        timezone_assumption: str = "UTC",
        default_year: Optional[int] = 2026,
        **kwargs
    ) -> ParsedRecord:
        clean_text = line_text.strip()
        
        # Blank line handling: must be explicitly classified as UNPARSED per accounting requirements
        if not clean_text:
            return ParsedRecord(
                line_number=line_number,
                raw_text=line_text,
                parsing_status="UNPARSED",
                time_status="UNRESOLVED",
                summary="Empty or whitespace line",
                warnings=["Blank line in input stream"]
            )

        match = self.SYSLOG_REGEX.match(clean_text)
        if not match:
            return ParsedRecord(
                line_number=line_number,
                raw_text=line_text,
                parsing_status="UNPARSED",
                time_status="UNRESOLVED",
                summary="Unrecognized log format (syslog header missing)",
                warnings=["Line does not conform to RFC 3164 Syslog standard format"]
            )

        groups = match.groupdict()
        month_str = groups["month"]
        day_str = groups["day"]
        time_str = groups["time"]
        hostname = groups["hostname"]
        process = groups["process"]
        pid = groups["pid"]
        message = groups["message"]

        raw_timestamp_str = f"{month_str} {day_str} {time_str}"
        warnings: List[str] = []
        extracted: Dict[str, Any] = {
            "month": month_str,
            "day": int(day_str),
            "time": time_str,
            "hostname": hostname,
            "process": process,
            "pid": pid,
            "message": message
        }

        # Handle syslog missing year & timezone
        parsed_dt: Optional[datetime] = None
        time_status = "UNRESOLVED"
        time_assumptions = None

        if month_str in self.MONTH_MAP:
            month_num = self.MONTH_MAP[month_str]
            day_num = int(day_str)
            hour, minute, second = map(int, time_str.split(":"))

            if default_year is not None:
                try:
                    if timezone_assumption and timezone_assumption.upper() in ("UTC", "Z"):
                        tz = timezone.utc
                    else:
                        try:
                            tz = ZoneInfo(timezone_assumption) if timezone_assumption else timezone.utc
                        except Exception:
                            tz = timezone.utc

                    parsed_dt = datetime(default_year, month_num, day_num, hour, minute, second, tzinfo=tz)
                    time_status = "INFERRED_OFFSET"
                    time_assumptions = f"Year inferred as {default_year}; Timezone inferred as {timezone_assumption} from configuration"
                    warnings.append(f"Syslog timestamp lacks year and timezone. Inferred year={default_year}, tz={timezone_assumption}")
                except Exception as ex:
                    time_status = "AMBIGUOUS"
                    warnings.append(f"Error parsing inferred datetime: {str(ex)}")
            else:
                time_status = "AMBIGUOUS"
                warnings.append("Syslog timestamp lacks year; no default year configured")
        else:
            time_status = "AMBIGUOUS"
            warnings.append(f"Invalid month name '{month_str}' in syslog timestamp")

        # Classify authentication message
        event_type = "SYSTEM"
        username = None
        source_ip = None
        source_port = None
        parsing_status = "PARSED"

        # 1. Failed password invalid user
        m_failed_inv = self.RE_FAILED_INVALID.match(message)
        if m_failed_inv:
            event_type = "AUTH_FAILURE"
            username = m_failed_inv.group("user")
            source_ip = m_failed_inv.group("ip")
            source_port = int(m_failed_inv.group("port"))
            extracted["user_status"] = "invalid"
            summary = f"SSH authentication failed for invalid user '{username}' from {source_ip}:{source_port}"
        else:
            # 2. Failed password normal user
            m_failed_norm = self.RE_FAILED_NORMAL.match(message)
            if m_failed_norm:
                event_type = "AUTH_FAILURE"
                username = m_failed_norm.group("user")
                source_ip = m_failed_norm.group("ip")
                source_port = int(m_failed_norm.group("port"))
                summary = f"SSH authentication failed for user '{username}' from {source_ip}:{source_port}"
            else:
                # 3. Accepted publickey/password
                m_accepted = self.RE_ACCEPTED.match(message)
                if m_accepted:
                    event_type = "AUTH_SUCCESS"
                    username = m_accepted.group("user")
                    source_ip = m_accepted.group("ip")
                    source_port = int(m_accepted.group("port"))
                    auth_meth = m_accepted.group("auth_method")
                    extracted["auth_method"] = auth_meth
                    summary = f"SSH authentication accepted ({auth_meth}) for user '{username}' from {source_ip}:{source_port}"
                else:
                    # 4. Invalid user attempt
                    m_inv = self.RE_INVALID_USER.match(message)
                    if m_inv:
                        event_type = "AUTH_FAILURE"
                        username = m_inv.group("user")
                        source_ip = m_inv.group("ip")
                        source_port = int(m_inv.group("port"))
                        summary = f"Invalid user probe for '{username}' from {source_ip}:{source_port}"
                    else:
                        # 5. PAM failure
                        m_pam_fail = self.RE_PAM_FAILURE.match(message)
                        if m_pam_fail:
                            event_type = "AUTH_FAILURE"
                            # Attempt to extract user/rhost from message
                            user_m = re.search(r"user=(\S+)", message)
                            rhost_m = re.search(r"rhost=(\S+)", message)
                            if user_m and user_m.group(1):
                                username = user_m.group(1)
                            if rhost_m and rhost_m.group(1):
                                source_ip = rhost_m.group(1)
                            summary = f"PAM authentication failure ({m_pam_fail.group('pam_app')})" + (f" for user '{username}'" if username else "")
                        else:
                            # 6. PAM session opened
                            m_sess_open = self.RE_PAM_SESSION_OPEN.match(message)
                            if m_sess_open:
                                event_type = "SESSION_OPEN"
                                username = m_sess_open.group("user")
                                summary = f"PAM session opened for user '{username}' ({m_sess_open.group('pam_app')})"
                            else:
                                # 7. PAM session closed
                                m_sess_close = self.RE_PAM_SESSION_CLOSE.match(message)
                                if m_sess_close:
                                    event_type = "SESSION_CLOSE"
                                    username = m_sess_close.group("user")
                                    summary = f"PAM session closed for user '{username}' ({m_sess_close.group('pam_app')})"
                                else:
                                    # 8. Connection closed
                                    m_close = self.RE_CONN_CLOSED.match(message)
                                    if m_close:
                                        event_type = "CONNECTION_CLOSE"
                                        source_ip = m_close.group("ip")
                                        source_port = int(m_close.group("port"))
                                        if m_close.group("user"):
                                            username = m_close.group("user")
                                        summary = f"SSH connection closed by {source_ip}:{source_port}"
                                    else:
                                        # Generic syslog system message
                                        event_type = "SYSTEM"
                                        summary = f"{process}: {message[:120]}"
                                        # If process is sshd/sudo but message pattern was unclassified, mark as PARTIAL
                                        if "sshd" in process or "sudo" in process or "auth" in process:
                                            parsing_status = "PARTIAL"
                                            warnings.append(f"Security daemon message format partially matched: {message[:60]}")

        # If timestamp is ambiguous or unresolved, degrade overall parsing status to AMBIGUOUS or PARTIAL
        if time_status == "AMBIGUOUS":
            parsing_status = "AMBIGUOUS"

        return ParsedRecord(
            line_number=line_number,
            raw_text=line_text,
            parsing_status=parsing_status,
            raw_timestamp=raw_timestamp_str,
            parsed_datetime=parsed_dt,
            timezone_offset_str=timezone_assumption,
            time_status=time_status,
            time_assumptions=time_assumptions,
            event_type=event_type,
            hostname=hostname,
            process_name=process,
            pid=pid,
            username=username,
            source_ip=source_ip,
            source_port=source_port,
            summary=summary,
            full_message=message,
            warnings=warnings,
            extracted_data=extracted
        )
