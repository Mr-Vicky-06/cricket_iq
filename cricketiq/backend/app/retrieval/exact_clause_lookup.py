"""Exact Clause Lookup Engine for CricketIQ.

Deterministically detects and extracts dotted clause identifiers (e.g. '21.18.2', '21.18', '22.1')
and retrieves the exact matching RuleClause within the applicable source bundle.
"""

from __future__ import annotations
import re
from typing import List, Optional, Tuple, Set
from sqlalchemy import select

from cricketiq.backend.app.database.models import RuleClause
from cricketiq.backend.app.database.orm_models import RuleClauseEntity
from cricketiq.backend.app.database.repository import CricketIQRepository

EXACT_CLAUSE_PATTERN = re.compile(
    r"(?:(?:clause|law|rule|section)\s+)?\b([0-9]{1,2}(?:\.[0-9]{1,2}(?:\.[0-9]{1,2})?)?)\b",
    re.IGNORECASE
)


class ExactClauseLookupEngine:
    """Detects and executes exact clause lookups against candidate documents."""

    def __init__(self, repository: CricketIQRepository):
        self.repository = repository
        self.session = repository.session

    def extract_clause_identifiers(self, query: str) -> List[str]:
        """Extract candidate clause numbers from query string."""
        matches = EXACT_CLAUSE_PATTERN.findall(query.strip())
        # Filter out isolated single digits unless prefixed by Law/Clause
        valid_ids: List[str] = []
        for m in matches:
            if "." in m or len(m) >= 2 or re.search(rf"(?:clause|law)\s+{re.escape(m)}\b", query, re.I):
                if m not in valid_ids:
                    valid_ids.append(m)
        return valid_ids

    def lookup(
        self,
        query: str,
        candidate_document_ids: Optional[List[str]] = None
    ) -> List[Tuple[RuleClause, float]]:
        """Perform exact clause lookup within candidate document scope.

        Returns list of (clause, confidence_score) where confidence is 1.0 for exact matches.
        """
        extracted_nums = self.extract_clause_identifiers(query)
        if not extracted_nums:
            return []

        # If candidate_document_ids is explicitly empty list, no documents are applicable
        if candidate_document_ids is not None and len(candidate_document_ids) == 0:
            return []

        results: List[Tuple[RuleClause, float]] = []
        seen_clause_ids: Set[str] = set()

        for c_num in extracted_nums:
            stmt = select(RuleClauseEntity).where(RuleClauseEntity.clause_number == c_num)
            if candidate_document_ids is not None:
                stmt = stmt.where(RuleClauseEntity.source_document_id.in_(candidate_document_ids))

            entities = self.session.scalars(stmt).all()
            for entity in entities:
                clause = self.repository._entity_to_rule_clause(entity)
                if clause.id not in seen_clause_ids:
                    # Give exact clause matches top confidence score
                    results.append((clause, 1.0))
                    seen_clause_ids.add(clause.id)

        return results
