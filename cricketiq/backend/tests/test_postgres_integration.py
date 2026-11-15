"""PostgreSQL Integration Tests for CricketIQ.

Executed in CI or when a live PostgreSQL instance is configured via TEST_POSTGRES_DSN.
Gracefully skipped when running in standard local development without an external database service.
"""

import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from cricketiq.backend.app.database.connection import Base
from cricketiq.backend.app.database.models import (
    SourceDocument, DocumentAuthority, DocumentType, ScopeLevel,
    CricketFormat, GenderCategory, DocumentStatus
)
from cricketiq.backend.app.database.repository import CricketIQRepository

POSTGRES_DSN = os.getenv("TEST_POSTGRES_DSN") or os.getenv("POSTGRES_DATABASE_URL")


@pytest.mark.skipif(not POSTGRES_DSN, reason="Skipped: No PostgreSQL DSN configured (local zero-external-service mode).")
def test_postgres_schema_creation_and_crud():
    engine = create_engine(POSTGRES_DSN)
    Base.metadata.create_all(bind=engine)

    session = Session(bind=engine)
    try:
        repo = CricketIQRepository(session)
        doc = SourceDocument(
            id="ICC_TEST_PG_INTEGRATION",
            publisher=DocumentAuthority.ICC,
            title="PostgreSQL Integration Test Document",
            document_type=DocumentType.PLAYING_CONDITIONS,
            scope_level=ScopeLevel.FORMAT_PC,
            format=CricketFormat.TEST,
            category=GenderCategory.MENS,
            edition="October 2026",
            official_url="https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions",
            sha256="9" * 64,
            status=DocumentStatus.ACTIVE
        )
        saved = repo.upsert_source_document(doc)
        assert saved.id == doc.id

        fetched = repo.get_document(doc.id)
        assert fetched is not None
        assert fetched.title == doc.title
    finally:
        session.rollback()
        session.close()
