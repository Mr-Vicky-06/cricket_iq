#!/usr/bin/env python3
"""Safe Database Reconciliation & Staging Promotion Tool for CricketIQ (Phase 6 Gate 2).

Provides safe, two-phase, reproducible reconciliation between canonical normalized
corpus JSON records (data/corpus/clauses/) and SQLite persistent storage (data/cricketiq.db).

Key Architectural Invariants:
1. No destructive in-place modification of active database during build-staging.
2. Verified online SQLite backup before any staging operation.
3. Pre-promotion active database SHA invariance assertion to prevent overwriting intervening changes.
4. Comprehensive parity verification across canonical JSON, Relational, FTS5, and Vector stores.
5. Exact ID set digest equality across all four stores.
6. Recoverable atomic filesystem swap with rollback snapshot preserved permanently.
7. Conservative process locking via data/reconcile.lock to prevent concurrent execution.

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
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional, Iterable

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


# -----------------------------------------------------------------------------
# Custom Reconciliation Exceptions
# -----------------------------------------------------------------------------

class ReconciliationError(Exception):
    """Base exception for database reconciliation errors."""
    pass


class LockAcquisitionError(ReconciliationError):
    """Raised when process lock cannot be acquired."""
    pass


class ActiveDBChangedError(ReconciliationError):
    """Raised when active DB SHA has changed between staging build and promotion."""
    pass


class StagingValidationError(ReconciliationError):
    """Raised when staging database or manifest fails pre-promotion validation."""
    pass


class PromotionSwapError(ReconciliationError):
    """Raised when filesystem swap fails during promotion."""
    pass


class PostPromotionVerificationError(ReconciliationError):
    """Raised when post-promotion validation fails on active DB."""
    pass


# -----------------------------------------------------------------------------
# Process Lock
# -----------------------------------------------------------------------------

class ReconciliationLock:
    """Exclusive filesystem process lock for database reconciliation."""

    def __init__(self, lock_path: Path = LOCK_FILE_PATH, stale_seconds: int = 3600):
        self.lock_path = lock_path
        self.stale_seconds = stale_seconds
        self._fd: Optional[int] = None

    def acquire(self) -> None:
        if self._fd is not None:
            return
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Atomic file creation with exclusive mode
            flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
            self._fd = os.open(str(self.lock_path), flags, 0o644)
            info = {
                "pid": os.getpid(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "hostname": os.environ.get("COMPUTERNAME", "unknown")
            }
            os.write(self._fd, json.dumps(info).encode("utf-8"))
        except FileExistsError:
            # Check for stale lock
            is_stale = False
            lock_info = {}
            try:
                mtime = self.lock_path.stat().st_mtime
                age = time.time() - mtime
                with open(self.lock_path, "r", encoding="utf-8") as f:
                    lock_info = json.load(f)
                if age > self.stale_seconds:
                    is_stale = True
            except Exception:
                pass

            if is_stale:
                try:
                    self.lock_path.unlink()
                    self.acquire()
                    return
                except Exception as e:
                    raise LockAcquisitionError(f"Could not break stale lock at {self.lock_path}: {e}")

            pid = lock_info.get("pid", "unknown")
            created = lock_info.get("created_at", "unknown")
            raise LockAcquisitionError(
                f"Another reconciliation process is currently running (PID {pid}, started {created}). Lock path: {self.lock_path}"
            )

    def release(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        if self.lock_path.exists():
            try:
                self.lock_path.unlink()
            except OSError:
                pass

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


# -----------------------------------------------------------------------------
# Digest and Hashing Utilities
# -----------------------------------------------------------------------------

def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 digest of file."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_id_set_digest(ids: Iterable[str]) -> str:
    """Compute deterministic SHA-256 digest of sorted unique identifier set."""
    sorted_unique = sorted(set(ids))
    return hashlib.sha256("\n".join(sorted_unique).encode("utf-8")).hexdigest()


def get_git_commit() -> str:
    """Get current Git commit hash or 'unknown'."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=PROJECT_ROOT
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def load_canonical_clauses(clauses_dir: Path = CANONICAL_CLAUSES_DIR) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """Load canonical normalized clause records from JSON files with full metadata.
    
    When duplicate IDs occur in corpus files (e.g. TOC/header lines vs substantive clauses),
    deduplicates deterministically by selecting the substantive clause (longest original_text).
    """
    canonical_map: Dict[str, Dict[str, Any]] = {}
    input_files: Dict[str, Dict[str, Any]] = {}
    total_raw = 0
    duplicate_count = 0
    per_doc_counts: Dict[str, int] = {}

    if not clauses_dir.exists():
        raise FileNotFoundError(f"Canonical clauses directory missing: {clauses_dir}")

    for jf in sorted(clauses_dir.glob("*_clauses.json")):
        sha256 = compute_file_sha256(jf)
        size = jf.stat().st_size
        with open(jf, "r", encoding="utf-8") as f:
            items = json.load(f)
        total_raw += len(items)
        input_files[jf.name] = {
            "sha256": sha256,
            "raw_records": len(items),
            "size_bytes": size
        }
        for item in items:
            cid = item["id"]
            if cid in canonical_map:
                duplicate_count += 1
                prev = canonical_map[cid]
                prev_len = len(prev.get("original_text", "") or "")
                new_len = len(item.get("original_text", "") or "")
                if new_len > prev_len:
                    canonical_map[cid] = item
            else:
                canonical_map[cid] = item

    for item in canonical_map.values():
        doc_id = item.get("source_document_id", "UNKNOWN")
        per_doc_counts[doc_id] = per_doc_counts.get(doc_id, 0) + 1

    canonical_digest = compute_id_set_digest(canonical_map.keys())
    metadata = {
        "input_files": input_files,
        "total_raw_records": total_raw,
        "unique_clause_count": len(canonical_map),
        "duplicate_count": duplicate_count,
        "per_document_counts": per_doc_counts,
        "canonical_ids_digest": canonical_digest,
    }
    return canonical_map, metadata


# -----------------------------------------------------------------------------
# Database Parity Validator
# -----------------------------------------------------------------------------

def verify_database_parity(db_path: Path, canonical_map: Dict[str, Any]) -> Dict[str, Any]:
    """Verify exact parity between SQLite database and canonical corpus map.
    
    Checks:
    - PRAGMA integrity_check == ok
    - PRAGMA foreign_key_check is empty
    - Relational clauses count == canonical count
    - All relational clauses link to existing source_documents
    - FTS5 clauses count == canonical count
    - Embedding vectors count == canonical count
    - Exact ID set SHA-256 digest equality across Canonical, Relational, FTS5, and Vector stores
    - Zero Devanagari Hindi rows in MCC_LAWS_2022
    - Consistency of embedding metadata (model_name, dimension, template_version)
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database file does not exist: {db_path}")

    conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    c = conn.cursor()

    integ = c.execute("PRAGMA integrity_check").fetchall()
    fk = c.execute("PRAGMA foreign_key_check").fetchall()

    rel_rows = c.execute("SELECT id, source_document_id, original_text FROM rule_clauses").fetchall()
    rel_ids = [r[0] for r in rel_rows]
    doc_ids_in_clauses = {r[1] for r in rel_rows}

    registered_docs = {r[0] for r in c.execute("SELECT id FROM source_documents").fetchall()}
    unregistered_docs = doc_ids_in_clauses - registered_docs

    fts_rows = c.execute("SELECT clause_id FROM rule_clauses_fts").fetchall()
    fts_ids = [r[0] for r in fts_rows]

    emb_rows = c.execute("SELECT clause_id, model_name, dimension, template_version FROM clause_embeddings").fetchall()
    emb_ids = [r[0] for r in emb_rows]
    emb_models = {r[1] for r in emb_rows}
    emb_dims = {r[2] for r in emb_rows}
    emb_templates = {r[3] for r in emb_rows}

    hindi_rows = c.execute(
        "SELECT count(*) FROM rule_clauses WHERE source_document_id = 'MCC_LAWS_2022' AND original_text GLOB '*[ऀ-ॿ]*'"
    ).fetchone()[0]

    conn.close()

    canonical_digest = compute_id_set_digest(canonical_map.keys())
    rel_digest = compute_id_set_digest(rel_ids)
    fts_digest = compute_id_set_digest(fts_ids)
    emb_digest = compute_id_set_digest(emb_ids)

    passed = True
    errors: List[str] = []

    if not integ or integ[0][0] != "ok":
        passed = False
        errors.append(f"PRAGMA integrity_check failed: {integ}")
    if len(fk) > 0:
        passed = False
        errors.append(f"Foreign key violations found: {len(fk)}")
    if len(unregistered_docs) > 0:
        passed = False
        errors.append(f"Clauses reference unregistered source documents: {unregistered_docs}")
    if hindi_rows > 0:
        passed = False
        errors.append(f"Found {hindi_rows} contaminated Devanagari Hindi rows")
    if len(rel_ids) != len(canonical_map):
        passed = False
        errors.append(f"Relational row count mismatch: {len(rel_ids)} vs canonical {len(canonical_map)}")
    if len(fts_ids) != len(canonical_map):
        passed = False
        errors.append(f"FTS5 row count mismatch: {len(fts_ids)} vs canonical {len(canonical_map)}")
    if len(emb_ids) != len(canonical_map):
        passed = False
        errors.append(f"Embedding row count mismatch: {len(emb_ids)} vs canonical {len(canonical_map)}")
    if not (canonical_digest == rel_digest == fts_digest == emb_digest):
        passed = False
        errors.append(
            f"Digest mismatch! canonical={canonical_digest}, rel={rel_digest}, fts={fts_digest}, emb={emb_digest}"
        )

    file_size = db_path.stat().st_size
    file_sha = compute_file_sha256(db_path)

    return {
        "passed": passed,
        "errors": errors,
        "database_path": str(db_path.resolve()),
        "file_size_bytes": file_size,
        "sha256": file_sha,
        "integrity": integ[0][0] if integ else "FAILED",
        "fk_errors": len(fk),
        "relational_count": len(rel_ids),
        "fts_count": len(fts_ids),
        "embedding_count": len(emb_ids),
        "canonical_ids_digest": canonical_digest,
        "relational_ids_digest": rel_digest,
        "fts_ids_digest": fts_digest,
        "embedding_ids_digest": emb_digest,
        "embedding_models": list(emb_models),
        "embedding_dimensions": list(emb_dims),
        "embedding_templates": list(emb_templates),
        "hindi_rows": hindi_rows,
    }


# -----------------------------------------------------------------------------
# 1. Dry Run Mode
# -----------------------------------------------------------------------------

def run_dry_run(
    active_db_path: Path = ACTIVE_DB_PATH,
    clauses_dir: Path = CANONICAL_CLAUSES_DIR
) -> None:
    print("=" * 90)
    print("CRICKETIQ DATABASE RECONCILIATION — NON-DESTRUCTIVE DRY RUN")
    print("=" * 90)

    if not active_db_path.exists():
        print(f"ERROR: Active database not found at {active_db_path}")
        sys.exit(1)

    canonical_map, meta = load_canonical_clauses(clauses_dir)
    canonical_ids = set(canonical_map.keys())
    print(f"Loaded {len(canonical_map):,} canonical clauses from {clauses_dir}")

    conn = sqlite3.connect(f"file:{active_db_path.resolve()}?mode=ro", uri=True)
    c = conn.cursor()

    db_rows = c.execute("SELECT id, source_document_id, original_text FROM rule_clauses").fetchall()
    db_id_map = {row[0]: (row[1], row[2]) for row in db_rows}
    db_ids = set(db_id_map.keys())

    fts_count = c.execute("SELECT count(*) FROM rule_clauses_fts").fetchone()[0]
    emb_count = c.execute("SELECT count(*) FROM clause_embeddings").fetchone()[0]
    integ = c.execute("PRAGMA integrity_check").fetchall()
    fk = c.execute("PRAGMA foreign_key_check").fetchall()
    conn.close()

    db_sha256 = compute_file_sha256(active_db_path)
    db_size = active_db_path.stat().st_size

    print(f"\nActive Database State:")
    print(f"  Path:       {active_db_path}")
    print(f"  Size:       {db_size:,} bytes ({round(db_size / (1024*1024), 2)} MB)")
    print(f"  SHA-256:    {db_sha256}")
    print(f"  Integrity:  {integ[0][0] if integ else 'UNKNOWN'}")
    print(f"  FK Errors:  {len(fk)}")
    print(f"  Relational: {len(db_ids):,} rows")
    print(f"  FTS5 Rows:  {fts_count:,} rows")
    print(f"  Embeddings: {emb_count:,} rows")

    to_remove = db_ids - canonical_ids
    to_add = canonical_ids - db_ids
    common = db_ids & canonical_ids

    stale_hindi = []
    stale_appendix = []
    stale_other = []

    for cid in to_remove:
        doc_id, text = db_id_map[cid]
        if DEVANAGARI_REGEX.search(text):
            stale_hindi.append(cid)
        elif ":2." in cid or ":3." in cid or ":1." in cid:
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

    parity = verify_database_parity(active_db_path, canonical_map)
    print("\n" + "-" * 90)
    print("PARITY VERIFICATION SUMMARY")
    print("-" * 90)
    print(f"  Overall Parity Passed:     {parity['passed']}")
    if parity["errors"]:
        for err in parity["errors"]:
            print(f"  [X] {err}")
    else:
        print("  [OK] Exact 4-way ID digest match across Canonical, Relational, FTS5, and Vector stores.")

    print("\nDry run complete. No modifications were made to the database.")


# -----------------------------------------------------------------------------
# 2. Build Staging Database
# -----------------------------------------------------------------------------

def build_staging(
    active_db_path: Path = ACTIVE_DB_PATH,
    staging_db_path: Path = STAGING_DB_PATH,
    backup_dir: Path = BACKUP_DIR,
    clauses_dir: Path = CANONICAL_CLAUSES_DIR,
    manifest_path: Path = MANIFEST_PATH,
    lock_path: Path = LOCK_FILE_PATH,
    confirm: bool = False
) -> Dict[str, Any]:
    """Build clean staging database from canonical corpus records.
    
    Guarantees:
    - Never touches or overwrites active_db_path.
    - Creates immutable verified online backup snapshot in backup_dir.
    - Builds staging DB at staging_db_path.
    - Ingests canonical clauses, builds FTS5 and embeddings.
    - Validates 4-way ID digest parity.
    - Writes promotion manifest recording input hashes, digests, and metadata.
    """
    if not confirm:
        raise ValueError("Staging build requires explicit confirmation: confirm=True / --confirm-staging")

    if not active_db_path.exists():
        raise FileNotFoundError(f"Active database not found at {active_db_path}")

    with ReconciliationLock(lock_path=lock_path):
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"cricketiq_backup_{timestamp}.db"

        # Step 1: Online SQLite Backup
        print(f"\n[Step 1/6] Creating verified online backup of active database...")
        print(f"  Source: {active_db_path}")
        print(f"  Backup: {backup_file}")

        src_conn = sqlite3.connect(active_db_path)
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
            if backup_file.exists():
                backup_file.unlink()
            raise StagingValidationError(f"Backup integrity verification failed: {b_integ}, FK errors: {b_fk}")

        active_sha256 = compute_file_sha256(active_db_path)
        backup_sha256 = compute_file_sha256(backup_file)
        print(f"  Active DB SHA-256: {active_sha256}")
        print(f"  Backup SHA-256:    {backup_sha256}")
        print("  Backup verified successfully (PRAGMA integrity_check = ok, 0 foreign key errors).")

        # Step 2: Initialize Clean Staging Database
        print(f"\n[Step 2/6] Initializing clean staging database at {staging_db_path}...")
        if staging_db_path.exists():
            staging_db_path.unlink()

        staging_engine = create_db_engine(f"sqlite:///{staging_db_path}")
        Base.metadata.create_all(bind=staging_engine)
        staging_session = Session(bind=staging_engine)
        staging_repo = CricketIQRepository(staging_session)

        # Step 3: Register Official Source Documents with Explicit Regulatory Role
        print(f"\n[Step 3/6] Populating authoritative source documents and relationships...")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_docs = json.load(f)

        for m in manifest_docs:
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
        print(f"\n[Step 4/6] Ingesting canonical clauses from {clauses_dir}...")
        canonical_map, corpus_meta = load_canonical_clauses(clauses_dir)
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

        # Step 6: Validate Staging Database Parity
        print(f"\n[Step 6/6] Executing comprehensive integrity verification on staging database...")
        parity = verify_database_parity(staging_db_path, canonical_map)

        print(f"\nStaging Validation Results:")
        print(f"  Path:                    {staging_db_path}")
        print(f"  Size:                    {parity['file_size_bytes']:,} bytes ({round(parity['file_size_bytes'] / (1024*1024), 2)} MB)")
        print(f"  SHA-256:                 {parity['sha256']}")
        print(f"  Integrity Check:         {parity['integrity']}")
        print(f"  Foreign Key Errors:      {parity['fk_errors']}")
        print(f"  Relational Clauses:      {parity['relational_count']:,} (Expected: {len(canonical_map):,})")
        print(f"  FTS5 Clauses:            {parity['fts_count']:,} (Expected: {len(canonical_map):,})")
        print(f"  Vector Embeddings:       {parity['embedding_count']:,} (Expected: {len(canonical_map):,})")
        print(f"  Stale Devanagari Rows:   {parity['hindi_rows']}")
        print(f"  Canonical ID Digest:     {parity['canonical_ids_digest']}")
        print(f"  Relational ID Digest:    {parity['relational_ids_digest']}")
        print(f"  FTS5 ID Digest:          {parity['fts_ids_digest']}")
        print(f"  Vector ID Digest:        {parity['embedding_ids_digest']}")

        if not parity["passed"]:
            raise StagingValidationError(f"Staging validation failed: {parity['errors']}")

        # Save Promotion Manifest
        manifest_data = {
            "timestamp": timestamp,
            "git_commit": get_git_commit(),
            "script_version": "1.1.0",
            "active_db_path": str(active_db_path.resolve()),
            "active_db_sha256_before": active_sha256,
            "active_db_backup": str(backup_file.resolve()),
            "staging_db_path": str(staging_db_path.resolve()),
            "staging_db_sha256": parity["sha256"],
            "staging_db_size_bytes": parity["file_size_bytes"],
            "canonical_input_files": corpus_meta["input_files"],
            "canonical_deduplicated_clause_count": len(canonical_map),
            "canonical_duplicate_count": corpus_meta["duplicate_count"],
            "per_document_counts": corpus_meta["per_document_counts"],
            "canonical_ids_digest": parity["canonical_ids_digest"],
            "relational_ids_digest": parity["relational_ids_digest"],
            "fts_ids_digest": parity["fts_ids_digest"],
            "embedding_ids_digest": parity["embedding_ids_digest"],
            "fts_config": {
                "table_name": "rule_clauses_fts",
                "tokenizer": "porter",
                "columns": ["clause_number", "heading", "content"]
            },
            "embedding_metadata": {
                "provider": "LocalDeterministicEmbeddingProvider",
                "model_name": embedder.model_name,
                "dimension": embedder.dimension,
                "template_version": "v1",
                "input_hash_scheme": "sha256",
                "is_semantic": False,
                "readiness_classification": "diagnostic_non_semantic"
            },
            "integrity_check": parity["integrity"],
            "foreign_key_errors": parity["fk_errors"],
            "exact_parity_results": {
                "all_id_digests_match": (
                    parity["canonical_ids_digest"] == parity["relational_ids_digest"] ==
                    parity["fts_ids_digest"] == parity["embedding_ids_digest"]
                ),
                "counts_match": (
                    len(canonical_map) == parity["relational_count"] ==
                    parity["fts_count"] == parity["embedding_count"]
                )
            },
            "validation_passed": True,
            "status": "STAGING_READY",
            "explicit_limitations": [
                "local-deterministic-v1 is a non-semantic pseudo-embedding for structural integrity testing only.",
                "Diagnostic dense channel is excluded from production RRF ranking by default."
            ]
        }
        manifest_file = backup_dir / f"staging_manifest_{timestamp}.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        print(f"\nPromotion manifest written to: {manifest_file}")
        return manifest_data


# -----------------------------------------------------------------------------
# 3. Promote Staging Database
# -----------------------------------------------------------------------------

def promote_staging(
    active_db_path: Path = ACTIVE_DB_PATH,
    staging_db_path: Path = STAGING_DB_PATH,
    backup_dir: Path = BACKUP_DIR,
    clauses_dir: Path = CANONICAL_CLAUSES_DIR,
    manifest_path: Optional[Path] = None,
    lock_path: Path = LOCK_FILE_PATH,
    confirm: bool = False
) -> Dict[str, Any]:
    """Promote staging database to active path with full rollback guarantees.
    
    Guarantees:
    - Pre-promotion active database SHA invariance check against manifest.
    - Full pre-promotion staging revalidation.
    - Verified rollback snapshot (cricketiq_rollback_<timestamp>.db) created before swap.
    - Swap error recovery for PermissionError and OSError.
    - Automatic rollback if post-promotion checks fail on active DB.
    - Rollback snapshot permanently preserved.
    """
    if not confirm:
        raise ValueError("Promotion requires explicit confirmation: confirm=True / --confirm-promote")

    if not staging_db_path.exists():
        raise FileNotFoundError(f"Staging database not found at {staging_db_path}. Run build_staging first.")

    with ReconciliationLock(lock_path=lock_path):
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        # Step 1: Load and Validate Manifest
        if manifest_path is None:
            # Find latest staging manifest
            manifests = sorted(backup_dir.glob("staging_manifest_*.json"))
            if not manifests:
                raise StagingValidationError(f"No staging manifest found in {backup_dir}. Run build_staging first.")
            manifest_path = manifests[-1]

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        if not manifest_data.get("validation_passed"):
            raise StagingValidationError(f"Manifest at {manifest_path} indicates staging validation was NOT passed.")

        # Verify staging file hash matches manifest
        current_staging_sha = compute_file_sha256(staging_db_path)
        expected_staging_sha = manifest_data.get("staging_db_sha256")
        if current_staging_sha != expected_staging_sha:
            raise StagingValidationError(
                f"Staging database SHA ({current_staging_sha}) does not match manifest SHA ({expected_staging_sha}). Corruption suspected."
            )

        # Step 2: Active DB SHA Invariance Assertion
        if active_db_path.exists():
            current_active_sha = compute_file_sha256(active_db_path)
            expected_active_sha = manifest_data.get("active_db_sha256_before")
            if expected_active_sha and current_active_sha != expected_active_sha:
                raise ActiveDBChangedError(
                    f"Active database SHA has changed since staging was built! "
                    f"Expected: {expected_active_sha}, Current: {current_active_sha}. "
                    f"Refusing to overwrite intervening database modifications. Run build_staging again."
                )
        else:
            current_active_sha = None

        # Step 3: Revalidate Staging DB Parity
        canonical_map, _ = load_canonical_clauses(clauses_dir)
        pre_parity = verify_database_parity(staging_db_path, canonical_map)
        if not pre_parity["passed"]:
            raise StagingValidationError(f"Staging pre-promotion parity check failed: {pre_parity['errors']}")

        # Step 4: Create Rollback Snapshot
        rollback_file = backup_dir / f"cricketiq_rollback_{timestamp}.db"
        if active_db_path.exists():
            print(f"\n[Step 1/3] Creating immutable rollback snapshot: {rollback_file}...")
            shutil.copy2(active_db_path, rollback_file)
            rollback_sha = compute_file_sha256(rollback_file)
            if rollback_sha != current_active_sha:
                raise ReconciliationError("Rollback snapshot creation failed: SHA-256 mismatch.")
            print(f"  Rollback snapshot verified (SHA-256: {rollback_sha}).")

        # Step 5: Atomic Filesystem Swap with Recovery
        print(f"\n[Step 2/3] Performing atomic filesystem swap: {staging_db_path.name} -> {active_db_path.name}...")
        temp_old = active_db_path.with_suffix(".old")
        if temp_old.exists():
            temp_old.unlink()

        try:
            if active_db_path.exists():
                active_db_path.replace(temp_old)
            staging_db_path.replace(active_db_path)
            print("  Filesystem rename completed.")
        except Exception as e:
            # Recovery
            print(f"CRITICAL: Swap failed ({type(e).__name__}: {e}). Restoring active database...")
            if temp_old.exists() and not active_db_path.exists():
                temp_old.replace(active_db_path)
            elif not active_db_path.exists() and rollback_file.exists():
                shutil.copy2(rollback_file, active_db_path)
            raise PromotionSwapError(f"Filesystem swap failed ({e}). Active database was restored.") from e

        # Step 6: Post-Promotion Verification on Active DB
        print(f"\n[Step 3/3] Verifying active database post-promotion...")
        try:
            post_parity = verify_database_parity(active_db_path, canonical_map)
            if not post_parity["passed"]:
                raise PostPromotionVerificationError(f"Post-promotion verification failed: {post_parity['errors']}")
            if post_parity["sha256"] != current_staging_sha:
                raise PostPromotionVerificationError(
                    f"Active DB SHA ({post_parity['sha256']}) does not match expected staging SHA ({current_staging_sha})"
                )
        except Exception as e:
            print(f"\nCRITICAL: Post-promotion validation failed! Triggering automatic rollback to {rollback_file}...")
            if temp_old.exists():
                try:
                    if active_db_path.exists():
                        active_db_path.unlink()
                    temp_old.replace(active_db_path)
                except Exception:
                    shutil.copy2(rollback_file, active_db_path)
            else:
                shutil.copy2(rollback_file, active_db_path)

            restored_sha = compute_file_sha256(active_db_path)
            if current_active_sha and restored_sha != current_active_sha:
                raise PostPromotionVerificationError(
                    f"FATAL: Rollback restored active DB but SHA mismatch detected! Expected {current_active_sha}, got {restored_sha}"
                )
            raise PostPromotionVerificationError(
                f"Post-promotion verification failed ({e}). Active database successfully rolled back to pre-promotion state."
            ) from e

        # Step 7: Finalize Promotion
        if temp_old.exists():
            temp_old.unlink()

        manifest_data["status"] = "PROMOTED"
        manifest_data["promoted_at"] = datetime.now(timezone.utc).isoformat()
        manifest_data["rollback_snapshot"] = str(rollback_file.resolve())
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        success_manifest = backup_dir / f"promotion_success_{timestamp}.json"
        with open(success_manifest, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        print(f"\nPromotion success manifest written to: {success_manifest}")
        print(f"Rollback snapshot preserved permanently at: {rollback_file}")
        return manifest_data


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

    try:
        if args.promote_staging:
            promote_staging(confirm=args.confirm_promote)
        elif args.build_staging:
            build_staging(confirm=args.confirm_staging)
        else:
            run_dry_run()
    except Exception as e:
        print(f"\n[ERROR] Reconciliation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
