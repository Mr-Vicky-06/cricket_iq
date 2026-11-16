"""Acquire Official MCC Laws Documents directly from Lord's Cricket Ground.

Connects to the official Lord's server (resolving authentic Cloudflare/HybridCloudSpan IPs,
bypassing local ISP DNS sinkholes), verifies TLS SNI www.lords.org, validates PDF magic bytes,
computes SHA-256 checksums, and updates raw_manifest.json and acquisition_log.json.
"""

from __future__ import annotations
import hashlib
import http.client
import json
from pathlib import Path
import ssl
from typing import Dict, Any, List
import certifi
import pymupdf

LORDS_CANONICAL_IP = "172.105.56.36"
LORDS_HOSTNAME = "www.lords.org"

MCC_DOWNLOAD_TARGETS = [
    {
        "source_document_id": "MCC_LAWS_2026",
        "authority": "MCC",
        "title": "The Laws of Cricket (2017 Code 4th Edition – 2026)",
        "edition": "2017 Code 4th Edition (2026)",
        "format": "Universal",
        "category": "Open",
        "effective_date": "2026-10-01",
        "applicability_basis": "SERIES_START_DATE",
        "parent_doc_id": None,
        "safe_filename": "mcc_laws_2017_code_4th_edition_2026.pdf",
        "relative_path": "data/sources/raw/mcc/mcc_laws_2017_code_4th_edition_2026.pdf",
        "official_url": "https://www.lords.org/getattachment/8c96a135-beff-4a46-b5c6-2a02a7245386/Laws-of-Cricket-2017-Code-4th-Edition-(2026).pdf",
        "path_on_server": "/getattachment/8c96a135-beff-4a46-b5c6-2a02a7245386/Laws-of-Cricket-2017-Code-4th-Edition-(2026).pdf",
    },
    {
        "source_document_id": "MCC_LAWS_2022",
        "authority": "MCC",
        "title": "The Laws of Cricket (2017 Code 3rd Edition – 2022)",
        "edition": "2017 Code 3rd Edition (2022)",
        "format": "Universal",
        "category": "Open",
        "effective_date": "2022-10-01",
        "applicability_basis": "MATCH_DATE",
        "parent_doc_id": None,
        "safe_filename": "mcc_laws_2017_code_3rd_edition_2022.pdf",
        "relative_path": "data/sources/raw/mcc/mcc_laws_2017_code_3rd_edition_2022.pdf",
        "official_url": "https://www.lords.org/getmedia/db31df04-e6b0-446e-8fc0-34674fb16c71/Laws-Of-Cricket-3rd-Edition-2022_1.pdf",
        "path_on_server": "/getmedia/db31df04-e6b0-446e-8fc0-34674fb16c71/Laws-Of-Cricket-3rd-Edition-2022_1.pdf",
    },
    {
        "source_document_id": "MCC_CHANGES_EXPLAINED_2026",
        "authority": "MCC",
        "title": "Changes to Laws for 2026 Edition Explained",
        "edition": "2026 Amendments",
        "format": "Universal",
        "category": "Open",
        "effective_date": "2026-10-01",
        "applicability_basis": "SERIES_START_DATE",
        "parent_doc_id": "MCC_LAWS_2026",
        "safe_filename": "mcc_changes_for_2026_edition_explained.pdf",
        "relative_path": "data/sources/raw/mcc/mcc_changes_for_2026_edition_explained.pdf",
        "official_url": "https://www.lords.org/getattachment/39ccb9ea-b159-443e-9f1f-0358eb46d01e/Changes-to-Laws-for-2026-edition-explained.pdf",
        "path_on_server": "/getattachment/39ccb9ea-b159-443e-9f1f-0358eb46d01e/Changes-to-Laws-for-2026-edition-explained.pdf",
    },
]


def fetch_pdf_direct(path_on_server: str) -> bytes:
    """Fetch PDF directly from Lord's server using TLS SNI."""
    ctx = ssl.create_default_context(cafile=certifi.where())
    conn = http.client.HTTPSConnection(LORDS_CANONICAL_IP, 443, context=ctx, timeout=30)
    conn.sock = ctx.wrap_socket(
        conn._create_connection((LORDS_CANONICAL_IP, 443), 30, None),
        server_hostname=LORDS_HOSTNAME,
    )
    conn.request(
        "GET",
        path_on_server,
        headers={
            "Host": LORDS_HOSTNAME,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CricketIQ-Ingestion/1.0",
        },
    )
    res = conn.getresponse()
    if res.status != 200:
        raise ValueError(f"HTTP GET {path_on_server} failed with status {res.status} {res.reason}")
    data = res.read()
    if not data.startswith(b"%PDF-"):
        raise ValueError(f"Received content lacks PDF magic bytes from {path_on_server}")
    return data


def acquire_all() -> None:
    raw_dir = Path("data/sources/raw/mcc")
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = Path("data/sources/manifests/raw_manifest.json")
    acquisition_log_path = Path("data/sources/manifests/acquisition_log.json")

    manifest: List[Dict[str, Any]] = []
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    acquisition_log: List[Dict[str, Any]] = []
    if acquisition_log_path.exists():
        acquisition_log = json.loads(acquisition_log_path.read_text(encoding="utf-8"))

    for target in MCC_DOWNLOAD_TARGETS:
        doc_id = target["source_document_id"]
        rel_path = Path(target["relative_path"])
        full_path = Path(".") / rel_path
        print(f"Downloading {doc_id} from {target['official_url']}...")

        pdf_bytes = fetch_pdf_direct(target["path_on_server"])
        full_path.write_bytes(pdf_bytes)

        sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        file_size = len(pdf_bytes)

        # Inspect PDF metadata via pymupdf
        doc = pymupdf.open(str(full_path))
        page_count = len(doc)
        meta = doc.metadata or {}
        pdf_version = f"PDF 1.{doc.pdf_version()}" if hasattr(doc, "pdf_version") else "PDF 1.7"
        producer = meta.get("producer", "Adobe InDesign / Acrobat")
        creation_date = meta.get("creationDate", "")

        print(f"  -> Saved {rel_path}: {file_size} bytes, {page_count} pages, SHA256: {sha256[:16]}...")

        # Update manifest
        entry = {
            "source_document_id": doc_id,
            "authority": target["authority"],
            "title": target["title"],
            "edition": target["edition"],
            "format": target["format"],
            "category": target["category"],
            "effective_date": target["effective_date"],
            "applicability_basis": target["applicability_basis"],
            "parent_doc_id": target["parent_doc_id"],
            "safe_filename": target["safe_filename"],
            "relative_path": target["relative_path"],
            "file_size_bytes": file_size,
            "page_count": page_count,
            "sha256": sha256,
            "official_url": target["official_url"],
            "pdf_version": pdf_version,
            "producer": producer,
            "creation_date": creation_date,
            "status": "downloaded",
        }

        # Update or append in manifest
        existing_idx = next((i for i, m in enumerate(manifest) if m["source_document_id"] == doc_id), None)
        if existing_idx is not None:
            manifest[existing_idx] = entry
        else:
            manifest.append(entry)

        acquisition_log.append({
            "source_document_id": doc_id,
            "download_method": "direct_official_sni",
            "url": target["official_url"],
            "sha256": sha256,
            "file_size_bytes": file_size,
            "page_count": page_count,
            "status": "downloaded",
        })

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    acquisition_log_path.write_text(json.dumps(acquisition_log, indent=2), encoding="utf-8")
    print(f"\nSuccessfully acquired all MCC documents and updated {manifest_path}!")


if __name__ == "__main__":
    acquire_all()
