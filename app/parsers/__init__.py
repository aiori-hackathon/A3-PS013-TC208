from app.parsers.base import BaseLogParser, ParsedRecord
from app.parsers.auth_log import LinuxAuthParser
from app.parsers.nginx_access import NginxAccessParser

PARSER_REGISTRY = {
    "linux_auth": LinuxAuthParser(),
    "nginx_access": NginxAccessParser(),
}

def get_parser(parser_name: str) -> BaseLogParser:
    if parser_name not in PARSER_REGISTRY:
        raise ValueError(f"Unknown parser '{parser_name}'. Supported parsers: {list(PARSER_REGISTRY.keys())}")
    return PARSER_REGISTRY[parser_name]

__all__ = ["BaseLogParser", "ParsedRecord", "LinuxAuthParser", "NginxAccessParser", "PARSER_REGISTRY", "get_parser"]
