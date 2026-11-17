#!/usr/bin/env python3
"""Safe Database Reconciliation & Staging Promotion Tool for CricketIQ (Phase 6 Gate 2).

Provides safe, two-phase, reproducible reconciliation between canonical normalized
corpus JSON records (data/corpus/clauses/) and SQLite persistent storage (data/cricketiq.db).

Usage:
  # 1. Non-destructive Dry Run (Default)
  python scripts/reconcile_database.py --dry-run

  # 2. Build Staging Database with Verified Backup
  python scripts/reconcile_database.py --build-staging --confirm-staging

  # 3. Atomically Promote Staging to Active
  python scripts/reconcile_database.py --promote-staging --confirm-promote
"""

from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import Session
from cricketiq.backend.app.database.connection import create_db_engine
from cricketiq.backend.app.database.orm_models import Base
from cricketiq.backend.app.database.models import (
    SourceDocument, RuleClause, DocumentRelationship, DocumentAuthority,
    DocumentType, DocumentStatus, CricketFormat, GenderCategory, ScopeLevel,
    ApplicabilityBasis, RelationshipType, RegulatoryRole
)
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.retrieval.sparse.sqlite_fts import SQLiteFTSSearchProvider
from cricketiq.backend.app.retrieval.dense.embedding_provider import LocalDeterministicEmbeddingProvider
from cricketiq.backend.app.retrieval.dense.embedding_store import EmbeddingStore

ACTIVE_DB_PATH = PROJECT_ROOT / "data" / "cricketiq.db"
STAGING_DB_PATH = PROJECT_ROOT / "data" / "cricketiq_staging.db"
BACKUP_DIR = PROJECT_ROOT / "data" / "backups"
CANONICAL_CLAUSES_DIR = PROJECT_ROOT / "data" / "corpus" / "clauses"
MANIFEST_PATH = PROJECT_ROOT / "data" / "sources" / "manifests" / "raw_manifest.json"
LOCK_FILE_PATH = PROJECT_ROOT / "data" / "reconcile.lock"

DEVANAGARI_REGEX = re.compile(r"[\u0900-\u097F]")


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 digest of file."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_canonical_clauses() -> Dict[str, Dict[str, Any]]:
    """Load all canonical normalized clause records from JSON files.
    
    When duplicate IDs occur in corpus files (e.g. TOC/header lines vs substantive clauses),
    deduplicates deterministically by selecting the substantive clause (longest original_text).
    """
    canonical_map: Dict[str, Dict[str, Any]] = {}
    if not CANONICAL_CLAUSES_DIR.exists():
        raise FileNotFoundError(f"Canonical clauses directory missing: {CANONICAL_CLAUSES_DIR}")

    for jf in sorted(CANONICAL_CLAUSES_DIR.glob("*_clauses.json")):
        with open(jf, "r", encoding="utf-8") as f:
            items = json.load(f)
        for item in items:
            cid = item["id"]
            if cid in canonical_map:
                prev = canonical_map[cid]
                prev_len = len(prev.get("original_text", "") or "")
                new_len = len(item.get("original_text", "") or "")
                if new_len > prev_len:
                    canonical_map[cid] = item
            else:
                canonical_map[cid] = item

    return canonical_map


# -----------------------------------------------------------------------------
# 1. Dry Run Mode
# -----------------------------------------------------------------------------

def run_dry_run() -> None:
    print("=" * 90)
    print("CRICKETIQ DATABASE RECONCILIATION — NON-DESTRUCTIVE DRY RUN")
    print("=" * 90)

    if not ACTIVE_DB_PATH.exists():
        print(f"ERROR: Active database not found at {ACTIVE_DB_PATH}")
        sys.exit(1)

    # 1. Load Canonical Map
    canonical_map = load_canonical_clauses()
    canonical_ids = set(canonical_map.keys())
    print(f"Loaded {len(canonical_map):,} canonical clauses from {CANONICAL_CLAUSES_DIR}")

    # 2. Inspect Active Database
    conn = sqlite3.connect(f"file:{ACTIVE_DB_PATH}?mode=ro", uri=True)
    c = conn.cursor()

    db_rows = c.execute("SELECT id, source_document_id, original_text FROM rule_clauses").fetchall()
    db_id_map = {row[0]: (row[1], row[2]) for row in db_rows}
    db_ids = set(db_id_map.keys())

    fts_count = c.execute("SELECT count(*) FROM rule_clauses_fts").fetchone()[0]
    emb_count = c.execute("SELECT count(*) FROM clause_embeddings").fetchone()[0]
    integ = c.execute("PRAGMA integrity_check").fetchall()
    fk = c.execute("PRAGMA foreign_key_check").fetchall()

    conn.close()

    db_sha256 = compute_file_sha256(ACTIVE_DB_PATH)
    db_size = ACTIVE_DB_PATH.stat().st_size

    print(f"\nActive Database State:")
    print(f"  Path:       {ACTIVE_DB_PATH}")
    print(f"  Size:       {db_size:,} bytes ({round(db_size / (1024*1024), 2)} MB)")
    print(f"  SHA-256:    {db_sha256}")
    print(f"  Integrity:  {integ[0][0] if integ else 'UNKNOWN'}")
    print(f"  FK Errors:  {len(fk)}")
    print(f"  Relational: {len(db_ids):,} rows")
    print(f"  FTS5 Rows:  {fts_count:,} rows")
    print(f"  Embeddings: {emb_count:,} rows")

    # 3. Discrepancy Categorization
    to_remove = db_ids - canonical_ids
    to_add = canonical_ids - db_ids
    common = db_ids & canonical_ids

    # Classify removals
    stale_hindi = []
    stale_appendix = []
    stale_other = []

    for cid in to_remove:
        doc_id, text = db_id_map[cid]
        if DEVANAGARI_REGEX.search(text):
            stale_hindi.append(cid)
        elif ":2." in cid or ":3." in cid or ":1." in cid:
            # Check if an APP_ clause exists in canonical
            prefix, clause_num = cid.split(":", 1)
            matching_app = any(c.startswith(f"{prefix}:APP_") and c.endswith(f":{clause_num}") for c in canonical_ids)
            if matching_app or "ADD" not in prefix:
                stale_appendix.append(cid)
            else:
                stale_other.append(cid)
        else:
            stale_other.append(cid)

    print("\n" + "-" * 90)
    print("RECONCILIATION DELTA BREAKDOWN")
    print("-" * 90)
    print(f"Relational Rows in DB:           {len(db_ids):,}")
    print(f"Canonical Clauses in Corpus:     {len(canonical_ids):,}")
    print(f"Net Row Delta to Purge:          {len(to_remove) - len(to_add):,} rows (Total DB: {len(db_ids)} -> Target: {len(canonical_ids)})")
    print(f"\nRows to Remove from DB ({len(to_remove):,} rows):")
    print(f"  1. Stale Devanagari Hindi rows (MCC_LAWS_2022):     {len(stale_hindi):,}")
    print(f"  2. Stale un-namespaced duplicate appendix rows:    {len(stale_appendix):,}")
    print(f"  3. Stale legacy extraction rows:                   {len(stale_other):,}")
    print(f"\nRows to Add from Canonical Corpus ({len(to_add):,} rows):")
    print(f"  New canonical appendix/definition clauses in JSON:  {len(to_add):,}")
    print(f"\nCommon Retained Clauses (Preserved):                {len(common):,}")

    if stale_hindi:
        print(f"\nSample Stale Hindi Rows to Purge:")
        for cid in sorted(stale_hindi)[:5]:
            print(f"  - {cid}")
    if stale_appendix:
        print(f"\nSample Stale Appendix Duplicates to Purge:")
        for cid in sorted(stale_appendix)[:5]:
            print(f"  - {cid}")
    if to_add:
        print(f"\nSample New Canonical Clauses to Add:")
        for cid in sorted(to_add)[:5]:
            print(f"  - {cid}")

    print("\n" + "=" * 90)
    print("EXPECTED POST-RECONCILIATION STATE (TARGET INVARIANTS)")
    print("=" * 90)
    print(f"Relational Clauses (`rule_clauses`):      {len(canonical_ids):,} rows (Exactly matches canonical corpus)")
    print(f"FTS5 Search Index (`rule_clauses_fts`):   {len(canonical_ids):,} rows (100% 1-to-1 sync)")
    print(f"Vector Embeddings (`clause_embeddings`): {len(canonical_ids):,} rows (Template v1, Model local-deterministic-v1)")
    print(f"Stale Foreign Language Rows:             0 rows")
    print(f"Duplicate Un-namespaced Appendices:      0 rows")
    print(f"\nDry run complete. No modifications were made to {ACTIVE_DB_PATH}.")
    print("To execute a safe staging build and validation, run:")
    print("  python scripts/reconcile_database.py --build-staging --confirm-staging")


# -----------------------------------------------------------------------------
# 2. Build Staging Database
# -----------------------------------------------------------------------------

def run_build_staging(confirm: bool) -> None:
    print("=" * 90)
    print("CRICKETIQ DATABASE RECONCILIATION — BUILD STAGING DATABASE")
    print("=" * 90)

    if not confirm:
        print("ERROR: Staging build requires explicit confirmation flag: --confirm-staging")
        sys.exit(1)

    if not ACTIVE_DB_PATH.exists():
        print(f"ERROR: Active database not found at {ACTIVE_DB_PATH}")
        sys.exit(1)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"cricketiq_backup_{timestamp}.db"

    # Step 1: Online SQLite Backup
    print(f"\n[Step 1/6] Creating immutable verified backup of active database...")
    print(f"  Source: {ACTIVE_DB_PATH}")
    print(f"  Backup: {backup_file}")

    src_conn = sqlite3.connect(ACTIVE_DB_PATH)
    dst_conn = sqlite3.connect(backup_file)
    src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()

    # Verify Backup Integrity
    test_conn = sqlite3.connect(backup_file)
    b_integ = test_conn.cursor().execute("PRAGMA integrity_check").fetchall()
    b_fk = test_conn.cursor().execute("PRAGMA foreign_key_check").fetchall()
    test_conn.close()

    if not b_integ or b_integ[0][0] != "ok" or len(b_fk) > 0:
        print(f"FATAL: Backup integrity verification failed: {b_integ}, FK errors: {b_fk}")
        if backup_file.exists():
            backup_file.unlink()
        sys.exit(1)

    active_sha256 = compute_file_sha256(ACTIVE_DB_PATH)
    backup_sha256 = compute_file_sha256(backup_file)
    print(f"  Active DB SHA-256: {active_sha256}")
    print(f"  Backup SHA-256:    {backup_sha256}")
    print("  Backup verified successfully (PRAGMA integrity_check = ok, 0 foreign key errors).")

    # Step 2: Initialize Clean Staging Database
    print(f"\n[Step 2/6] Initializing clean staging database at {STAGING_DB_PATH}...")
    if STAGING_DB_PATH.exists():
        STAGING_DB_PATH.unlink()

    staging_engine = create_db_engine(f"sqlite:///{STAGING_DB_PATH}")
    Base.metadata.create_all(bind=staging_engine)
    staging_session = Session(bind=staging_engine)
    staging_repo = CricketIQRepository(staging_session)

    # Step 3: Register Official Source Documents with Explicit Regulatory Role
    print(f"\n[Step 3/6] Populating authoritative source documents and relationships...")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for m in manifest:
        fmt = (CricketFormat.TEST if m["format"] == "Test" else
               CricketFormat.ODI if m["format"] == "ODI" else
               CricketFormat.T20I if m["format"] == "T20I" else CricketFormat.GENERAL)
        cat = (GenderCategory.MENS if m["category"] == "Men's" else
               GenderCategory.WOMENS if m["category"] == "Women's" else GenderCategory.UNIVERSAL)

        doc_id = m["source_document_id"]
        if "changes" in doc_id.lower():
            role = RegulatoryRole.EXPLANATORY_GUIDANCE
            scope = ScopeLevel.LAWS_BASELINE
            auth = DocumentAuthority.MCC
            dtype = DocumentType.AMENDMENT
        elif doc_id.startswith("MCC"):
            role = RegulatoryRole.NORMATIVE_LAWS_BASELINE
            scope = ScopeLevel.LAWS_BASELINE
            auth = DocumentAuthority.MCC
            dtype = DocumentType.LAW
        elif "ADD" in doc_id:
            role = RegulatoryRole.NORMATIVE_ADDENDUM
            scope = ScopeLevel.ADDENDUM
            auth = DocumentAuthority.ICC
            dtype = DocumentType.ADDENDUM
        elif "WTC" in doc_id:
            role = RegulatoryRole.NORMATIVE_COMPETITION_REGULATION
            scope = ScopeLevel.COMPETITION_PC
            auth = DocumentAuthority.ICC
            dtype = DocumentType.COMPETITION_REGULATIONS
        else:
            role = RegulatoryRole.NORMATIVE_FORMAT_PC
            scope = ScopeLevel.FORMAT_PC
            auth = DocumentAuthority.ICC
            dtype = DocumentType.PLAYING_CONDITIONS

        basis = (ApplicabilityBasis.MATCH_DATE if m.get("applicability_basis") == "match_date" else
                 ApplicabilityBasis.COMPETITION_START_DATE if m.get("applicability_basis") == "competition_start_date" else
                 ApplicabilityBasis.SERIES_START_DATE)

        doc = SourceDocument(
            id=doc_id,
            publisher=auth,
            title=m["title"],
            document_type=dtype,
            scope_level=scope,
            regulatory_role=role,
            format=fmt,
            category=cat,
            edition=m["edition"],
            effective_from=m.get("effective_date", "2026-10-01"),
            applicability_basis=basis,
            official_url=m["official_url"],
            file_path=m.get("relative_path"),
            sha256=m["sha256"],
            status=DocumentStatus.ACTIVE
        )
        staging_repo.upsert_source_document(doc)
        print(f"  -> SourceDocument: {doc.id:30} [{doc.regulatory_role.value}]")

    # Register Relationships
    relationships = [
        ("ICC_TEST_MEN_2026", "MCC_LAWS_2026", RelationshipType.INCORPORATES),
        ("ICC_ODI_MEN_2026", "MCC_LAWS_2026", RelationshipType.INCORPORATES),
        ("ICC_T20I_MEN_2026", "MCC_LAWS_2026", RelationshipType.INCORPORATES),
        ("ICC_TEST_WOMEN_2026", "MCC_LAWS_2026", RelationshipType.INCORPORATES),
        ("ICC_ODI_WOMEN_2026", "MCC_LAWS_2026", RelationshipType.INCORPORATES),
        ("ICC_T20I_WOMEN_2026", "MCC_LAWS_2026", RelationshipType.INCORPORATES),
        ("ICC_T20I_MEN_ADD_2026", "ICC_T20I_MEN_2026", RelationshipType.SUPPLEMENTS),
        ("ICC_WTC_2025_2027_PC", "ICC_TEST_MEN_2026", RelationshipType.MODIFIES),
        ("MCC_LAWS_2026", "MCC_LAWS_2022", RelationshipType.SUPERSEDES),
        ("MCC_CHANGES_EXPLAINED_2026", "MCC_LAWS_2026", RelationshipType.SUPPLEMENTS)
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
        staging_repo.add_relationship(rel)

    # Step 4: Ingest Canonical Clauses
    print(f"\n[Step 4/6] Ingesting canonical clauses from {CANONICAL_CLAUSES_DIR}...")
    canonical_map = load_canonical_clauses()
    clause_objs = [RuleClause(**c_dict) for c_dict in canonical_map.values()]
    ingested_count = staging_repo.upsert_clauses(clause_objs)
    print(f"  Successfully upserted {ingested_count:,} canonical clauses.")

    # Step 5: Build Deterministic Search Indexes
    print(f"\n[Step 5/6] Building deterministic SQLite FTS5 and Vector Embedding indexes...")
    fts_provider = SQLiteFTSSearchProvider(staging_repo)
    fts_indexed = fts_provider.rebuild_index()
    print(f"  -> SQLite FTS5 index built: {fts_indexed:,} rows.")

    embedder = LocalDeterministicEmbeddingProvider(dimension=384)
    emb_store = EmbeddingStore(repository=staging_repo, provider=embedder)
    emb_indexed = emb_store.build_all_embeddings()
    print(f"  -> Clause embeddings built: {emb_indexed:,} vectors (model={embedder.model_name}, dim={embedder.dimension}).")

    staging_session.close()

    # Step 6: Validate Staging Database
    print(f"\n[Step 6/6] Executing comprehensive integrity verification on staging database...")
    staging_conn = sqlite3.connect(STAGING_DB_PATH)
    s_cur = staging_conn.cursor()
    s_integ = s_cur.execute("PRAGMA integrity_check").fetchall()
    s_fk = s_cur.execute("PRAGMA foreign_key_check").fetchall()
    s_rel_count = s_cur.execute("SELECT count(*) FROM rule_clauses").fetchone()[0]
    s_fts_count = s_cur.execute("SELECT count(*) FROM rule_clauses_fts").fetchone()[0]
    s_emb_count = s_cur.execute("SELECT count(*) FROM clause_embeddings").fetchone()[0]
    s_hindi_count = s_cur.execute("SELECT count(*) FROM rule_clauses WHERE source_document_id = 'MCC_LAWS_2022' AND original_text GLOB '*[ऀ-ॿ]*'").fetchone()[0]
    staging_conn.close()

    staging_sha256 = compute_file_sha256(STAGING_DB_PATH)
    staging_size = STAGING_DB_PATH.stat().st_size

    print(f"\nStaging Validation Results:")
    print(f"  Path:                    {STAGING_DB_PATH}")
    print(f"  Size:                    {staging_size:,} bytes ({round(staging_size / (1024*1024), 2)} MB)")
    print(f"  SHA-256:                 {staging_sha256}")
    print(f"  Integrity Check:         {s_integ[0][0] if s_integ else 'FAILED'}")
    print(f"  Foreign Key Errors:      {len(s_fk)}")
    print(f"  Relational Clauses:      {s_rel_count:,} (Expected: {len(canonical_map):,})")
    print(f"  FTS5 Clauses:            {s_fts_count:,} (Expected: {len(canonical_map):,})")
    print(f"  Vector Embeddings:       {s_emb_count:,} (Expected: {len(canonical_map):,})")
    print(f"  Stale Devanagari Rows:   {s_hindi_count}")

    if s_rel_count != len(canonical_map) or s_fts_count != len(canonical_map) or s_emb_count != len(canonical_map) or s_hindi_count > 0:
        print("FATAL: Staging validation failed. Staging database has mismatched counts or residual contaminated rows.")
        sys.exit(1)

    # Save Promotion Manifest
    manifest_data = {
        "timestamp": timestamp,
        "active_db_backup": str(backup_file.resolve()),
        "active_db_sha256_before": active_sha256,
        "staging_db_path": str(STAGING_DB_PATH.resolve()),
        "staging_db_sha256": staging_sha256,
        "staging_db_size_bytes": staging_size,
        "canonical_clauses_count": len(canonical_map),
        "relational_rows": s_rel_count,
        "fts_rows": s_fts_count,
        "embedding_rows": s_emb_count,
        "integrity_check": s_integ[0][0] if s_integ else "FAILED",
        "validation_passed": True
    }
    manifest_file = BACKUP_DIR / f"staging_manifest_{timestamp}.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print(f"\nPromotion manifest written to: {manifest_file}")
    print("\n" + "=" * 90)
    print("STAGING BUILD AND VALIDATION SUCCESSFUL!")
    print("=" * 90)
    print("Active database was NOT modified. To promote staging to active, run:")
    print("  python scripts/reconcile_database.py --promote-staging --confirm-promote")


# -----------------------------------------------------------------------------
# 3. Promote Staging Database
# -----------------------------------------------------------------------------

def run_promote_staging(confirm: bool) -> None:
    print("=" * 90)
    print("CRICKETIQ DATABASE RECONCILIATION — PROMOTE STAGING DATABASE")
    print("=" * 90)

    if not confirm:
        print("ERROR: Promotion requires explicit confirmation flag: --confirm-promote")
        sys.exit(1)

    if not STAGING_DB_PATH.exists():
        print(f"ERROR: Staging database not found at {STAGING_DB_PATH}. Run --build-staging first.")
        sys.exit(1)

    canonical_map = load_canonical_clauses()
    expected_count = len(canonical_map)

    # Pre-promotion check of staging
    s_conn = sqlite3.connect(STAGING_DB_PATH)
    s_count = s_conn.cursor().execute("SELECT count(*) FROM rule_clauses").fetchone()[0]
    s_integ = s_conn.cursor().execute("PRAGMA integrity_check").fetchall()
    s_conn.close()

    if s_count != expected_count or not s_integ or s_integ[0][0] != "ok":
        print(f"FATAL: Pre-promotion check failed on {STAGING_DB_PATH}. Count={s_count}, expected={expected_count}")
        sys.exit(1)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    pre_promote_backup = BACKUP_DIR / f"cricketiq_pre_promote_{timestamp}.db"

    print(f"\n[Step 1/3] Preserving current active database to {pre_promote_backup}...")
    if ACTIVE_DB_PATH.exists():
        shutil.copy2(ACTIVE_DB_PATH, pre_promote_backup)
        print(f"  Active DB preserved successfully (SHA-256: {compute_file_sha256(pre_promote_backup)}).")

    # Step 2: Atomic Swap
    print(f"\n[Step 2/3] Performing atomic swap of staging database into active path...")
    temp_old = ACTIVE_DB_PATH.with_suffix(".old")
    if temp_old.exists():
        temp_old.unlink()

    try:
        # On Windows, replace works atomically if destination is replaced
        if ACTIVE_DB_PATH.exists():
            ACTIVE_DB_PATH.replace(temp_old)
        STAGING_DB_PATH.replace(ACTIVE_DB_PATH)
        if temp_old.exists():
            temp_old.unlink()
        print(f"  Atomic swap complete: {STAGING_DB_PATH.name} -> {ACTIVE_DB_PATH.name}")
    except PermissionError as e:
        print(f"\nFATAL: Failed to replace active database due to file lock: {e}")
        print("A process (e.g. uvicorn backend or background task) currently holds a lock on cricketiq.db.")
        print("Please stop the uvicorn process, then re-run the promote command.")
        if temp_old.exists() and not ACTIVE_DB_PATH.exists():
            temp_old.replace(ACTIVE_DB_PATH)
        sys.exit(1)

    # Step 3: Post-Promotion Verification
    print(f"\n[Step 3/3] Verifying active database post-promotion...")
    active_conn = sqlite3.connect(ACTIVE_DB_PATH)
    ac = active_conn.cursor()
    a_integ = ac.execute("PRAGMA integrity_check").fetchall()
    a_fk = ac.execute("PRAGMA foreign_key_check").fetchall()
    a_rel = ac.execute("SELECT count(*) FROM rule_clauses").fetchone()[0]
    a_fts = ac.execute("SELECT count(*) FROM rule_clauses_fts").fetchone()[0]
    a_emb = ac.execute("SELECT count(*) FROM clause_embeddings").fetchone()[0]
    active_conn.close()

    active_sha = compute_file_sha256(ACTIVE_DB_PATH)
    print(f"  Post-Promotion State:")
    print(f"    Path:               {ACTIVE_DB_PATH}")
    print(f"    SHA-256:            {active_sha}")
    print(f"    Integrity Check:    {a_integ[0][0] if a_integ else 'FAILED'}")
    print(f"    Foreign Key Errors: {len(a_fk)}")
    print(f"    Relational Clauses: {a_rel:,} (Target: {expected_count:,})")
    print(f"    FTS5 Search Rows:   {a_fts:,} (Target: {expected_count:,})")
    print(f"    Vector Embeddings:  {a_emb:,} (Target: {expected_count:,})")

    if a_rel != expected_count or a_fts != expected_count or a_emb != expected_count or not a_integ or a_integ[0][0] != "ok":
        print(f"\nCRITICAL: Post-promotion verification failed! Rolling back to {pre_promote_backup}...")
        shutil.copy2(pre_promote_backup, ACTIVE_DB_PATH)
        print("Rollback complete. Active database restored to pre-promotion state.")
        sys.exit(1)

    print("\n" + "=" * 90)
    print("PROMOTION COMPLETE & VERIFIED SUCCESSFULLY!")
    print("=" * 90)
    print(f"Active database at {ACTIVE_DB_PATH} is now fully reconciled with canonical corpus ({expected_count:,} unique clauses).")
    print(f"Backup preserved at: {pre_promote_backup}")


# -----------------------------------------------------------------------------
# Main CLI Entrypoint
# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="CricketIQ Database Reconciliation Tool")
    parser.add_argument("--dry-run", action="store_true", help="Execute non-destructive reconciliation dry-run (Default)")
    parser.add_argument("--build-staging", action="store_true", help="Build staging database from canonical corpus with backup")
    parser.add_argument("--confirm-staging", action="store_true", help="Explicit confirmation to build staging database")
    parser.add_argument("--promote-staging", action="store_true", help="Atomically promote staging database to active path")
    parser.add_argument("--confirm-promote", action="store_true", help="Explicit confirmation to promote staging database")

    args = parser.parse_args()

    if args.promote_staging:
        run_promote_staging(confirm=args.confirm_promote)
    elif args.build_staging:
        run_build_staging(confirm=args.confirm_staging)
    else:
        run_dry_run()


if __name__ == "__main__":
    main()
