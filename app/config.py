import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "TraceLens"
    APP_VERSION: str = "1.0.0"
    TAGLINE: str = "Trace evidence. Show uncertainty. Make review accountable."
    TEAM_NAME: str = "Threat Tracers"
    PROBLEM_STATEMENT: str = "A3-PS013-TC208"
    ENVIRONMENT: str = "Demo / Evaluation"
    
    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    
    # On Vercel serverless, the filesystem outside /tmp is read-only
    IS_VERCEL: bool = bool(os.environ.get("VERCEL"))
    STORAGE_DIR: Path = Path("/tmp/storage") if IS_VERCEL else BASE_DIR / "storage"
    EVIDENCE_DIR: Path = STORAGE_DIR / "evidence"
    REPORTS_DIR: Path = STORAGE_DIR / "reports"
    SAMPLE_DATA_DIR: Path = BASE_DIR / "sample-data"
    
    # Database
    DATABASE_URL: str = f"sqlite:///{STORAGE_DIR / 'tracelens.db'}"
    
    # Defaults and Limits
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    DEFAULT_TIMEZONE: str = "UTC"
    DEFAULT_UNCERTAINTY_MARGIN_SECONDS: float = 1.0
    DEFAULT_SYSLOG_YEAR: int = 2026
    
    # Server config
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Ensure directories exist
settings.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
