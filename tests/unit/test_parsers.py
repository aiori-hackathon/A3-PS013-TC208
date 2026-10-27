import pytest
from app.parsers.auth_log import LinuxAuthParser
from app.parsers.nginx_access import NginxAccessParser

def test_auth_parser_failed_password_invalid_user():
    parser = LinuxAuthParser()
    line = "Oct 27 10:30:01 host01 sshd[1234]: Failed password for invalid user admin from 192.0.2.10 port 52100 ssh2"
    rec = parser.parse_line(1, line, timezone_assumption="UTC", default_year=2026)

    assert rec.parsing_status == "PARSED"
    assert rec.event_type == "AUTH_FAILURE"
    assert rec.username == "admin"
    assert rec.source_ip == "192.0.2.10"
    assert rec.source_port == 52100
    assert rec.hostname == "host01"
    assert rec.process_name == "sshd"
    assert rec.pid == "1234"
    assert rec.time_status == "INFERRED_OFFSET"
    assert "Year inferred as 2026" in (rec.time_assumptions or "")

def test_auth_parser_accepted_publickey():
    parser = LinuxAuthParser()
    line = "Oct 27 10:30:08 host01 sshd[1234]: Accepted publickey for analyst from 192.0.2.20 port 52110 ssh2"
    rec = parser.parse_line(2, line, timezone_assumption="UTC", default_year=2026)

    assert rec.parsing_status == "PARSED"
    assert rec.event_type == "AUTH_SUCCESS"
    assert rec.username == "analyst"
    assert rec.source_ip == "192.0.2.20"
    assert rec.source_port == 52110

def test_auth_parser_malformed_and_blank_lines():
    parser = LinuxAuthParser()
    blank_rec = parser.parse_line(3, "   \n")
    assert blank_rec.parsing_status == "UNPARSED"
    assert "Blank line" in blank_rec.warnings[0]

    garbage_rec = parser.parse_line(4, "This is not a syslog log line at all!")
    assert garbage_rec.parsing_status == "UNPARSED"

def test_nginx_parser_standard_combined():
    parser = NginxAccessParser()
    line = '192.0.2.10 - - [27/Oct/2026:10:30:01 +0000] "GET /login HTTP/1.1" 401 612 "-" "Mozilla/5.0"'
    rec = parser.parse_line(1, line)

    assert rec.parsing_status == "PARSED"
    assert rec.source_ip == "192.0.2.10"
    assert rec.http_method == "GET"
    assert rec.http_target == "/login"
    assert rec.http_protocol == "HTTP/1.1"
    assert rec.http_status == 401
    assert rec.response_bytes == 612
    assert rec.time_status == "EXACT_OFFSET"
    assert rec.timezone_offset_str == "+0000"
    assert rec.event_type == "HTTP_AUTH_FAILURE"

def test_nginx_parser_quoted_fields_and_username():
    parser = NginxAccessParser()
    line = '192.0.2.20 - analyst [27/Oct/2026:10:30:08 +0000] "POST /api/auth?source=web HTTP/1.1" 200 128 "https://internal.sec/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"'
    rec = parser.parse_line(2, line)

    assert rec.parsing_status == "PARSED"
    assert rec.username == "analyst"
    assert rec.http_method == "POST"
    assert rec.http_target == "/api/auth?source=web"
    assert rec.http_status == 200
    assert rec.user_agent == "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

def test_nginx_parser_malformed_line():
    parser = NginxAccessParser()
    malformed = '192.0.2.10 - - [27/Oct/2026:10:30:01 +0000] "GET /unclosed-quote 401'
    rec = parser.parse_line(3, malformed)
    assert rec.parsing_status in ("PARTIAL", "UNPARSED")
