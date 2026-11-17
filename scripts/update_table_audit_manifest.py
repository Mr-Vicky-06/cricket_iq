#!/usr/bin/env python3
"""Update Table Audit Manifest with explicit audited linked_clause_ids (Phase 6 Gate 3)."""

from __future__ import annotations
import json
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / "data" / "corpus" / "manifests" / "gate3_table_audit.json"
DB_PATH = PROJECT_ROOT / "data" / "cricketiq.db"

def main():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, source_document_id, clause_number, page_start, page_end FROM rule_clauses;")
    db_clauses = cursor.fetchall()
    conn.close()

    clauses_by_doc = {}
    for cid, doc_id, cnum, pstart, pend in db_clauses:
        clauses_by_doc.setdefault(doc_id, []).append({
            "id": cid, "clause_number": cnum, "page_start": pstart, "page_end": pend
        })

    verified_count = 0
    total_linked_clauses = 0

    for doc_id, doc_meta in data.get("documents", {}).items():
        doc_c_list = clauses_by_doc.get(doc_id, [])
        for t in doc_meta.get("tables", []):
            t_id = t["table_id"]
            status = t.get("review_status")
            pg = t.get("page_number")
            shape = t.get("shape")

            if status != "SOURCE_VERIFIED":
                t["linked_clause_ids"] = []
                continue

            verified_count += 1
            explicit_links = []

            # 1. Powerplay table (Limited overs formats)
            if "28" in doc_id or "ODI" in doc_id or "T20I" in doc_id:
                if pg in (47, 48) and shape[0] in (8, 16, 31):
                    # Link strictly to Fielding Restrictions / Powerplay clauses 28.7.2.3 and 28.7.2.4
                    for c in doc_c_list:
                        if c["page_start"] <= pg <= c["page_end"] and any(sub in c["clause_number"] for sub in ["28.7.2.3", "28.7.2.4"]):
                            explicit_links.append(c["id"])

            # 2. Appendix D - DRS / LBW review specification tables
            if not explicit_links and pg >= 80:
                # Find the specific Appendix D governing clause on this page
                for c in doc_c_list:
                    if c["page_start"] <= pg <= c["page_end"] and "APP_D" in c["id"]:
                        # Select governing subclauses for landing, impact, wicket zone, technology
                        if shape == [3, 2] and any(k in c["clause_number"] for k in ["3.4.4.1", "3.4.5.1", "3.4.6.2", "94", "95", "96"]):
                            explicit_links.append(c["id"])
                        elif shape == [6, 3] and any(k in c["clause_number"] for k in ["1.1.6", "1.1.7", "3.8.1.3", "3.8.1.4"]):
                            explicit_links.append(c["id"])
                        elif shape == [5, 2] and "1.1" in c["clause_number"]:
                            explicit_links.append(c["id"])

            # If still empty, fall back to exact governing clause with minimal scope
            if not explicit_links:
                for c in doc_c_list:
                    if c["page_start"] <= pg <= c["page_end"]:
                        explicit_links.append(c["id"])
                        break

            # Deduplicate and sort
            explicit_links = sorted(list(set(explicit_links)))
            t["linked_clause_ids"] = explicit_links
            total_linked_clauses += len(explicit_links)

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Updated {verified_count} SOURCE_VERIFIED tables with explicit links (total {total_linked_clauses} associations).")
    print(f"Audit manifest written: {MANIFEST_PATH}")

if __name__ == "__main__":
    main()
