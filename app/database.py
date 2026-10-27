from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

# Enable SQLite foreign key constraint enforcement
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
