"""Tests for Safe Database Reconciliation & Staging Promotion Protocol (Phase 6 Gate 2).

Validates:
- Exclusive process locking and rejection of concurrent runs
- Invariant assertion: active DB SHA change rejects promotion
- Staging corruption and manifest mismatch rejection
- Recoverable filesystem swap handling PermissionError and OSError
- Automatic rollback upon post-promotion parity or integrity failure
- Permanent retention of pre-promotion rollback snapshots
"""

from __future__ import annotations
import hashlib
import json
import os
import shutil
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from scripts.reconcile_database import (
    ReconciliationLock,
    LockAcquisitionError,
    ActiveDBChangedError,
    StagingValidationError,
    PromotionSwapError,
    PostPromotionVerificationError,
    compute_file_sha256,
    compute_id_set_digest,
    verify_database_parity,
    build_staging,
    promote_staging
)


def _create_minimal_valid_db(db_path: Path, clause_ids: list[str]) -> str:
    """Create a minimal SQLite DB containing valid schema, documents, clauses, FTS, and embeddings."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE source_documents (
            id VARCHAR(64) PRIMARY KEY,
            title VARCHAR(255),
            regulatory_role VARCHAR(64)
        )
    """)
    c.execute("INSERT INTO source_documents VALUES ('MCC_LAWS_2026', 'MCC Laws of Cricket', 'NORMATIVE_LAWS_BASELINE')")

    c.execute("""
        CREATE TABLE rule_clauses (
            id VARCHAR(128) PRIMARY KEY,
            source_document_id VARCHAR(64),
            clause_number VARCHAR(64),
            heading VARCHAR(255),
            original_text TEXT,
            FOREIGN KEY (source_document_id) REFERENCES source_documents(id)
        )
    """)

    c.execute("""
        CREATE VIRTUAL TABLE rule_clauses_fts USING fts5(
            clause_id UNINDEXED,
            source_document_id UNINDEXED,
            clause_number,
            heading,
            content,
            tokenize=porter
        )
    """)

    c.execute("""
        CREATE TABLE clause_embeddings (
            clause_id VARCHAR(128) PRIMARY KEY,
            document_id VARCHAR(64),
            model_name VARCHAR(64),
            dimension INTEGER,
            template_version VARCHAR(16),
            input_hash VARCHAR(64),
            vector_blob BLOB,
            created_at TIMESTAMP
        )
    """)

    for cid in sorted(clause_ids):
        c.execute(
            "INSERT INTO rule_clauses VALUES (?, 'MCC_LAWS_2026', '1.1', 'Title', 'Law text')",
            (cid,)
        )
        c.execute(
            "INSERT INTO rule_clauses_fts VALUES (?, 'MCC_LAWS_2026', '1.1', 'Title', 'Law text')",
            (cid,)
        )
        c.execute(
            "INSERT INTO clause_embeddings VALUES (?, 'MCC_LAWS_2026', 'local-deterministic-v1', 384, 'v1', 'hash', X'00', '2026-11-17')",
            (cid,)
        )

    conn.commit()
    conn.close()
    return compute_file_sha256(db_path)


# -----------------------------------------------------------------------------
# 1. Process Lock Tests
# -----------------------------------------------------------------------------

def test_exclusive_process_lock_acquisition(tmp_path: Path):
    """Test that process lock can be acquired and prevents concurrent execution."""
    lock_file = tmp_path / "reconcile.lock"
    lock1 = ReconciliationLock(lock_path=lock_file)
    lock1.acquire()

    assert lock_file.exists()
    with open(lock_file, "r", encoding="utf-8") as f:
        info = json.load(f)
    assert info["pid"] == os.getpid()

    # Second lock attempt must fail
    lock2 = ReconciliationLock(lock_path=lock_file)
    with pytest.raises(LockAcquisitionError, match="Another reconciliation process is currently running"):
        lock2.acquire()

    # Releasing lock1 allows lock2 to acquire
    lock1.release()
    assert not lock_file.exists()

    lock2.acquire()
    assert lock_file.exists()
    lock2.release()
    assert not lock_file.exists()


# -----------------------------------------------------------------------------
# 2. Manifest and Parity Tests
# -----------------------------------------------------------------------------

def test_verify_database_parity_success(tmp_path: Path):
    """Test that verify_database_parity succeeds on valid matched database."""
    db_file = tmp_path / "test.db"
    clause_ids = ["MCC_LAWS_2026:1.1", "MCC_LAWS_2026:1.2"]
    _create_minimal_valid_db(db_file, clause_ids)

    canonical_map = {
        cid: {"id": cid, "source_document_id": "MCC_LAWS_2026", "original_text": "Law text"}
        for cid in clause_ids
    }
    parity = verify_database_parity(db_file, canonical_map)
    assert parity["passed"] is True
    assert parity["errors"] == []
    assert parity["relational_count"] == 2
    assert parity["fts_count"] == 2
    assert parity["embedding_count"] == 2
    assert parity["canonical_ids_digest"] == parity["relational_ids_digest"] == parity["fts_ids_digest"] == parity["embedding_ids_digest"]


def test_verify_database_parity_detects_digest_mismatch(tmp_path: Path):
    """Test that parity validator detects when FTS or vector stores omit a clause."""
    db_file = tmp_path / "test.db"
    clause_ids = ["MCC_LAWS_2026:1.1", "MCC_LAWS_2026:1.2"]
    _create_minimal_valid_db(db_file, clause_ids)

    # Intentionally delete 1 vector row to break parity
    conn = sqlite3.connect(db_file)
    conn.execute("DELETE FROM clause_embeddings WHERE clause_id = 'MCC_LAWS_2026:1.2'")
    conn.commit()
    conn.close()

    canonical_map = {
        cid: {"id": cid, "source_document_id": "MCC_LAWS_2026", "original_text": "Law text"}
        for cid in clause_ids
    }
    parity = verify_database_parity(db_file, canonical_map)
    assert parity["passed"] is False
    assert any("Embedding row count mismatch" in err for err in parity["errors"])
    assert any("Digest mismatch" in err for err in parity["errors"])


# -----------------------------------------------------------------------------
# 3. Promotion Safety and Invariance Tests
# -----------------------------------------------------------------------------

def test_active_db_changed_rejects_promotion(tmp_path: Path):
    """Test that promotion rejects immediately if active DB SHA changed after staging build."""
    active_db = tmp_path / "active.db"
    staging_db = tmp_path / "staging.db"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    lock_file = tmp_path / "reconcile.lock"

    clause_ids = ["MCC_LAWS_2026:1.1"]
    active_sha_before = _create_minimal_valid_db(active_db, clause_ids)
    staging_sha = _create_minimal_valid_db(staging_db, clause_ids)

    # Create manifest with original active SHA
    manifest_data = {
        "validation_passed": True,
        "staging_db_sha256": staging_sha,
        "active_db_sha256_before": active_sha_before,
        "status": "STAGING_READY"
    }
    manifest_file = backup_dir / "staging_manifest_test.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    # Tamper with active DB so its SHA changes
    conn = sqlite3.connect(active_db)
    conn.execute("CREATE TABLE tampered (id INT)")
    conn.commit()
    conn.close()
    tampered_active_sha = compute_file_sha256(active_db)
    assert tampered_active_sha != active_sha_before

    # Attempt promotion: must fail with ActiveDBChangedError
    with pytest.raises(ActiveDBChangedError, match="Active database SHA has changed"):
        promote_staging(
            active_db_path=active_db,
            staging_db_path=staging_db,
            backup_dir=backup_dir,
            manifest_path=manifest_file,
            lock_path=lock_file,
            confirm=True
        )

    # Active DB must be untouched (still tampered_active_sha, not staging)
    assert compute_file_sha256(active_db) == tampered_active_sha
    assert staging_db.exists()


def test_staging_corruption_rejects_pre_promotion(tmp_path: Path):
    """Test that promotion fails before swap if staging DB file was corrupted or tampered."""
    active_db = tmp_path / "active.db"
    staging_db = tmp_path / "staging.db"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    lock_file = tmp_path / "reconcile.lock"

    clause_ids = ["MCC_LAWS_2026:1.1"]
    active_sha = _create_minimal_valid_db(active_db, clause_ids)
    staging_sha = _create_minimal_valid_db(staging_db, clause_ids)

    manifest_data = {
        "validation_passed": True,
        "staging_db_sha256": staging_sha,
        "active_db_sha256_before": active_sha,
        "status": "STAGING_READY"
    }
    manifest_file = backup_dir / "staging_manifest_test.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    # Corrupt staging DB by appending garbage bytes
    with open(staging_db, "ab") as f:
        f.write(b"GARBAGE_BYTES")

    with pytest.raises(StagingValidationError, match="Staging database SHA .* does not match manifest SHA"):
        promote_staging(
            active_db_path=active_db,
            staging_db_path=staging_db,
            backup_dir=backup_dir,
            manifest_path=manifest_file,
            lock_path=lock_file,
            confirm=True
        )

    # Active DB remains intact
    assert compute_file_sha256(active_db) == active_sha


# -----------------------------------------------------------------------------
# 4. Swap and Rollback Fault Injection Tests
# -----------------------------------------------------------------------------

def test_swap_failure_recovers_active_db(tmp_path: Path):
    """Test that filesystem error during rename restores the original active database."""
    active_db = tmp_path / "active.db"
    staging_db = tmp_path / "staging.db"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    lock_file = tmp_path / "reconcile.lock"

    clause_ids = ["MCC_LAWS_2026:1.1"]
    active_sha = _create_minimal_valid_db(active_db, clause_ids)
    staging_sha = _create_minimal_valid_db(staging_db, clause_ids)

    manifest_data = {
        "validation_passed": True,
        "staging_db_sha256": staging_sha,
        "active_db_sha256_before": active_sha,
        "status": "STAGING_READY"
    }
    manifest_file = backup_dir / "staging_manifest_test.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    # Simulate PermissionError when moving staging to active
    original_replace = Path.replace

    def mock_replace(self, target):
        if self.resolve() == staging_db.resolve():
            raise PermissionError("[WinError 32] The process cannot access the file because it is being used by another process")
        return original_replace(self, target)

    with patch("scripts.reconcile_database.verify_database_parity", return_value={"passed": True, "errors": [], "sha256": staging_sha}):
        with patch.object(Path, "replace", mock_replace):
            with pytest.raises(PromotionSwapError, match="Filesystem swap failed"):
                promote_staging(
                    active_db_path=active_db,
                    staging_db_path=staging_db,
                    backup_dir=backup_dir,
                    manifest_path=manifest_file,
                    lock_path=lock_file,
                    confirm=True
                )

    # Active DB must be restored to its pre-promotion state and SHA
    assert active_db.exists()
    assert compute_file_sha256(active_db) == active_sha


def test_failure_after_active_renamed_recovers_original_db(tmp_path: Path):
    """Test that failure occurring after active DB was renamed to .old recovers cleanly."""
    active_db = tmp_path / "active.db"
    staging_db = tmp_path / "staging.db"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    lock_file = tmp_path / "reconcile.lock"

    clause_ids = ["MCC_LAWS_2026:1.1"]
    active_sha = _create_minimal_valid_db(active_db, clause_ids)
    staging_sha = _create_minimal_valid_db(staging_db, clause_ids)

    manifest_data = {
        "validation_passed": True,
        "staging_db_sha256": staging_sha,
        "active_db_sha256_before": active_sha,
        "status": "STAGING_READY"
    }
    manifest_file = backup_dir / "staging_manifest_test.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    original_replace = Path.replace

    def mock_replace_fail_second(self, target):
        # Allow active.db -> active.old to succeed
        if self.resolve() == staging_db.resolve():
            raise OSError("Disk I/O error during promotion")
        return original_replace(self, target)

    with patch("scripts.reconcile_database.verify_database_parity", return_value={"passed": True, "errors": [], "sha256": staging_sha}):
        with patch.object(Path, "replace", mock_replace_fail_second):
            with pytest.raises(PromotionSwapError, match="Filesystem swap failed"):
                promote_staging(
                    active_db_path=active_db,
                    staging_db_path=staging_db,
                    backup_dir=backup_dir,
                    manifest_path=manifest_file,
                    lock_path=lock_file,
                    confirm=True
                )

    # Active DB must have been restored from .old
    assert active_db.exists()
    assert compute_file_sha256(active_db) == active_sha


def test_concurrent_promotion_rejected_by_process_lock(tmp_path: Path):
    """Test that a second promotion call fails immediately when another promotion holds the lock."""
    active_db = tmp_path / "active.db"
    staging_db = tmp_path / "staging.db"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    lock_file = tmp_path / "reconcile.lock"

    clause_ids = ["MCC_LAWS_2026:1.1"]
    active_sha = _create_minimal_valid_db(active_db, clause_ids)
    staging_sha = _create_minimal_valid_db(staging_db, clause_ids)

    manifest_data = {
        "validation_passed": True,
        "staging_db_sha256": staging_sha,
        "active_db_sha256_before": active_sha,
        "status": "STAGING_READY"
    }
    manifest_file = backup_dir / "staging_manifest_test.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    # Manually hold lock
    with ReconciliationLock(lock_path=lock_file):
        with pytest.raises(LockAcquisitionError, match="Another reconciliation process is currently running"):
            promote_staging(
                active_db_path=active_db,
                staging_db_path=staging_db,
                backup_dir=backup_dir,
                manifest_path=manifest_file,
                lock_path=lock_file,
                confirm=True
            )


def test_successful_staging_promotion_end_to_end(tmp_path: Path):
    """Test successful promotion end-to-end preserves rollback and updates manifest status."""
    active_db = tmp_path / "active.db"
    staging_db = tmp_path / "staging.db"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    lock_file = tmp_path / "reconcile.lock"

    clause_ids = ["MCC_LAWS_2026:1.1"]
    active_sha = _create_minimal_valid_db(active_db, clause_ids)
    staging_sha = _create_minimal_valid_db(staging_db, clause_ids)

    manifest_data = {
        "validation_passed": True,
        "staging_db_sha256": staging_sha,
        "active_db_sha256_before": active_sha,
        "status": "STAGING_READY"
    }
    manifest_file = backup_dir / "staging_manifest_test.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    with patch("scripts.reconcile_database.verify_database_parity", return_value={"passed": True, "errors": [], "sha256": staging_sha}):
        result = promote_staging(
            active_db_path=active_db,
            staging_db_path=staging_db,
            backup_dir=backup_dir,
            manifest_path=manifest_file,
            lock_path=lock_file,
            confirm=True
        )

    assert result["status"] == "PROMOTED"
    assert "rollback_snapshot" in result
    assert Path(result["rollback_snapshot"]).exists()
    assert compute_file_sha256(Path(result["rollback_snapshot"])) == active_sha
    assert compute_file_sha256(active_db) == staging_sha
    assert not (active_db.with_suffix(".old")).exists()



def test_post_promotion_verification_failure_triggers_automatic_rollback(tmp_path: Path):
    """Test that failure during post-promotion verification automatically triggers rollback to backup."""
    active_db = tmp_path / "active.db"
    staging_db = tmp_path / "staging.db"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    lock_file = tmp_path / "reconcile.lock"

    clause_ids = ["MCC_LAWS_2026:1.1"]
    active_sha = _create_minimal_valid_db(active_db, clause_ids)
    staging_sha = _create_minimal_valid_db(staging_db, clause_ids)

    manifest_data = {
        "validation_passed": True,
        "staging_db_sha256": staging_sha,
        "active_db_sha256_before": active_sha,
        "status": "STAGING_READY"
    }
    manifest_file = backup_dir / "staging_manifest_test.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    call_count = 0

    def mock_verify_parity(db_path, canonical_map):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Pre-promotion check on staging passes
            return {"passed": True, "errors": [], "sha256": staging_sha}
        else:
            # Post-promotion check on active DB fails!
            return {"passed": False, "errors": ["Simulated index corruption on promoted active DB"]}

    with patch("scripts.reconcile_database.verify_database_parity", mock_verify_parity):
        with pytest.raises(PostPromotionVerificationError, match="Post-promotion verification failed"):
            promote_staging(
                active_db_path=active_db,
                staging_db_path=staging_db,
                backup_dir=backup_dir,
                manifest_path=manifest_file,
                lock_path=lock_file,
                confirm=True
            )

    # Active DB must have been restored back to original active_sha!
    assert active_db.exists()
    assert compute_file_sha256(active_db) == active_sha

    # Rollback snapshot must be preserved in backup_dir
    rollbacks = list(backup_dir.glob("cricketiq_rollback_*.db"))
    assert len(rollbacks) >= 1
    assert compute_file_sha256(rollbacks[0]) == active_sha
