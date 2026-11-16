#!/usr/bin/env python3
"""Build Multi-View Normalized Corpus for all extracted cricket rule documents.

Reads:
- data/sources/manifests/raw_manifest.json
- data/corpus/clauses/{doc_id}_clauses.json

Outputs:
- data/corpus/normalized/{doc_id}_normalized.json (all 7 text views)
- data/corpus/metadata/{doc_id}_metadata.json
- data/corpus/corpus_manifest.json (master manifest)
"""

import json
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from cricketiq.backend.app.nlp.normalizer import TextNormalizer, NORMALIZATION_VERSION, PIPELINE_VERSION

def main():
    manifest_path = root_dir / "data" / "sources" / "manifests" / "raw_manifest.json"
    clauses_dir = root_dir / "data" / "corpus" / "clauses"
    norm_dir = root_dir / "data" / "corpus" / "normalized"
    meta_dir = root_dir / "data" / "corpus" / "metadata"

    norm_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    normalizer = TextNormalizer(normalization_version=NORMALIZATION_VERSION)
    master_corpus_summary = []
    total_clauses_processed = 0

    print(f"Building normalized multi-view corpus for {len(manifest)} documents...\n")

    for item in manifest:
        doc_id = item["source_document_id"]
        clause_file = clauses_dir / f"{doc_id}_clauses.json"
        if not clause_file.exists():
            print(f"Skipping {doc_id} (clauses file not found)")
            continue

        with open(clause_file, "r", encoding="utf-8") as f:
            raw_clauses = json.load(f)

        # Build map for fast parent lookup
        clause_map = {c["clause_number"]: c for c in raw_clauses}

        normalized_records = []
        for c in raw_clauses:
            clause_num = c["clause_number"]
            parent_id = c.get("parent_clause_id")
            parent_text = ""
            if parent_id and ":" in parent_id:
                p_num = parent_id.split(":", 1)[1]
                if p_num in clause_map:
                    parent_text = clause_map[p_num].get("original_text", "")

            view_record = normalizer.build_views(
                clause_id=c["id"],
                source_document_id=doc_id,
                clause_number=clause_num,
                heading=c.get("heading") or f"Clause {clause_num}",
                original_text=c.get("original_text", ""),
                authority=item["authority"],
                document_title=item["title"],
                edition=item["edition"],
                page_start=c.get("page_start", 1),
                parent_clause_id=parent_id,
                parent_clause_text=parent_text,
                clause_type=c.get("clause_type", "RULE")
            )
            normalized_records.append(view_record.to_dict())

        # Write normalized JSON
        norm_output_path = norm_dir / f"{doc_id}_normalized.json"
        with open(norm_output_path, "w", encoding="utf-8") as f:
            json.dump(normalized_records, f, indent=2)

        # Write metadata JSON
        meta_payload = {
            "source_document_id": doc_id,
            "authority": item["authority"],
            "title": item["title"],
            "edition": item["edition"],
            "format": item["format"],
            "category": item["category"],
            "effective_date": item.get("effective_date"),
            "applicability_basis": item.get("applicability_basis"),
            "parent_doc_id": item.get("parent_doc_id"),
            "pipeline_version": PIPELINE_VERSION,
            "normalization_version": NORMALIZATION_VERSION,
            "total_clauses": len(normalized_records),
            "views_generated": ["original_text", "normalized_text", "lexical_text", "embedding_text", "sentence_segments", "chunks", "display_text"]
        }
        with open(meta_dir / f"{doc_id}_metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta_payload, f, indent=2)

        total_clauses_processed += len(normalized_records)
        master_corpus_summary.append(meta_payload)
        print(f"  -> Generated {len(normalized_records)} multi-view records for {doc_id}")

    # Write master corpus manifest
    with open(root_dir / "data" / "corpus" / "corpus_manifest.json", "w", encoding="utf-8") as f:
        json.dump({
            "manifest_version": "1.0.0",
            "pipeline_version": PIPELINE_VERSION,
            "normalization_version": NORMALIZATION_VERSION,
            "total_documents": len(master_corpus_summary),
            "total_clauses": total_clauses_processed,
            "documents": master_corpus_summary
        }, f, indent=2)

    print(f"\nCorpus normalization complete! Total documents: {len(master_corpus_summary)}, Total clauses: {total_clauses_processed}")

if __name__ == "__main__":
    main()
