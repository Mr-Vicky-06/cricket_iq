"""CricketIQ Retrieval Subsystem."""

from cricketiq.backend.app.retrieval.contracts import (
    RetrievalRequest, RetrievalHit, RetrievalOutcome, RetrievalStatus, EvidenceRole
)
from cricketiq.backend.app.retrieval.exact_clause_lookup import ExactClauseLookupEngine
from cricketiq.backend.app.retrieval.sparse.sqlite_fts import SQLiteFTSSearchProvider
from cricketiq.backend.app.retrieval.dense.sqlite_numpy_search import SQLiteNumPyDenseSearchProvider
from cricketiq.backend.app.retrieval.fusion.rrf import RRFEngine
from cricketiq.backend.app.retrieval.expansion.evidence_expander import EvidenceExpander
from cricketiq.backend.app.retrieval.service import RetrievalService

__all__ = [
    "RetrievalRequest",
    "RetrievalHit",
    "RetrievalOutcome",
    "RetrievalStatus",
    "EvidenceRole",
    "ExactClauseLookupEngine",
    "SQLiteFTSSearchProvider",
    "SQLiteNumPyDenseSearchProvider",
    "RRFEngine",
    "EvidenceExpander",
    "RetrievalService"
]
