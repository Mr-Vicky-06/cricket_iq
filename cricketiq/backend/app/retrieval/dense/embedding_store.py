"""Persistent Versioned Vector Store for CricketIQ.

Manages vector serialization, metadata validation (model, dimension, hash, template),
atomic index rebuilds, and safe vector recovery without unvetted pickle files.
"""

from __future__ import annotations
import math
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
from sqlalchemy import text, select
from sqlalchemy.orm import Session

from cricketiq.backend.app.database.models import RuleClause, SourceDocument
from cricketiq.backend.app.database.orm_models import RuleClauseEntity, SourceDocumentEntity
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.retrieval.dense.base import EmbeddingProvider
from cricketiq.backend.app.retrieval.dense.embedding_provider import (
    build_clause_embedding_text, compute_text_hash, EMBEDDING_TEMPLATE_VERSION
)


class EmbeddingStore:
    """Manages versioned, persistent clause embeddings in SQLite."""

    TABLE_NAME = "clause_embeddings"
    STAGING_TABLE_NAME = "clause_embeddings_staging"

    def __init__(self, repository: CricketIQRepository, provider: EmbeddingProvider):
        self.repository = repository
        self.session: Session = repository.session
        self.provider = provider
        self._ensure_tables_exist()

    def _ensure_tables_exist(self) -> None:
        """Create primary and staging tables for embedding persistence."""
        table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
            clause_id VARCHAR(128) PRIMARY KEY,
            document_id VARCHAR(128) NOT NULL,
            model_name VARCHAR(64) NOT NULL,
            dimension INTEGER NOT NULL,
            template_version VARCHAR(16) NOT NULL,
            input_hash VARCHAR(64) NOT NULL,
            vector_blob BLOB NOT NULL,
            created_at VARCHAR(32) NOT NULL
        )
        """
        index_sql = f"CREATE INDEX IF NOT EXISTS idx_embeddings_doc ON {self.TABLE_NAME}(document_id)"
        self.session.execute(text(table_sql))
        self.session.execute(text(index_sql))
        self.session.commit()

    def get_store_metadata(self) -> Dict[str, Any]:
        """Inspect and return metadata describing vectors currently in storage."""
        sql = text(f"""
            SELECT DISTINCT model_name, dimension, template_version
            FROM {self.TABLE_NAME}
        """)
        rows = self.session.execute(sql).fetchall()
        count_sql = text(f"SELECT count(*) FROM {self.TABLE_NAME}")
        total = self.session.execute(count_sql).scalar() or 0

        models = list({r[0] for r in rows})
        dims = list({r[1] for r in rows})
        templates = list({r[2] for r in rows})

        is_consistent = len(models) == 1 and len(dims) == 1 and len(templates) == 1 and total > 0

        return {
            "total_rows": total,
            "distinct_models": models,
            "distinct_dimensions": dims,
            "distinct_templates": templates,
            "is_consistent": is_consistent,
            "model_name": models[0] if len(models) == 1 else None,
            "dimension": dims[0] if len(dims) == 1 else None,
            "template_version": templates[0] if len(templates) == 1 else None,
            "is_semantic_model": (models[0] != "local-deterministic-v1") if len(models) == 1 else False
        }

    def _validate_vector(self, vec: List[float]) -> np.ndarray:
        """Validate vector dimensionality, finiteness, and norm."""
        if len(vec) != self.provider.dimension:
            raise ValueError(f"Vector dimension mismatch: expected {self.provider.dimension}, got {len(vec)}")

        arr = np.array(vec, dtype=np.float32)
        if not np.all(np.isfinite(arr)):
            raise ValueError("Vector contains non-finite values (NaN or Inf)")

        norm = float(np.linalg.norm(arr))
        if norm == 0.0:
            raise ValueError("Vector has zero magnitude")

        return arr

    def build_all_embeddings(self) -> int:
        """Atomically rebuild embeddings for all active clauses using staging table."""
        # 1. Fetch all documents and clauses
        docs = {d.id: d for d in self.repository.list_active_documents()}
        clauses = self.session.scalars(select(RuleClauseEntity)).all()

        if not clauses:
            return 0

        # 2. Setup staging table
        self.session.execute(text(f"DROP TABLE IF EXISTS {self.STAGING_TABLE_NAME}"))
        self.session.execute(text(f"""
            CREATE TABLE {self.STAGING_TABLE_NAME} (
                clause_id VARCHAR(128) PRIMARY KEY,
                document_id VARCHAR(128) NOT NULL,
                model_name VARCHAR(64) NOT NULL,
                dimension INTEGER NOT NULL,
                template_version VARCHAR(16) NOT NULL,
                input_hash VARCHAR(64) NOT NULL,
                vector_blob BLOB NOT NULL,
                created_at VARCHAR(32) NOT NULL
            )
        """))
        self.session.commit()

        # 3. Compute texts and hashes
        domain_clauses = [self.repository._entity_to_rule_clause(c) for c in clauses]
        texts_to_embed: List[str] = []
        hashes: List[str] = []
        for c in domain_clauses:
            doc = docs.get(c.source_document_id)
            embed_text = build_clause_embedding_text(c, doc)
            texts_to_embed.append(embed_text)
            hashes.append(compute_text_hash(embed_text))

        # 4. Generate batch embeddings
        vectors = self.provider.embed_batch(texts_to_embed)

        # 5. Insert into staging table with validation
        now_iso = datetime.now(timezone.utc).isoformat()
        insert_sql = text(f"""
            INSERT INTO {self.STAGING_TABLE_NAME} (
                clause_id, document_id, model_name, dimension,
                template_version, input_hash, vector_blob, created_at
            ) VALUES (
                :clause_id, :document_id, :model_name, :dimension,
                :template_version, :input_hash, :vector_blob, :created_at
            )
        """)

        for c, h, vec in zip(domain_clauses, hashes, vectors):
            valid_arr = self._validate_vector(vec)
            self.session.execute(insert_sql, {
                "clause_id": c.id,
                "document_id": c.source_document_id,
                "model_name": self.provider.model_name,
                "dimension": self.provider.dimension,
                "template_version": EMBEDDING_TEMPLATE_VERSION,
                "input_hash": h,
                "vector_blob": valid_arr.tobytes(),
                "created_at": now_iso
            })

        # 6. Atomic swap: replace production table with staging table in a single transaction
        self.session.execute(text(f"DELETE FROM {self.TABLE_NAME}"))
        self.session.execute(text(f"INSERT INTO {self.TABLE_NAME} SELECT * FROM {self.STAGING_TABLE_NAME}"))
        self.session.execute(text(f"DROP TABLE {self.STAGING_TABLE_NAME}"))
        self.session.commit()

        return len(domain_clauses)

    def load_embeddings(
        self,
        candidate_document_ids: Optional[List[str]] = None
    ) -> Dict[str, Tuple[str, np.ndarray]]:
        """Load stored embeddings as numpy arrays.

        Returns:
            Dict mapping clause_id -> (document_id, numpy_vector)
        """
        if candidate_document_ids is not None and len(candidate_document_ids) == 0:
            return {}

        params: Dict[str, Any] = {
            "model_name": self.provider.model_name,
            "dimension": self.provider.dimension
        }

        doc_filter = ""
        if candidate_document_ids is not None:
            placeholders = []
            for i, doc_id in enumerate(candidate_document_ids):
                k = f"doc_{i}"
                placeholders.append(f":{k}")
                params[k] = doc_id
            doc_filter = f"AND document_id IN ({', '.join(placeholders)})"

        sql = f"""
            SELECT clause_id, document_id, vector_blob
            FROM {self.TABLE_NAME}
            WHERE model_name = :model_name AND dimension = :dimension
            {doc_filter}
        """

        rows = self.session.execute(text(sql), params).fetchall()
        result: Dict[str, Tuple[str, np.ndarray]] = {}

        for row in rows:
            cid, did, blob = row[0], row[1], row[2]
            vec = np.frombuffer(blob, dtype=np.float32)
            result[cid] = (did, vec)

        return result
