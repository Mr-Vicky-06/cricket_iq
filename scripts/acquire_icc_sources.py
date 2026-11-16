#!/usr/bin/env python3
"""Acquire Tier 1 ICC Playing Conditions PDFs securely."""

import json
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import fitz
from cricketiq.backend.app.ingestion.secure_downloader import SecureDocumentDownloader

TARGETS = [
    {
        "doc_id": "ICC_TEST_MEN_2026",
        "url": "https://images.icc-cricket.com/image/upload/prd/a8114zro5tkioifz0jqg.pdf",
        "safe_name": "icc_mens_test_pc_2026.pdf",
        "title": "Men's Test Match Playing Conditions",
        "format": "Test",
        "category": "Men's",
        "effective_date": "2026-10-01",
        "applicability_basis": "SERIES_START_DATE",
        "parent_doc_id": None
    },
    {
        "doc_id": "ICC_ODI_MEN_2026",
        "url": "https://images.icc-cricket.com/image/upload/prd/bxkzkcyvfn6tvi70zh0w.pdf",
        "safe_name": "icc_mens_odi_pc_2026.pdf",
        "title": "Men's One Day International Playing Conditions",
        "format": "ODI",
        "category": "Men's",
        "effective_date": "2026-10-01",
        "applicability_basis": "SERIES_START_DATE",
        "parent_doc_id": None
    },
    {
        "doc_id": "ICC_T20I_MEN_2026",
        "url": "https://images.icc-cricket.com/image/upload/prd/bsxcho7ufe2pjban0wjp.pdf",
        "safe_name": "icc_mens_t20i_pc_2026.pdf",
        "title": "Men's Twenty20 International Playing Conditions",
        "format": "T20I",
        "category": "Men's",
        "effective_date": "2026-10-01",
        "applicability_basis": "SERIES_START_DATE",
        "parent_doc_id": None
    },
    {
        "doc_id": "ICC_T20I_MEN_ADD_2026",
        "url": "https://images.icc-cricket.com/image/upload/prd/pzyejpstlhptewq9qs2n.pdf",
        "safe_name": "icc_mens_t20i_addendum_2026.pdf",
        "title": "Addendum to Men's T20I Playing Conditions",
        "format": "T20I",
        "category": "Men's",
        "effective_date": "2026-10-01",
        "applicability_basis": "SERIES_START_DATE",
        "parent_doc_id": "ICC_T20I_MEN_2026"
    },
    {
        "doc_id": "ICC_TEST_WOMEN_2026",
        "url": "https://images.icc-cricket.com/image/upload/prd/hbwwi78pugzpdwft0v4v.pdf",
        "safe_name": "icc_womens_test_pc_2026.pdf",
        "title": "Women's Test Match Playing Conditions",
        "format": "Test",
        "category": "Women's",
        "effective_date": "2026-10-01",
        "applicability_basis": "SERIES_START_DATE",
        "parent_doc_id": None
    },
    {
        "doc_id": "ICC_ODI_WOMEN_2026",
        "url": "https://images.icc-cricket.com/image/upload/prd/qunpw1kfh3ibxlz58jlw.pdf",
        "safe_name": "icc_womens_odi_pc_2026.pdf",
        "title": "Women's One Day International Playing Conditions",
        "format": "ODI",
        "category": "Women's",
        "effective_date": "2026-10-01",
        "applicability_basis": "SERIES_START_DATE",
        "parent_doc_id": None
    },
    {
        "doc_id": "ICC_T20I_WOMEN_2026",
        "url": "https://images.icc-cricket.com/image/upload/prd/o3vhm0zw7pppoxpgopke.pdf",
        "safe_name": "icc_womens_t20i_pc_2026.pdf",
        "title": "Women's Twenty20 International Playing Conditions",
        "format": "T20I",
        "category": "Women's",
        "effective_date": "2026-10-01",
        "applicability_basis": "SERIES_START_DATE",
        "parent_doc_id": None
    },
    {
        "doc_id": "ICC_WTC_2025_2027_PC",
        "url": "https://images.icc-cricket.com/image/upload/prd/jrwhpcwk8mmpv0fx3lnd.pdf",
        "safe_name": "icc_wtc_2025_2027_pc.pdf",
        "title": "World Test Championship 2025–2027 Playing Conditions",
        "format": "Test",
        "category": "Men's",
        "effective_date": "2026-10-01",
        "applicability_basis": "COMPETITION_START_DATE",
        "parent_doc_id": "ICC_TEST_MEN_2026"
    }
]

def main():
    root = Path(__file__).resolve().parent.parent
    raw_icc_dir = root / "data" / "sources" / "raw" / "icc"
    raw_icc_dir.mkdir(parents=True, exist_ok=True)
    downloader = SecureDocumentDownloader(dest_dir=raw_icc_dir)

    manifest_entries = []
    acquisition_logs = []

    for item in TARGETS:
        dest_file = raw_icc_dir / item["safe_name"]
        print(f"Fetching {item['doc_id']} from {item['url']}...")
        try:
            temp_path, sha256_hash = downloader.download_pdf(item["url"])
            if dest_file.exists():
                dest_file.unlink()
            temp_path.rename(dest_file)

            # Validate with PyMuPDF
            doc = fitz.open(dest_file)
            page_count = len(doc)
            file_size = dest_file.stat().st_size
            meta = doc.metadata
            doc.close()

            manifest_entry = {
                "source_document_id": item["doc_id"],
                "authority": "ICC",
                "title": item["title"],
                "edition": "October 2026",
                "format": item["format"],
                "category": item["category"],
                "effective_date": item["effective_date"],
                "applicability_basis": item["applicability_basis"],
                "parent_doc_id": item["parent_doc_id"],
                "safe_filename": item["safe_name"],
                "relative_path": f"data/sources/raw/icc/{item['safe_name']}",
                "file_size_bytes": file_size,
                "page_count": page_count,
                "sha256": sha256_hash,
                "official_url": item["url"],
                "pdf_version": meta.get("format", "PDF"),
                "producer": meta.get("producer", ""),
                "creation_date": meta.get("creationDate", ""),
                "status": "downloaded"
            }
            manifest_entries.append(manifest_entry)

            log_entry = {
                "source_document_id": item["doc_id"],
                "url": item["url"],
                "status": "SUCCESS",
                "sha256": sha256_hash,
                "file_size_bytes": file_size,
                "page_count": page_count
            }
            acquisition_logs.append(log_entry)
            print(f"  -> OK: {item['doc_id']} ({page_count} pages, {file_size:,} bytes, SHA-256: {sha256_hash[:12]}...)")
        except Exception as err:
            print(f"  -> FAILED: {item['doc_id']}: {err}")
            acquisition_logs.append({
                "source_document_id": item["doc_id"],
                "url": item["url"],
                "status": "FAILED",
                "error": str(err)
            })

    manifests_dir = root / "data" / "sources" / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)

    with open(manifests_dir / "raw_icc_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_entries, f, indent=2)

    with open(manifests_dir / "acquisition_log.json", "w", encoding="utf-8") as f:
        json.dump(acquisition_logs, f, indent=2)

    print(f"\nCompleted ICC acquisition. Total successful: {len(manifest_entries)}/{len(TARGETS)}")

if __name__ == "__main__":
    main()
