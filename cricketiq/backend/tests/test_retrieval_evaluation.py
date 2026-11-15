"""Automated benchmark regression test for CricketIQ Retrieval Subsystem (Gate 6).
"""

import json
from pathlib import Path
from evaluation.retrieval.evaluate_retrieval import (
    setup_benchmark_environment, evaluate_configuration
)
from cricketiq.backend.app.retrieval.sparse.sqlite_fts import SQLiteFTSSearchProvider
from cricketiq.backend.app.retrieval.dense.embedding_provider import LocalDeterministicEmbeddingProvider
from cricketiq.backend.app.retrieval.dense.embedding_store import EmbeddingStore
from cricketiq.backend.app.retrieval.dense.sqlite_numpy_search import SQLiteNumPyDenseSearchProvider
from cricketiq.backend.app.retrieval.service import RetrievalService


def test_benchmark_hybrid_quality_thresholds():
    """Verify that hybrid retrieval meets strict regression thresholds on benchmark_v1."""
    benchmark_path = Path("evaluation/retrieval/benchmark_v1.jsonl")
    assert benchmark_path.exists(), "benchmark_v1.jsonl must exist"

    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark_items = [json.loads(line) for line in f if line.strip()]

    assert len(benchmark_items) >= 60

    repo = setup_benchmark_environment()

    # Providers
    sparse_prov = SQLiteFTSSearchProvider(repo)
    sparse_prov.rebuild_index()

    embedder = LocalDeterministicEmbeddingProvider(dimension=384)
    store = EmbeddingStore(repo, embedder)
    store.build_all_embeddings()
    dense_prov = SQLiteNumPyDenseSearchProvider(repo, embedder, store)

    service = RetrievalService(
        repository=repo,
        sparse_provider=sparse_prov,
        dense_provider=dense_prov
    )

    results = evaluate_configuration(service, benchmark_items, mode="Hybrid")

    # Hard Quality Invariants
    assert results["leakage_rate"] == 0.0, f"Regulatory leakage must be exactly 0.0%, got {results['leakage_rate']}%"
    assert results["exact_clause_accuracy"] >= 95.0, f"Exact accuracy must be >= 95%, got {results['exact_clause_accuracy']}%"
    assert results["supporting_clause_recall"] >= 90.0, f"Supporting clause recall must be >= 90%, got {results['supporting_clause_recall']}%"
    assert results["recall_at_5"] >= 85.0, f"Recall@5 must be >= 85%, got {results['recall_at_5']}%"
    assert results["latencies_ms"]["avg_total"] < 100.0, "Average latency must be under 100ms"
