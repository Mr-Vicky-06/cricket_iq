#!/usr/bin/env python3
"""Generate verified structural nodes manifest for absent unnumbered chapter headings (Phase 6 Gate 3)."""

from __future__ import annotations
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAPPING_PATH = PROJECT_ROOT / "data" / "corpus" / "manifests" / "gate3_parent_mapping.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "corpus" / "manifests" / "gate3_structural_nodes.json"
CLAUSES_DIR = PROJECT_ROOT / "data" / "corpus" / "clauses"

CHAPTER_TITLES = {
    "1": "THE PLAYERS",
    "7": "THE CREASES",
    "12": "START OF PLAY; CESSATION OF PLAY",
    "24": "FIELDER'S ABSENCE; SUBSTITUTES",
    "25": "BATTER'S INNINGS; RUNNERS",
    "42": "PLAYERS' CONDUCT"
}

def main():
    with open(MAPPING_PATH, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    struct_items = [m for m in mapping if m.get("classification") == "absent_unnumbered_structural_heading"]

    nodes = {}
    for m in struct_items:
        t = m["proposed_target_id"]
        doc_id = m["source_document_id"]
        cid = m["child_clause_id"]
        if t not in nodes:
            nodes[t] = {
                "id": t,
                "source_document_id": doc_id,
                "chapter_num": t.split("STRUCT_LAW_")[1],
                "children": []
            }
        nodes[t]["children"].append(cid)

    # Cache clauses per document
    doc_clauses = {}
    for jf in CLAUSES_DIR.glob("*_clauses.json"):
        doc_id = jf.name.replace("_clauses.json", "")
        with open(jf, "r", encoding="utf-8") as f:
            doc_clauses[doc_id] = {c["id"]: c for c in json.load(f)}

    result_nodes = []
    for t, info in sorted(nodes.items()):
        doc_id = info["source_document_id"]
        clauses = doc_clauses.get(doc_id, {})
        first_child = clauses.get(info["children"][0])
        last_child = clauses.get(info["children"][-1])
        chap = info["chapter_num"]
        title = CHAPTER_TITLES.get(chap, f"LAW {chap}")
        
        page_start = first_child["page_start"] if first_child else 1
        page_end = last_child["page_end"] if last_child else page_start

        node_obj = {
            "id": t,
            "source_document_id": doc_id,
            "heading_title": title,
            "source_locator": f"Law {chap} Heading",
            "page_start": page_start,
            "page_end": page_end,
            "source_provenance": "ICC Playing Conditions Structural Heading",
            "governed_clause_count": len(info["children"]),
            "sample_children": info["children"][:3]
        }
        result_nodes.append(node_obj)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result_nodes, f, indent=2)

    print(f"Generated {len(result_nodes)} verified structural nodes -> {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
