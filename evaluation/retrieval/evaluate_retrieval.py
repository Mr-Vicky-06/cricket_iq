"""Benchmark Evaluation Runner for CricketIQ Retrieval Subsystem (Gate 6).

Evaluates Sparse-only, Dense-only, and Hybrid (RRF + Expansion) configurations against
evaluation/retrieval/benchmark_v1.jsonl measuring:
- Recall@5, Recall@10
- Mean Reciprocal Rank (MRR)
- Exact Clause Lookup Accuracy
- Supporting Clause Recall (after evidence expansion)
- Bundle Leakage Rate (must be 0.0%)
- Latency percentiles (sparse, dense, fusion, expansion, total)
"""

from __future__ import annotations
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import time
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy.orm import Session

from cricketiq.backend.app.database.connection import create_db_engine
from cricketiq.backend.app.database.orm_models import Base
from cricketiq.backend.app.database.models import (
    SourceDocument, RuleClause, DocumentAuthority, DocumentType, DocumentStatus,
    ClauseType, MatchContext, CricketFormat, GenderCategory, ScopeLevel
)
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.retrieval.contracts import (
    RetrievalRequest, RetrievalOutcome, RetrievalStatus, EvidenceRole
)
from cricketiq.backend.app.retrieval.dense.embedding_provider import LocalDeterministicEmbeddingProvider
from cricketiq.backend.app.retrieval.dense.embedding_store import EmbeddingStore
from cricketiq.backend.app.retrieval.dense.sqlite_numpy_search import SQLiteNumPyDenseSearchProvider
from cricketiq.backend.app.retrieval.sparse.sqlite_fts import SQLiteFTSSearchProvider
from cricketiq.backend.app.retrieval.fusion.rrf import RRFEngine
from cricketiq.backend.app.retrieval.expansion.evidence_expander import EvidenceExpander
from cricketiq.backend.app.retrieval.service import RetrievalService


def setup_benchmark_environment() -> CricketIQRepository:
    """Populate an in-memory repository with authentic ICC Playing Conditions clauses."""
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    repo = CricketIQRepository(session)

    # 1. ICC Men's T20I PC 2026
    t20_2026 = SourceDocument(
        id="ICC_T20I_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's Twenty20 International Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        scope_level=ScopeLevel.FORMAT_PC,
        edition="October 2026",
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        official_url="https://www.icc-cricket.com/t20i-2026.pdf",
        sha256="1" * 64,
        status=DocumentStatus.ACTIVE
    )
    # 2. ICC Men's T20I PC 2024 (Predecessor edition)
    t20_2024 = SourceDocument(
        id="ICC_T20I_MEN_2024",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's Twenty20 International Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        scope_level=ScopeLevel.FORMAT_PC,
        edition="October 2024",
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        official_url="https://www.icc-cricket.com/t20i-2024.pdf",
        sha256="0" * 64,
        status=DocumentStatus.ACTIVE
    )
    # 3. ICC Men's Test PC 2026
    test_2026 = SourceDocument(
        id="ICC_TEST_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's Test Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        scope_level=ScopeLevel.FORMAT_PC,
        edition="October 2026",
        format=CricketFormat.TEST,
        category=GenderCategory.MENS,
        official_url="https://www.icc-cricket.com/test-2026.pdf",
        sha256="2" * 64,
        status=DocumentStatus.ACTIVE
    )
    repo.upsert_source_document(t20_2026)
    repo.upsert_source_document(t20_2024)
    repo.upsert_source_document(test_2026)

    # Populate clauses for T20I 2026
    clauses = [
        RuleClause(
            id="ICC_T20I_MEN_2026:21",
            source_document_id=t20_2026.id,
            clause_number="21",
            heading="NO BALL",
            original_text="21 NO BALL. Law 21 shall apply subject to the following modifications.",
            clause_type=ClauseType.RULE,
            page_start=1,
            page_end=1
        ),
        RuleClause(
            id="ICC_T20I_MEN_2026:21.1",
            source_document_id=t20_2026.id,
            clause_number="21.1",
            parent_clause_id="ICC_T20I_MEN_2026:21",
            heading="Mode of delivery",
            original_text="21.1 Mode of delivery. The umpire shall ascertain whether the bowler intends to bowl right handed or left handed, over or round.",
            clause_type=ClauseType.RULE,
            page_start=1,
            page_end=1
        ),
        RuleClause(
            id="ICC_T20I_MEN_2026:21.1.1",
            source_document_id=t20_2026.id,
            clause_number="21.1.1",
            parent_clause_id="ICC_T20I_MEN_2026:21.1",
            heading="Bowler mode notification",
            original_text="The umpire shall ascertain whether the bowler intends to bowl right handed or left handed, over or round the wicket.",
            clause_type=ClauseType.RULE,
            page_start=1,
            page_end=1
        ),
        RuleClause(
            id="ICC_T20I_MEN_2026:21.1.2",
            source_document_id=t20_2026.id,
            clause_number="21.1.2",
            parent_clause_id="ICC_T20I_MEN_2026:21.1",
            heading="Change of mode",
            original_text="Under no circumstances shall the bowler change the mode of delivery without informing the umpire.",
            clause_type=ClauseType.RULE,
            page_start=1,
            page_end=1
        ),
        RuleClause(
            id="ICC_T20I_MEN_2026:21.2",
            source_document_id=t20_2026.id,
            clause_number="21.2",
            parent_clause_id="ICC_T20I_MEN_2026:21",
            heading="Fair delivery - the arm",
            original_text="For a delivery to be fair in respect of the arm the ball must not be thrown.",
            clause_type=ClauseType.RULE,
            page_start=1,
            page_end=1
        ),
        RuleClause(
            id="ICC_T20I_MEN_2026:21.5",
            source_document_id=t20_2026.id,
            clause_number="21.5",
            parent_clause_id="ICC_T20I_MEN_2026:21",
            heading="High full-pitched deliveries",
            original_text="Any delivery which passes or would have passed on the full above waist height of the striker standing upright at the popping crease is unfair and shall be called a No ball.",
            clause_type=ClauseType.RULE,
            page_start=2,
            page_end=2
        ),
        RuleClause(
            id="ICC_T20I_MEN_2026:21.17",
            source_document_id=t20_2026.id,
            clause_number="21.17",
            parent_clause_id="ICC_T20I_MEN_2026:21",
            heading="Dismissals from a No ball",
            original_text="When a No ball has been bowled, neither batter shall be out off that delivery except for Run out, Hit the ball twice or Obstructing the field.",
            clause_type=ClauseType.RULE,
            cross_references=["34", "37", "38"],
            page_start=2,
            page_end=2
        ),
        RuleClause(
            id="ICC_T20I_MEN_2026:21.18",
            source_document_id=t20_2026.id,
            clause_number="21.18",
            parent_clause_id="ICC_T20I_MEN_2026:21",
            heading="Free Hit",
            original_text="21.18 Free Hit. In addition to the above, the delivery following a No ball called shall be a free hit for whichever batter is facing it.",
            clause_type=ClauseType.RULE,
            page_start=2,
            page_end=2
        ),
        RuleClause(
            id="ICC_T20I_MEN_2026:21.18.1",
            source_document_id=t20_2026.id,
            clause_number="21.18.1",
            parent_clause_id="ICC_T20I_MEN_2026:21.18",
            heading="Free Hit Award",
            original_text="In addition to the above, the delivery following a No ball called (all modes of No ball) shall be a free hit for whichever batter is facing it.",
            clause_type=ClauseType.RULE,
            page_start=2,
            page_end=2
        ),
        RuleClause(
            id="ICC_T20I_MEN_2026:21.18.2",
            source_document_id=t20_2026.id,
            clause_number="21.18.2",
            parent_clause_id="ICC_T20I_MEN_2026:21.18",
            heading="Free Hit Dismissals",
            original_text="For any free hit, the striker can be dismissed only under the circumstances that apply for a No ball, even if the delivery for the free hit is called No ball.",
            clause_type=ClauseType.EXCEPTION,
            cross_references=["21.17"],
            page_start=2,
            page_end=2
        ),
        RuleClause(
            id="ICC_T20I_MEN_2026:21.18.3",
            source_document_id=t20_2026.id,
            clause_number="21.18.3",
            parent_clause_id="ICC_T20I_MEN_2026:21.18",
            heading="Field changes on Free Hit",
            original_text="Field changes are not permitted for free hit deliveries unless there is a change of striker (the provisions of clause 41.2 shall apply).",
            clause_type=ClauseType.RULE,
            page_start=2,
            page_end=2
        ),
        RuleClause(
            id="ICC_T20I_MEN_2026:22",
            source_document_id=t20_2026.id,
            clause_number="22",
            heading="WIDE BALL",
            original_text="22 WIDE BALL. Law 22 shall apply subject to the following modifications.",
            clause_type=ClauseType.RULE,
            page_start=3,
            page_end=3
        ),
        RuleClause(
            id="ICC_T20I_MEN_2026:22.1",
            source_document_id=t20_2026.id,
            clause_number="22.1",
            parent_clause_id="ICC_T20I_MEN_2026:22",
            heading="Judging a Wide",
            original_text="22.1 Judging a Wide. If the bowler bowls a ball, not being a No ball, the umpire shall adjudge it a Wide if it passes out of reach.",
            clause_type=ClauseType.RULE,
            page_start=3,
            page_end=3
        ),
        RuleClause(
            id="ICC_T20I_MEN_2026:22.1.1",
            source_document_id=t20_2026.id,
            clause_number="22.1.1",
            parent_clause_id="ICC_T20I_MEN_2026:22.1",
            heading="Judging a Wide Criteria",
            original_text="If the bowler bowls a ball, not being a No ball, the umpire shall adjudge it a Wide if according to the definition it is not a fair delivery.",
            clause_type=ClauseType.RULE,
            page_start=3,
            page_end=3
        ),
        RuleClause(
            id="ICC_T20I_MEN_2026:22.1.2",
            source_document_id=t20_2026.id,
            clause_number="22.1.2",
            parent_clause_id="ICC_T20I_MEN_2026:22.1",
            heading="Batter movement on wide delivery",
            original_text="The ball will be considered not to have passed wide if the batter moves to make contact with the ball, or brings the ball within reach.",
            clause_type=ClauseType.RULE,
            page_start=3,
            page_end=3
        ),
    ]

    # Predecessor T20I 2024 clauses
    clauses_2024 = [
        RuleClause(
            id="ICC_T20I_MEN_2024:21.18",
            source_document_id=t20_2024.id,
            clause_number="21.18",
            heading="Free Hit (2024 Edition)",
            original_text="The delivery following a No ball shall be a free hit (2024 regulation).",
            clause_type=ClauseType.RULE,
            page_start=2,
            page_end=2
        )
    ]

    # Test PC 2026 clauses (Mode of delivery only, NO Free Hit)
    clauses_test = [
        RuleClause(
            id="ICC_TEST_MEN_2026:21.1",
            source_document_id=test_2026.id,
            clause_number="21.1",
            heading="Mode of delivery (Test)",
            original_text="The umpire shall ascertain whether the bowler intends to bowl right handed or left handed in Test matches.",
            clause_type=ClauseType.RULE,
            page_start=1,
            page_end=1
        ),
        RuleClause(
            id="ICC_TEST_MEN_2026:21.2",
            source_document_id=test_2026.id,
            clause_number="21.2",
            heading="Fair delivery the arm (Test)",
            original_text="For a delivery to be fair in respect of the arm the ball must not be thrown in Test cricket.",
            clause_type=ClauseType.RULE,
            page_start=1,
            page_end=1
        )
    ]

    repo.upsert_clauses(clauses + clauses_2024 + clauses_test)
    return repo


def evaluate_configuration(
    service: RetrievalService,
    benchmark_items: List[Dict[str, Any]],
    mode: str = "hybrid"
) -> Dict[str, Any]:
    """Run evaluation for a specified retrieval mode."""
    total_queries = len(benchmark_items)
    recalls_at_1: List[float] = []
    recalls_at_3: List[float] = []
    recalls_at_5: List[float] = []
    recalls_at_10: List[float] = []
    ndcgs_at_5: List[float] = []
    ndcgs_at_10: List[float] = []
    reciprocal_ranks: List[float] = []
    exact_accuracies: List[float] = []
    supporting_recalls: List[float] = []
    leakage_count = 0
    valid_eval_queries = 0

    latencies_sparse: List[float] = []
    latencies_dense: List[float] = []
    latencies_fusion: List[float] = []
    latencies_expansion: List[float] = []
    latencies_total: List[float] = []

    for item in benchmark_items:
        q = item["question"]
        expected_status = item["expected_status"]
        expected_primaries = item["expected_primary_clause_numbers"]
        expected_supporting = item["expected_supporting_clause_numbers"]
        forbidden = set(item.get("forbidden_clause_numbers", []))
        ctx_dict = item.get("match_context")

        ctx: Optional[MatchContext] = None
        if ctx_dict:
            fmt = CricketFormat(ctx_dict["format"]) if "format" in ctx_dict and ctx_dict["format"] else None
            cat = GenderCategory(ctx_dict["category"]) if "category" in ctx_dict and ctx_dict["category"] else None
            ctx = MatchContext(
                cricket_level=ctx_dict.get("cricket_level", "international"),
                competition=ctx_dict.get("competition"),
                format=fmt,
                category=cat,
                series_start_date=ctx_dict.get("series_start_date"),
                match_date=ctx_dict.get("match_date")
            )

        req = RetrievalRequest(
            query=q,
            match_context=ctx,
            top_k_sparse=15,
            top_k_dense=15,
            top_k_fused=5,
            include_parent_context=True,
            include_related_evidence=True
        )

        outcome = service.retrieve(req)

        # Check status agreement
        if expected_status == "CLARIFICATION_REQUIRED":
            if outcome.status == RetrievalStatus.CLARIFICATION_REQUIRED:
                exact_accuracies.append(1.0)
            else:
                exact_accuracies.append(0.0)
            continue

        if outcome.status != RetrievalStatus.SUCCESS:
            recalls_at_5.append(0.0)
            recalls_at_10.append(0.0)
            reciprocal_ranks.append(0.0)
            continue

        valid_eval_queries += 1
        hits = outcome.hits
        primary_hits = [h for h in hits if h.evidence_role == EvidenceRole.PRIMARY]
        retrieved_primary_cnums = [h.clause_number for h in primary_hits]
        all_retrieved_cnums = [h.clause_number for h in hits]

        # 1. Leakage check
        has_leakage = False
        for h in hits:
            if h.clause_number in forbidden:
                has_leakage = True
                break
        if has_leakage:
            leakage_count += 1

        # 2. Recall@1, @3, @5 & @10
        top1_cnums = retrieved_primary_cnums[:1]
        top3_cnums = retrieved_primary_cnums[:3]
        top5_cnums = retrieved_primary_cnums[:5]
        top10_cnums = retrieved_primary_cnums[:10]

        matched_1 = sum(1 for ep in expected_primaries if ep in top1_cnums)
        r_1 = matched_1 / len(expected_primaries) if expected_primaries else 1.0
        recalls_at_1.append(r_1)

        matched_3 = sum(1 for ep in expected_primaries if ep in top3_cnums)
        r_3 = matched_3 / len(expected_primaries) if expected_primaries else 1.0
        recalls_at_3.append(r_3)

        matched_5 = sum(1 for ep in expected_primaries if ep in top5_cnums)
        r_5 = matched_5 / len(expected_primaries) if expected_primaries else 1.0
        recalls_at_5.append(r_5)

        matched_10 = sum(1 for ep in expected_primaries if ep in top10_cnums)
        r_10 = matched_10 / len(expected_primaries) if expected_primaries else 1.0
        recalls_at_10.append(r_10)

        # nDCG@5 & nDCG@10
        def calc_ndcg(cnums: List[str], k: int) -> float:
            dcg = 0.0
            for i, cn in enumerate(cnums[:k]):
                if cn in expected_primaries:
                    dcg += 1.0 / np.log2(i + 2)
            idcg = sum(1.0 / np.log2(i + 2) for i in range(min(k, len(expected_primaries))))
            return dcg / idcg if idcg > 0 else 1.0

        ndcgs_at_5.append(calc_ndcg(retrieved_primary_cnums, 5))
        ndcgs_at_10.append(calc_ndcg(retrieved_primary_cnums, 10))

        # 3. MRR
        rr = 0.0
        for rank_idx, cn in enumerate(retrieved_primary_cnums):
            if cn in expected_primaries:
                rr = 1.0 / (rank_idx + 1)
                break
        reciprocal_ranks.append(rr)

        # 4. Exact clause accuracy (if category is exact_clause_number)
        if item.get("category") == "exact_clause_number":
            if expected_primaries and expected_primaries[0] in top5_cnums:
                exact_accuracies.append(1.0)
            else:
                exact_accuracies.append(0.0)

        # 5. Supporting clause recall (after expansion)
        if expected_supporting:
            matched_supp = sum(1 for es in expected_supporting if es in all_retrieved_cnums)
            supp_recall = matched_supp / len(expected_supporting)
            supporting_recalls.append(supp_recall)

        # 6. Latencies
        diag = outcome.query_diagnostics
        latencies_sparse.append(diag.get("sparse_search_ms", 0.0))
        latencies_dense.append(diag.get("dense_search_ms", 0.0))
        latencies_fusion.append(diag.get("fusion_ms", 0.0))
        latencies_expansion.append(diag.get("expansion_ms", 0.0))
        latencies_total.append(diag.get("total_retrieval_ms", 0.0))

    avg_recall_1 = float(np.mean(recalls_at_1)) if recalls_at_1 else 0.0
    avg_recall_3 = float(np.mean(recalls_at_3)) if recalls_at_3 else 0.0
    avg_recall_5 = float(np.mean(recalls_at_5)) if recalls_at_5 else 0.0
    avg_recall_10 = float(np.mean(recalls_at_10)) if recalls_at_10 else 0.0
    avg_ndcg_5 = float(np.mean(ndcgs_at_5)) if ndcgs_at_5 else 0.0
    avg_ndcg_10 = float(np.mean(ndcgs_at_10)) if ndcgs_at_10 else 0.0
    mrr = float(np.mean(reciprocal_ranks)) if reciprocal_ranks else 0.0
    exact_acc = float(np.mean(exact_accuracies)) if exact_accuracies else 0.0
    supp_recall = float(np.mean(supporting_recalls)) if supporting_recalls else 0.0
    leakage_rate = (leakage_count / valid_eval_queries) * 100.0 if valid_eval_queries > 0 else 0.0

    return {
        "mode": mode,
        "total_queries": total_queries,
        "valid_eval_queries": valid_eval_queries,
        "recall_at_1": round(avg_recall_1 * 100, 2),
        "recall_at_3": round(avg_recall_3 * 100, 2),
        "recall_at_5": round(avg_recall_5 * 100, 2),
        "recall_at_10": round(avg_recall_10 * 100, 2),
        "ndcg_at_5": round(avg_ndcg_5, 4),
        "ndcg_at_10": round(avg_ndcg_10, 4),
        "mrr": round(mrr, 4),
        "exact_clause_accuracy": round(exact_acc * 100, 2),
        "supporting_clause_recall": round(supp_recall * 100, 2),
        "leakage_rate": round(leakage_rate, 2),
        "latencies_ms": {
            "avg_sparse": round(float(np.mean(latencies_sparse)), 2) if latencies_sparse else 0.0,
            "avg_dense": round(float(np.mean(latencies_dense)), 2) if latencies_dense else 0.0,
            "avg_fusion": round(float(np.mean(latencies_fusion)), 2) if latencies_fusion else 0.0,
            "avg_expansion": round(float(np.mean(latencies_expansion)), 2) if latencies_expansion else 0.0,
            "avg_total": round(float(np.mean(latencies_total)), 2) if latencies_total else 0.0,
            "median_total": round(float(np.percentile(latencies_total, 50)), 2) if latencies_total else 0.0,
            "p95_total": round(float(np.percentile(latencies_total, 95)), 2) if latencies_total else 0.0,
            "p99_total": round(float(np.percentile(latencies_total, 99)), 2) if latencies_total else 0.0
        }
    }


def setup_full_corpus_environment(db_path: Path) -> Tuple[CricketIQRepository, SQLiteFTSSearchProvider, EmbeddingStore]:
    """Connect to persistent on-disk full corpus database for benchmark v2 evaluation."""
    engine = create_db_engine(f"sqlite:///{db_path}")
    session = Session(bind=engine)
    repo = CricketIQRepository(session)
    sparse_prov = SQLiteFTSSearchProvider(repo)
    embedder = LocalDeterministicEmbeddingProvider(dimension=384)
    store = EmbeddingStore(repo, embedder)
    return repo, sparse_prov, store


def main():
    benchmark_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evaluation/retrieval/benchmark_v1.jsonl")
    if not benchmark_path.exists():
        print(f"Benchmark file not found at {benchmark_path}")
        return

    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark_items = [json.loads(line) for line in f if line.strip()]

    print(f"Loaded {len(benchmark_items)} evaluation queries from {benchmark_path}")

    db_path = PROJECT_ROOT / "data" / "cricketiq.db"
    if "v2" in benchmark_path.name and db_path.exists():
        print(f"Running against full persistent database at {db_path}...")
        repo, sparse_prov, store = setup_full_corpus_environment(db_path)
        embedder = LocalDeterministicEmbeddingProvider(dimension=384)
        dense_prov = SQLiteNumPyDenseSearchProvider(repo, embedder, store)
    else:
        print("Running against in-memory baseline benchmark environment...")
        repo = setup_benchmark_environment()
        sparse_prov = SQLiteFTSSearchProvider(repo)
        sparse_prov.rebuild_index()
        embedder = LocalDeterministicEmbeddingProvider(dimension=384)
        store = EmbeddingStore(repo, embedder)
        store.build_all_embeddings()
        dense_prov = SQLiteNumPyDenseSearchProvider(repo, embedder, store)

    # 1. Config A: Sparse Only
    service_sparse = RetrievalService(
        repository=repo,
        sparse_provider=sparse_prov,
        dense_provider=None
    )
    res_sparse = evaluate_configuration(service_sparse, benchmark_items, mode="Sparse-Only (SQLite FTS5)")

    # 2. Config B: Dense Only
    # A dummy sparse provider returning empty list to evaluate dense only
    class NullSparseProvider:
        def search(self, *args, **kwargs): return []

    service_dense = RetrievalService(
        repository=repo,
        sparse_provider=NullSparseProvider(),
        dense_provider=dense_prov,
        enable_diagnostic_dense=True
    )
    res_dense = evaluate_configuration(service_dense, benchmark_items, mode="Dense-Only (NumPy Cosine)")

    # 3. Config C: Hybrid (Sparse + Dense + RRF + Expansion)
    service_hybrid = RetrievalService(
        repository=repo,
        sparse_provider=sparse_prov,
        dense_provider=dense_prov,
        enable_diagnostic_dense=True
    )
    res_hybrid = evaluate_configuration(service_hybrid, benchmark_items, mode="Hybrid (Sparse + Dense + RRF + Expansion)")

    results_all = {
        "benchmark_file": str(benchmark_path),
        "total_queries": len(benchmark_items),
        "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "configurations": [res_sparse, res_dense, res_hybrid]
    }

    out_dir = Path("evaluation/retrieval/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_filename = "eval_report_v2.json" if "v2" in benchmark_path.name else "eval_report_v1.json"
    report_file = out_dir / report_filename
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results_all, f, indent=2)

    # Print summary table
    print("\n" + "=" * 100)
    print(f"CRICKETIQ RETRIEVAL BENCHMARK EVALUATION ({len(benchmark_items)} QUERIES - {benchmark_path.name})")
    print("=" * 100)
    print(f"{'Configuration':<42} | {'Recall@5':<9} | {'MRR':<8} | {'Exact Acc':<9} | {'Supp Recall':<11} | {'Leakage':<7} | {'Latency':<8}")
    print("-" * 100)
    for res in [res_sparse, res_dense, res_hybrid]:
        lat = f"{res['latencies_ms']['avg_total']}ms"
        print(f"{res['mode']:<42} | {res['recall_at_5']:>7}% | {res['mrr']:>8} | {res['exact_clause_accuracy']:>8}% | {res['supporting_clause_recall']:>10}% | {res['leakage_rate']:>6}% | {lat:>8}")
    print("=" * 100)
    print(f"\nDetailed JSON report written to: {report_file}")


if __name__ == "__main__":
    main()
