"""Database connection, session management, and capability detection for CricketIQ.

Supports dual-mode persistence:
- Local development & testing: SQLite with FTS5 detection and thread safety
- Production: PostgreSQL with pgvector and full-text search
"""

from __future__ import annotations
import os
import sqlite3
from pathlib import Path
from typing import Generator, Optional
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session

Base = declarative_base()


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        curr = Path(__file__).resolve().parent
        found_path = None
        for _ in range(6):
            cand = curr / "data" / "cricketiq.db"
            if cand.exists():
                found_path = cand
                break
            curr = curr.parent
        if not found_path:
            root_dir = Path(__file__).resolve().parents[4]
            found_path = root_dir / "data" / "cricketiq.db"
            found_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{found_path}"
    return url


def create_db_engine(db_url: Optional[str] = None):
    url = db_url or get_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    eng = create_engine(
        url,
        connect_args=connect_args,
        echo=os.getenv("DEBUG", "false").lower() == "true"
    )

    if url.startswith("sqlite"):
        @event.listens_for(eng, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return eng


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def check_sqlite_fts5_support(target_engine=None) -> bool:
    """Verify if SQLite runtime has FTS5 module compiled and enabled."""
    eng = target_engine or engine
    if not str(eng.url).startswith("sqlite"):
        return False
    try:
        with eng.connect() as conn:
            # Check compile options
            options = conn.execute(text("PRAGMA compile_options")).fetchall()
            opt_set = {row[0].upper() for row in options}
            if "ENABLE_FTS5" in opt_set or "FTS5" in opt_set:
                return True
            # Fallback direct probe
            conn.execute(text("CREATE TEMP TABLE _fts5_probe USING fts5(probe);"))
            conn.execute(text("DROP TABLE _fts5_probe;"))
            return True
    except Exception:
        return False


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine=None):
    """Create all database tables."""
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)
