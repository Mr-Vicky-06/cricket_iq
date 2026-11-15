"""SQLite FTS5 Sparse Search Provider for CricketIQ.

Implements tokenization, punctuation handling, parameterized FTS5 queries,
column-weighted BM25 ranking, candidate-document scoping, and index synchronization.
"""

from __future__ import annotations
import re
from typing import List, Tuple, Optional, Set, Dict, Any
from sqlalchemy import text, select
from sqlalchemy.orm import Session

from cricketiq.backend.app.database.models import RuleClause
from cricketiq.backend.app.database.orm_models import RuleClauseEntity
from cricketiq.backend.app.database.repository import CricketIQRepository


class SQLiteFTSSearchProvider:
    """Sparse lexical search using SQLite FTS5 with BM25 ranking."""

    FTS_TABLE_NAME = "rule_clauses_fts"

    def __init__(self, repository: CricketIQRepository):
        self.repository = repository
        self.session: Session = repository.session
        self._ensure_table_exists()

    def _ensure_table_exists(self) -> None:
        """Create FTS5 virtual table if it does not exist."""
        sql = f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS {self.FTS_TABLE_NAME} USING fts5(
            clause_id UNINDEXED,
            source_document_id UNINDEXED,
            clause_number,
            heading,
            content,
            tokenize=porter
        );
        """
        self.session.execute(text(sql))
        self.session.commit()

    def rebuild_index(self) -> int:
        """Rebuild the entire FTS5 index from rule_clauses in the database."""
        # Clear existing FTS rows
        self.session.execute(text(f"DELETE FROM {self.FTS_TABLE_NAME}"))

        # Fetch all active clauses
        stmt = select(RuleClauseEntity)
        clauses = self.session.scalars(stmt).all()

        insert_sql = text(f"""
            INSERT INTO {self.FTS_TABLE_NAME} (clause_id, source_document_id, clause_number, heading, content)
            VALUES (:clause_id, :source_document_id, :clause_number, :heading, :content)
        """)

        count = 0
        for c in clauses:
            self.session.execute(insert_sql, {
                "clause_id": c.id,
                "source_document_id": c.source_document_id,
                "clause_number": c.clause_number,
                "heading": c.heading or "",
                "content": c.original_text or ""
            })
            count += 1

        self.session.commit()
        return count

    def sync_clause(self, clause: RuleClause) -> None:
        """Insert or replace a clause in the FTS5 index."""
        del_sql = text(f"DELETE FROM {self.FTS_TABLE_NAME} WHERE clause_id = :clause_id")
        self.session.execute(del_sql, {"clause_id": clause.id})

        insert_sql = text(f"""
            INSERT INTO {self.FTS_TABLE_NAME} (clause_id, source_document_id, clause_number, heading, content)
            VALUES (:clause_id, :source_document_id, :clause_number, :heading, :content)
        """)
        self.session.execute(insert_sql, {
            "clause_id": clause.id,
            "source_document_id": clause.source_document_id,
            "clause_number": clause.clause_number,
            "heading": clause.heading or "",
            "content": clause.original_text or ""
        })
        self.session.commit()

    def delete_clause(self, clause_id: str) -> None:
        """Remove a clause from the FTS5 index."""
        del_sql = text(f"DELETE FROM {self.FTS_TABLE_NAME} WHERE clause_id = :clause_id")
        self.session.execute(del_sql, {"clause_id": clause_id})
        self.session.commit()

    def build_fts_query(self, raw_query: str) -> Optional[str]:
        """Convert a user query into a safe SQLite FTS5 query string.

        Preserves domain terms like 'no-ball', 'free-hit', handles punctuation,
        and quotes terms to prevent syntax errors.
        """
        if not raw_query or not raw_query.strip():
            return None

        clean_text = raw_query.strip()

        # Extract multi-word phrases and compound terms (e.g. no-ball, free hit, run out)
        phrases: List[str] = []
        compounds = re.findall(r"\b[A-Za-z]+-[A-Za-z]+\b", clean_text)
        for comp in compounds:
            phrases.append(comp.replace("-", " "))

        # Check for well-known cricket key phrases
        lower = clean_text.lower()
        key_phrases = ["free hit", "no ball", "wide ball", "dead ball", "run out", "hit the ball twice", "obstructing the field"]
        for kp in key_phrases:
            if kp in lower and kp not in phrases:
                phrases.append(kp)

        # Extract alphanumeric words and dotted numbers (e.g. 21.18.2)
        tokens = re.findall(r"[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*", clean_text)
        # Filter single character tokens except digits or specific markers
        valid_tokens = [t for t in tokens if len(t) > 1 or t.isdigit()]

        if not valid_tokens and not phrases:
            return None

        # Build FTS terms
        parts: List[str] = []
        # Add exact phrases first
        for phrase in phrases:
            # Quote each word inside phrase for FTS5 phrase search e.g. "free hit"
            clean_p = " ".join(re.findall(r"[A-Za-z0-9]+", phrase))
            if clean_p:
                parts.append(f'"{clean_p}"')

        # Add individual tokens
        for tok in valid_tokens:
            # Escape quotes if any and wrap in double quotes
            safe_tok = tok.replace('"', '')
            if safe_tok:
                parts.append(f'"{safe_tok}"')

        if not parts:
            return None

        # Disjunction with OR allows high recall while BM25 weights multiple hits higher
        return " OR ".join(parts)

    def search(
        self,
        query: str,
        candidate_document_ids: Optional[List[str]] = None,
        top_k: int = 15
    ) -> List[Tuple[RuleClause, float]]:
        """Search clauses lexically with BM25 ranking and candidate document scoping."""
        if candidate_document_ids is not None and len(candidate_document_ids) == 0:
            return []

        fts_query_str = self.build_fts_query(query)
        if not fts_query_str:
            return []

        # Parameters dict
        params: Dict[str, Any] = {
            "match_query": fts_query_str,
            "limit": top_k
        }

        # Build candidate document filter clause
        doc_filter_sql = ""
        if candidate_document_ids is not None:
            doc_placeholders = []
            for i, doc_id in enumerate(candidate_document_ids):
                param_key = f"doc_{i}"
                doc_placeholders.append(f":{param_key}")
                params[param_key] = doc_id
            doc_filter_sql = f"AND source_document_id IN ({', '.join(doc_placeholders)})"

        # BM25 column weights: clause_number=10.0, heading=5.0, content=1.0
        # Lower BM25 rank is better in SQLite; ORDER BY rank ASC
        sql = f"""
            SELECT clause_id, bm25({self.FTS_TABLE_NAME}, 10.0, 5.0, 1.0) AS rank
            FROM {self.FTS_TABLE_NAME}
            WHERE {self.FTS_TABLE_NAME} MATCH :match_query
            {doc_filter_sql}
            ORDER BY rank ASC
            LIMIT :limit
        """

        try:
            result = self.session.execute(text(sql), params).fetchall()
        except Exception:
            # Graceful error handling for any unexpected FTS query issue
            return []

        if not result:
            return []

        clause_ids = [row[0] for row in result]
        ranks = {row[0]: row[1] for row in result}

        # Fetch full RuleClause entities
        stmt = select(RuleClauseEntity).where(RuleClauseEntity.id.in_(clause_ids))
        entities = {e.id: e for e in self.session.scalars(stmt).all()}

        hits: List[Tuple[RuleClause, float]] = []
        for cid in clause_ids:
            if cid in entities:
                clause = self.repository._entity_to_rule_clause(entities[cid])
                # Convert SQLite negative bm25 score to positive score: -rank
                raw_bm25 = ranks[cid]
                score = round(-float(raw_bm25), 6) if raw_bm25 is not None else 0.0
                hits.append((clause, score))

        return hits
