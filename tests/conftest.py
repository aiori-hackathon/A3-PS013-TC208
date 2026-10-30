import os
import shutil
import tempfile
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.config import settings
from app.database import Base, get_db
from app.main import app

@pytest.fixture(scope="session")
def test_temp_dir():
    temp_dir = tempfile.TemporaryDirectory()
    yield Path(temp_dir.name)
    try:
        temp_dir.cleanup()
    except Exception:
        pass

@pytest.fixture(scope="function")
def db_session(test_temp_dir):
    # Isolated SQLite database in temp directory for test repeatability
    test_db_path = test_temp_dir / f"test_{os.urandom(4).hex()}.db"
    test_db_url = f"sqlite:///{test_db_path}"
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Override storage directory to temp directory for test isolation
    orig_evidence_dir = settings.EVIDENCE_DIR
    orig_reports_dir = settings.REPORTS_DIR
    settings.EVIDENCE_DIR = test_temp_dir / "evidence"
    settings.REPORTS_DIR = test_temp_dir / "reports"
    settings.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    yield session

    session.close()
    engine.dispose()
    settings.EVIDENCE_DIR = orig_evidence_dir
    settings.REPORTS_DIR = orig_reports_dir

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
