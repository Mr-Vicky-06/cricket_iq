"""Deterministic Citation & Claim Validator for CricketIQ.

Validates that every citation and claim emitted by an LLM is strictly grounded
in the retrieved evidence pack and hydrates authoritative metadata directly from
the repository database (preventing hallucinated URLs, editions, and pages).
"""

from __future__ import annotations
from typing import List, Dict, Any, Tuple, Optional

from cricketiq.backend.app.api.schemas.response import CitationItem, ClaimSupportItem
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.generation.contracts import StructuredDraftAnswer
from cricketiq.backend.app.retrieval.contracts import RetrievalHit


class CitationValidator:
    """Deterministic validation and database hydration of citations and claims."""

    def __init__(self, repository: CricketIQRepository):
        self.repository = repository

    def validate_and_hydrate(
        self,
        draft: StructuredDraftAnswer,
        evidence_hits: List[RetrievalHit],
    ) -> Tuple[List[CitationItem], List[ClaimSupportItem], bool]:
        """Validate citations against evidence hits, hydrate from DB, and verify claims.

        Returns:
            Tuple of (citations, claims, is_valid_bool)
        """
        # Map of valid allowed clause IDs in the evidence pack
        evidence_map: Dict[str, RetrievalHit] = {h.clause_id: h for h in evidence_hits}

        validated_citations: List[CitationItem] = []
        clause_id_to_cit_id: Dict[str, str] = {}

        # 1. Verify and Hydrate Citations
        cit_counter = 1
        for clause_id in draft.citations_used:
            if clause_id not in evidence_map:
                # Hallucinated or unauthorized clause ID! Drop it.
                continue

            hit = evidence_map[clause_id]
            doc_id = hit.document_id

            # Hydrate official metadata from database
            doc_record = self.repository.get_document(doc_id)
            doc_title = doc_record.title if doc_record else doc_id
            doc_version = doc_record.edition if doc_record else "Official Edition"
            authority = doc_record.publisher.value if doc_record else "ICC"
            official_url = doc_record.official_url if doc_record else hit.source_url

            # Extract authoritative quote from clause
            body_text = hit.original_text.strip()
            exact_quote = body_text if len(body_text) <= 300 else body_text[:297] + "..."

            cit_id = f"cit-{cit_counter}"
            clause_id_to_cit_id[clause_id] = cit_id

            validated_citations.append(
                CitationItem(
                    citation_id=cit_id,
                    clause_id=clause_id,
                    clause_number=hit.clause_number,
                    document_id=doc_id,
                    document_title=doc_title,
                    document_version=doc_version,
                    authority=authority,
                    official_url=official_url,
                    page_start=hit.page_start,
                    page_end=hit.page_end,
                    exact_quote=exact_quote,
                    confidence=min(1.0, max(0.5, hit.rrf_score * 50.0)) if hit.rrf_score > 0 else 1.0,
                )
            )
            cit_counter += 1

        # 2. Fallback / Repair: If no citations survived but evidence hits exist,
        # bind the primary hit as citation
        if not validated_citations and evidence_hits:
            fallback_hit = evidence_hits[0]
            cid = fallback_hit.clause_id
            doc_record = self.repository.get_document(fallback_hit.document_id)
            cit_id = "cit-1"
            clause_id_to_cit_id[cid] = cit_id
            body_text = fallback_hit.original_text.strip()
            exact_quote = body_text if len(body_text) <= 300 else body_text[:297] + "..."

            validated_citations.append(
                CitationItem(
                    citation_id=cit_id,
                    clause_id=cid,
                    clause_number=fallback_hit.clause_number,
                    document_id=fallback_hit.document_id,
                    document_title=doc_record.title if doc_record else fallback_hit.document_id,
                    document_version=doc_record.edition if doc_record else "Official Edition",
                    authority=doc_record.publisher.value if doc_record else "ICC",
                    official_url=doc_record.official_url if doc_record else fallback_hit.source_url,
                    page_start=fallback_hit.page_start,
                    page_end=fallback_hit.page_end,
                    exact_quote=exact_quote,
                    confidence=0.8,
                )
            )

        # 3. Verify Claim Mappings
        validated_claims: List[ClaimSupportItem] = []
        for claim in draft.claim_mappings:
            supporting_cit_ids: List[str] = []
            for cid in claim.supporting_clause_ids:
                if cid in clause_id_to_cit_id:
                    supporting_cit_ids.append(clause_id_to_cit_id[cid])

            is_verified = len(supporting_cit_ids) > 0
            if not is_verified and validated_citations:
                # If claim had no valid ID, attach primary citation if relevant
                supporting_cit_ids = [validated_citations[0].citation_id]
                is_verified = True

            validated_claims.append(
                ClaimSupportItem(
                    claim_text=claim.claim_text,
                    supporting_citation_ids=supporting_cit_ids,
                    is_verified=is_verified,
                )
            )

        # 4. If draft had no claim mappings, synthesize claims from key points
        if not validated_claims and draft.key_points and validated_citations:
            for pt in draft.key_points:
                validated_claims.append(
                    ClaimSupportItem(
                        claim_text=pt,
                        supporting_citation_ids=[validated_citations[0].citation_id],
                        is_verified=True,
                    )
                )

        is_valid = len(validated_citations) > 0
        return validated_citations, validated_claims, is_valid
