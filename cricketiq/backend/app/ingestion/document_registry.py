"""Source Document Registry for CricketIQ.

Manages registration, verification, metadata, SHA-256 integrity,
and lifecycle status of official MCC and ICC regulatory documents.
"""

from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from cricketiq.backend.app.database.models import (
    SourceDocument, DocumentAuthority, DocumentType,
    CricketFormat, GenderCategory, DocumentStatus
)

OFFICIAL_ALLOWED_DOMAINS = {
    "icc-cricket.com",
    "www.icc-cricket.com",
    "resources.pulse.icc-cricket.com",
    "lords.org",
    "www.lords.org",
}


class DocumentRegistry:
    """In-memory and file-backed source document registry."""

    def __init__(self, registry_file: Optional[Path] = None):
        if registry_file is None:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            self.registry_file = base_dir / "data" / "source_registry" / "registry.json"
        else:
            self.registry_file = Path(registry_file)
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        self._documents: Dict[str, SourceDocument] = {}
        self.load()

    def load(self) -> None:
        """Load registry from JSON file if it exists."""
        if self.registry_file.exists():
            with open(self.registry_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._documents = {doc_id: SourceDocument(**doc) for doc_id, doc in data.items()}

    def save(self) -> None:
        """Persist registry to JSON file."""
        with open(self.registry_file, "w", encoding="utf-8") as f:
            data = {doc_id: doc.model_dump() for doc_id, doc in self._documents.items()}
            json.dump(data, f, indent=2)

    @staticmethod
    def calculate_sha256(file_path: Path) -> str:
        """Compute SHA-256 hash of a file for integrity verification."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def is_official_url(url: str) -> bool:
        """Verify if a URL belongs to the approved official publishers."""
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        return any(hostname == d or hostname.endswith("." + d) for d in OFFICIAL_ALLOWED_DOMAINS)

    def register_document(
        self,
        id: str,
        publisher: DocumentAuthority,
        title: str,
        document_type: DocumentType,
        edition: str,
        official_url: str,
        file_path: Optional[Path] = None,
        sha256: Optional[str] = None,
        format: CricketFormat = CricketFormat.GENERAL,
        category: GenderCategory = GenderCategory.UNIVERSAL,
        competition: Optional[str] = None,
        published_at: Optional[str] = None,
        effective_from: Optional[str] = None,
        effective_until: Optional[str] = None,
        status: DocumentStatus = DocumentStatus.CANDIDATE,
        terms_notes: str = ""
    ) -> SourceDocument:
        """Register a new official document with validation."""
        if not self.is_official_url(official_url):
            raise ValueError(f"URL '{official_url}' is not from an approved official publisher domain.")

        if file_path is not None and Path(file_path).exists():
            computed_hash = self.calculate_sha256(Path(file_path))
            if sha256 and sha256.lower() != computed_hash.lower():
                raise ValueError(f"SHA-256 mismatch for {file_path}. Expected: {sha256}, Got: {computed_hash}")
            sha256 = computed_hash
        elif not sha256:
            raise ValueError("Either an existing file_path or a verified sha256 hash must be provided.")

        doc = SourceDocument(
            id=id,
            publisher=publisher,
            title=title,
            document_type=document_type,
            format=format,
            category=category,
            competition=competition,
            edition=edition,
            published_at=published_at,
            effective_from=effective_from,
            effective_until=effective_until,
            official_url=official_url,
            sha256=sha256,
            file_path=str(file_path) if file_path else None,
            status=status,
            terms_notes=terms_notes
        )

        self._documents[id] = doc
        self.save()
        return doc

    def get(self, document_id: str) -> Optional[SourceDocument]:
        return self._documents.get(document_id)

    def list_all(self) -> List[SourceDocument]:
        return list(self._documents.values())

    def update_status(self, document_id: str, new_status: DocumentStatus) -> SourceDocument:
        doc = self._documents.get(document_id)
        if not doc:
            raise KeyError(f"Document {document_id} not found in registry.")
        doc.status = new_status
        self.save()
        return doc
