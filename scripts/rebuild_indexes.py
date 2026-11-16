#!/usr/bin/env python3
"""Atomic Database and Index Rebuild Script for CricketIQ.

Builds persistent SQLite database and search indexes:
1. Populates all 10 SourceDocuments in data/cricketiq.db
2. Establishes official DocumentRelationships (INCORPORATES, MODIFIES, SUPPLEMENTS)
3. Inserts all 8,808 RuleClauses from data/corpus/clauses/
4. Rebuilds SQLite FTS5 index (rule_clauses_fts)
5. Builds persistent clause embeddings via EmbeddingStore using LocalDeterministicEmbeddingProvider
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from sqlalchemy.orm import Session
from cricketiq.backend.app.database.connection import create_db_engine
from cricketiq.backend.app.database.orm_models import Base
from cricketiq.backend.app.database.models import (
    SourceDocument, RuleClause, DocumentRelationship, DocumentAuthority,
    DocumentType, DocumentStatus, CricketFormat, GenderCategory, ScopeLevel,
    ApplicabilityBasis, RelationshipType
)
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.retrieval.sparse.sqlite_fts import SQLiteFTSSearchProvider
from cricketiq.backend.app.retrieval.dense.embedding_provider import LocalDeterministicEmbeddingProvider
from cricketiq.backend.app.retrieval.dense.embedding_store import EmbeddingStore

def main():
    db_path = root_dir / "data" / "cricketiq.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Initializing database at: {db_path}")
    engine = create_db_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    repo = CricketIQRepository(session)

    # 1. Load Manifest
    manifest_path = root_dir / "data" / "sources" / "manifests" / "raw_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 2. Register Source Documents
    print(f"Registering {len(manifest)} source documents...")
    doc_objs = []
    for m in manifest:
        if m["format"] == "Test":
            fmt = CricketFormat.TEST
        elif m["format"] == "ODI":
            fmt = CricketFormat.ODI
        elif m["format"] == "T20I":
            fmt = CricketFormat.T20I
        else:
            fmt = CricketFormat.GENERAL

        if m["category"] == "Men's":
            cat = GenderCategory.MENS
        elif m["category"] == "Women's":
            cat = GenderCategory.WOMENS
        else:
            cat = GenderCategory.UNIVERSAL

        if m["source_document_id"].startswith("MCC"):
            scope = ScopeLevel.LAWS_BASELINE
            auth = DocumentAuthority.MCC
            dtype = DocumentType.LAW
        elif "ADD" in m["source_document_id"]:
            scope = ScopeLevel.ADDENDUM
            auth = DocumentAuthority.ICC
            dtype = DocumentType.ADDENDUM
        elif "WTC" in m["source_document_id"]:
            scope = ScopeLevel.COMPETITION_PC
            auth = DocumentAuthority.ICC
            dtype = DocumentType.COMPETITION_REGULATIONS
        else:
            scope = ScopeLevel.FORMAT_PC
            auth = DocumentAuthority.ICC
            dtype = DocumentType.PLAYING_CONDITIONS

        basis_str = m.get("applicability_basis", "SERIES_START_DATE").lower()
        if basis_str == "series_start_date":
            basis = ApplicabilityBasis.SERIES_START_DATE
        elif basis_str == "match_date":
            basis = ApplicabilityBasis.MATCH_DATE
        elif basis_str == "competition_start_date":
            basis = ApplicabilityBasis.COMPETITION_START_DATE
        else:
            basis = ApplicabilityBasis.SERIES_START_DATE

        doc = SourceDocument(
            id=m["source_document_id"],
            publisher=auth,
            title=m["title"],
            document_type=dtype,
            scope_level=scope,
            format=fmt,
            category=cat,
            edition=m["edition"],
            effective_from=m.get("effective_date", "2026-10-01"),
            applicability_basis=basis,
            official_url=m["official_url"],
            file_path=m["relative_path"],
            sha256=m["sha256"],
            status=DocumentStatus.ACTIVE
        )
        repo.upsert_source_document(doc)
        doc_objs.append(doc)
        print(f"  -> Upserted document: {doc.id}")

    # 3. Register Relationships
    print("\nRegistering document relationships...")
    relationships = [
        ("ICC_TEST_MEN_2026", "MCC_LAWS_2026", RelationshipType.INCORPORATES),
        ("ICC_ODI_MEN_2026", "MCC_LAWS_2026", RelationshipType.INCORPORATES),
        ("ICC_T20I_MEN_2026", "MCC_LAWS_2026", RelationshipType.INCORPORATES),
        ("ICC_TEST_WOMEN_2026", "MCC_LAWS_2026", RelationshipType.INCORPORATES),
        ("ICC_ODI_WOMEN_2026", "MCC_LAWS_2026", RelationshipType.INCORPORATES),
        ("ICC_T20I_WOMEN_2026", "MCC_LAWS_2026", RelationshipType.INCORPORATES),
        ("ICC_T20I_MEN_ADD_2026", "ICC_T20I_MEN_2026", RelationshipType.SUPPLEMENTS),
        ("ICC_WTC_2025_2027_PC", "ICC_TEST_MEN_2026", RelationshipType.MODIFIES),
        ("MCC_LAWS_2026", "MCC_LAWS_2022", RelationshipType.SUPERSEDES)
    ]
    for source_id, target_id, rel_type in relationships:
        rel = DocumentRelationship(
            id=f"{source_id}_{rel_type.value}_{target_id}",
            source_doc_id=source_id,
            target_doc_id=target_id,
            relationship_type=rel_type,
            description=f"{source_id} {rel_type.value} {target_id}",
            review_status="APPROVED"
        )
        repo.add_relationship(rel)
    print(f"  -> Registered {len(relationships)} relationships.")

    # 4. Insert Clauses
    print("\nInserting clauses from normalized corpus...")
    total_clauses = 0
    clauses_dir = root_dir / "data" / "corpus" / "clauses"
    for m in manifest:
        doc_id = m["source_document_id"]
        clause_file = clauses_dir / f"{doc_id}_clauses.json"
        if not clause_file.exists():
            continue
        with open(clause_file, "r", encoding="utf-8") as f:
            raw_clauses = json.load(f)

        clause_objs = [RuleClause(**c) for c in raw_clauses]
        count = repo.upsert_clauses(clause_objs)
        total_clauses += count
        print(f"  -> Upserted {count} clauses for {doc_id}")

    # 5. Build SQLite FTS5 Index
    print("\nRebuilding SQLite FTS5 index...")
    fts = SQLiteFTSSearchProvider(repo)
    fts_count = fts.rebuild_index()
    print(f"  -> FTS5 index rebuilt with {fts_count} indexed clauses.")

    # 6. Build Deterministic Embeddings Store
    print("\nRebuilding persistent vector embeddings...")
    provider = LocalDeterministicEmbeddingProvider(dimension=384)
    store = EmbeddingStore(repository=repo, provider=provider)
    emb_count = store.build_all_embeddings()
    print(f"  -> Embedding store built with {emb_count} vectors (dim={provider.dimension}).")

    session.close()
    print(f"\nAll indexes rebuilt successfully! Database ready at {db_path} ({db_path.stat().st_size:,} bytes).")

if __name__ == "__main__":
    main()
