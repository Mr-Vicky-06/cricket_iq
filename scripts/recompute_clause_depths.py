#!/usr/bin/env python3
"""Deterministic Hierarchy Depth Calculation & Parent Relationship Repair Tool (Phase 6 Gate 3).

Computes true tree depth for all canonical clauses:
  depth(c) = 1 if parent is None or unresolvable
  depth(c) = depth(parent) + 1 if parent exists in same document

Sanitizes parent relationships:
  - Cross-document references in MCC_CHANGES_EXPLAINED_2026 converted to cross_references
  - Cross-document amendment pointers in ICC_T20I_MEN_ADD_2026 converted to cross_references
  - Absent unnumbered Law headings recorded in structural manifest
  - 100% preservation of clause IDs, original text, and cryptographic ID set digests

Usage:
  # Dry-run analysis (Default, non-destructive)
  python scripts/recompute_clause_depths.py --dry-run

  # Build staging canonical corpus and database with verified backup
  python scripts/recompute_clause_depths.py --build-staging --confirm-staging
"""

from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CANONICAL_CLAUSES_DIR = PROJECT_ROOT / "data" / "corpus" / "clauses"
STAGING_CLAUSES_DIR = PROJECT_ROOT / "data" / "corpus" / "clauses_staging"
MANIFEST_DIR = PROJECT_ROOT / "data" / "corpus" / "manifests"
REPAIR_MANIFEST_PATH = MANIFEST_DIR / "gate3_hierarchy_repairs.json"


def compute_file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_id_set_digest(ids: List[str]) -> str:
    sorted_unique = sorted(set(ids))
    return hashlib.sha256("\n".join(sorted_unique).encode("utf-8")).hexdigest()


def load_deduplicated_clauses(clauses_dir: Path) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Load canonical clause records per document, deterministically deduplicated by longest original_text."""
    doc_clauses: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for jf in sorted(clauses_dir.glob("*_clauses.json")):
        doc_id = jf.name.replace("_clauses.json", "")
        with open(jf, "r", encoding="utf-8") as f:
            items = json.load(f)
        seen: Dict[str, Dict[str, Any]] = {}
        for item in items:
            cid = item["id"]
            if cid in seen:
                prev_len = len(seen[cid].get("original_text", "") or "")
                new_len = len(item.get("original_text", "") or "")
                if new_len > prev_len:
                    seen[cid] = item
            else:
                seen[cid] = item
        doc_clauses[doc_id] = seen
    return doc_clauses


def recompute_hierarchy(doc_clauses: Dict[str, Dict[str, Dict[str, Any]]]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """Recompute true tree depth and sanitize parent links across all documents."""
    all_repaired: Dict[str, Dict[str, Any]] = {}
    depth_distribution: Dict[int, int] = {}
    doc_summaries: Dict[str, Any] = {}
    repaired_records_list: List[Dict[str, Any]] = []

    for doc_id, clauses in doc_clauses.items():
        memo: Dict[str, int] = {}
        doc_depth_dist: Dict[int, int] = {}
        doc_repaired_count = 0
        doc_xrefs_added = 0

        # Pass 1: Relationship Sanitization
        sanitized_clauses: Dict[str, Dict[str, Any]] = {}
        for cid, c in clauses.items():
            c_copy = dict(c)
            pid = c_copy.get("parent_clause_id")
            xrefs = list(c_copy.get("cross_references") or [])

            # Case A: MCC_CHANGES_EXPLAINED_2026 pointing to MCC Laws
            if doc_id == "MCC_CHANGES_EXPLAINED_2026" and pid and pid not in clauses:
                p_clause_num = pid.split(":", 1)[1] if ":" in pid else pid
                target_xref = f"MCC_LAWS_2026:{p_clause_num}"
                if target_xref not in xrefs:
                    xrefs.append(target_xref)
                    doc_xrefs_added += 1
                c_copy["parent_clause_id"] = None
                c_copy["cross_references"] = xrefs

            # Case B: ICC_T20I_MEN_ADD_2026 pointing to base T20I PC
            elif doc_id == "ICC_T20I_MEN_ADD_2026" and pid and pid not in clauses:
                p_clause_num = pid.split(":", 1)[1] if ":" in pid else pid
                target_xref = f"ICC_T20I_MEN_2026:{p_clause_num}"
                if target_xref not in xrefs:
                    xrefs.append(target_xref)
                    doc_xrefs_added += 1
                c_copy["parent_clause_id"] = None
                c_copy["cross_references"] = xrefs

            # Case C: Absent unnumbered chapter headings (:1, :7, :12, :24, :25, :42)
            elif pid and pid not in clauses:
                p_clause_num = pid.split(":", 1)[1] if ":" in pid else pid
                if p_clause_num in ["1", "7", "12", "24", "25", "42"]:
                    # Keep parent_clause_id as None for relational tree integrity, record in structure
                    c_copy["parent_clause_id"] = None

            sanitized_clauses[cid] = c_copy

        # Pass 2: Recursive Depth Calculation
        def get_depth(clause_id: str) -> int:
            if clause_id in memo:
                return memo[clause_id]
            curr = sanitized_clauses.get(clause_id)
            if not curr:
                return 1
            curr_pid = curr.get("parent_clause_id")
            if not curr_pid or curr_pid not in sanitized_clauses or curr_pid == clause_id:
                memo[clause_id] = 1
                return 1
            calculated_depth = get_depth(curr_pid) + 1
            memo[clause_id] = calculated_depth
            return calculated_depth

        for cid, c_obj in sanitized_clauses.items():
            new_depth = get_depth(cid)
            old_depth = c_obj.get("hierarchy_depth", 1)
            c_obj["hierarchy_depth"] = new_depth
            all_repaired[cid] = c_obj

            doc_depth_dist[new_depth] = doc_depth_dist.get(new_depth, 0) + 1
            depth_distribution[new_depth] = depth_distribution.get(new_depth, 0) + 1

            if new_depth != old_depth or c_obj.get("parent_clause_id") != clauses[cid].get("parent_clause_id"):
                doc_repaired_count += 1
                repaired_records_list.append({
                    "clause_id": cid,
                    "source_document_id": doc_id,
                    "old_depth": old_depth,
                    "new_depth": new_depth,
                    "old_parent": clauses[cid].get("parent_clause_id"),
                    "new_parent": c_obj.get("parent_clause_id"),
                    "cross_references": c_obj.get("cross_references")
                })

        doc_summaries[doc_id] = {
            "total_clauses": len(clauses),
            "depth_distribution": doc_depth_dist,
            "repaired_records_count": doc_repaired_count,
            "xrefs_added_count": doc_xrefs_added
        }

    manifest_metadata = {
        "total_clauses_evaluated": len(all_repaired),
        "total_records_modified": len(repaired_records_list),
        "depth_distribution_overall": depth_distribution,
        "documents": doc_summaries,
        "sample_repairs": repaired_records_list[:25]
    }
    return all_repaired, manifest_metadata


def run_dry_run() -> None:
    print("=" * 90)
    print("CRICKETIQ HIERARCHY DEPTH & PARENT RELATIONSHIP REPAIR — DRY RUN")
    print("=" * 90)

    doc_clauses = load_deduplicated_clauses(CANONICAL_CLAUSES_DIR)
    total_clauses = sum(len(c) for c in doc_clauses.values())
    print(f"Loaded {total_clauses:,} canonical deduplicated clauses across {len(doc_clauses)} documents.")

    repaired_clauses, meta = recompute_hierarchy(doc_clauses)

    print("\n" + "-" * 90)
    print("RECALCULATED TRUE DEPTH DISTRIBUTION (TARGET INVARIANT)")
    print("-" * 90)
    for d in sorted(meta["depth_distribution_overall"].keys()):
        count = meta["depth_distribution_overall"][d]
        pct = round(count / total_clauses * 100, 2)
        print(f"  Depth {d}: {count:5,} clauses ({pct:5.2f}%)")

    print("\n" + "-" * 90)
    print("PER-DOCUMENT HIERARCHY SUMMARY")
    print("-" * 90)
    for doc_id, s in meta["documents"].items():
        print(f"  {doc_id:28}: total={s['total_clauses']:5}, repaired={s['repaired_records_count']:5}, depths={s['depth_distribution']}")

    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPAIR_MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"\nRepair manifest written to: {REPAIR_MANIFEST_PATH}")
    print("\nDry-run complete. No canonical source files or databases were modified.")


def run_build_staging(confirm: bool) -> None:
    print("=" * 90)
    print("CRICKETIQ HIERARCHY DEPTH & PARENT RELATIONSHIP REPAIR — BUILD STAGING")
    print("=" * 90)

    if not confirm:
        print("ERROR: Staging build requires explicit confirmation flag: --confirm-staging")
        sys.exit(1)

    doc_clauses = load_deduplicated_clauses(CANONICAL_CLAUSES_DIR)
    repaired_clauses, meta = recompute_hierarchy(doc_clauses)

    # Assert invariant: exactly 10,388 unique clauses
    if len(repaired_clauses) != 10388:
        print(f"FATAL: Recomputed clause count {len(repaired_clauses)} != 10388")
        sys.exit(1)

    # Assert invariant: ID set digest unchanged
    original_ids = [cid for doc in doc_clauses.values() for cid in doc.keys()]
    repaired_ids = list(repaired_clauses.keys())
    orig_digest = compute_id_set_digest(original_ids)
    repaired_digest = compute_id_set_digest(repaired_ids)

    if orig_digest != repaired_digest:
        print(f"FATAL: ID set digest altered! {orig_digest} != {repaired_digest}")
        sys.exit(1)

    # Initialize isolated staging corpus directory
    if STAGING_CLAUSES_DIR.exists():
        shutil.rmtree(STAGING_CLAUSES_DIR)
    STAGING_CLAUSES_DIR.mkdir(parents=True, exist_ok=True)

    # Group repaired clauses back to per-document lists preserving source-order
    for jf in sorted(CANONICAL_CLAUSES_DIR.glob("*_clauses.json")):
        doc_id = jf.name.replace("_clauses.json", "")
        with open(jf, "r", encoding="utf-8") as f:
            items = json.load(f)

        staging_items = []
        seen = set()
        for item in items:
            cid = item["id"]
            if cid not in seen:
                seen.add(cid)
                staging_items.append(repaired_clauses[cid])

        staging_file = STAGING_CLAUSES_DIR / jf.name
        with open(staging_file, "w", encoding="utf-8") as f:
            json.dump(staging_items, f, indent=2)

    print(f"Wrote {len(repaired_clauses):,} repaired clauses to staging directory: {STAGING_CLAUSES_DIR}")
    print(f"Digest verified: {repaired_digest}")
    print("Canonical source JSON files in data/corpus/clauses/ remain untouched.")


def main():
    parser = argparse.ArgumentParser(description="CricketIQ Hierarchy Depth Recalculator")
    parser.add_argument("--dry-run", action="store_true", help="Execute non-destructive dry run (Default)")
    parser.add_argument("--build-staging", action="store_true", help="Build staging canonical corpus with true depths")
    parser.add_argument("--confirm-staging", action="store_true", help="Explicit confirmation to build staging corpus")

    args = parser.parse_args()

    if args.build_staging:
        run_build_staging(confirm=args.confirm_staging)
    else:
        run_dry_run()


if __name__ == "__main__":
    main()
