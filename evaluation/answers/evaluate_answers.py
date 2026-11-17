"""Automated Evaluation Runner for Grounded Answer Benchmark (Phase 4 Gate 6).

Evaluates the QueryOrchestrator across 50 golden Q&A cases:
- Status match / conclusion correctness
- Citation identity validity (target: 100%)
- Claim citation coverage (target: 100%)
- Regulatory leakage rate (target: 0.0%)
- Appropriate abstention on domestic, ambiguous, and out-of-scope inquiries (target: 100%)
- Latency percentiles (mean, median, p95)
- Category & format performance breakdowns
"""

from __future__ import annotations
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import Session
from cricketiq.backend.app.database.connection import create_db_engine
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.api.schemas.query import QueryRequest, MatchContextInput
from cricketiq.backend.app.api.schemas.response import QueryStatus
from cricketiq.backend.app.application.query_orchestrator import QueryOrchestrator
from cricketiq.backend.app.database.models import CricketFormat, GenderCategory


def run_benchmark(
    benchmark_file: Path,
    db_path: Path,
    output_report_file: Optional[Path] = None
) -> Dict[str, Any]:
    """Execute evaluation over all benchmark items and compute metrics."""
    engine = create_db_engine(f"sqlite:///{db_path}")
    session = Session(bind=engine)
    repo = CricketIQRepository(session)
    orchestrator = QueryOrchestrator(repository=repo)

    items = []
    with open(benchmark_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))

    print(f"Starting Grounded Answer Benchmark on {len(items)} curated cases...\n")

    results: List[Dict[str, Any]] = []
    latencies: List[float] = []

    total_cases = len(items)
    status_matches = 0
    valid_citation_identities = 0
    total_citations_emitted = 0
    claims_covered = 0
    total_claims_emitted = 0
    leakage_count = 0
    abstention_matches = 0
    total_abstention_expected = 0

    category_stats: Dict[str, Dict[str, int]] = {}

    for i, item in enumerate(items, 1):
        q_id = item["id"]
        q_text = item["question"]
        cat = item["category"]
        exp_status = item["expected_status"]
        fmt_str = item.get("format")
        gender_str = item.get("gender")

        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "status_correct": 0, "citations_valid": 0}
        category_stats[cat]["total"] += 1

        # Format context input if specified
        fmt = None
        if fmt_str == "T20I":
            fmt = CricketFormat.T20I
        elif fmt_str == "ODI":
            fmt = CricketFormat.ODI
        elif fmt_str == "Test":
            fmt = CricketFormat.TEST

        cat_gender = None
        if gender_str == "Men's":
            cat_gender = GenderCategory.MENS
        elif gender_str == "Women's":
            cat_gender = GenderCategory.WOMENS

        ctx_input = None
        if fmt or cat_gender:
            ctx_input = MatchContextInput(format=fmt, category=cat_gender)

        req = QueryRequest(query=q_text, context=ctx_input)

        t0 = time.perf_counter()
        resp = orchestrator.execute(req)
        t_elapsed = (time.perf_counter() - t0) * 1000.0
        latencies.append(t_elapsed)

        actual_status = resp.status.value
        is_status_match = (actual_status == exp_status)
        if is_status_match:
            status_matches += 1
            category_stats[cat]["status_correct"] += 1

        # Check citations
        item_citations_valid = True
        applicable_docs = set(resp.trace.applicable_documents)

        for cit in resp.citations:
            total_citations_emitted += 1
            # Check if clause exists in DB
            db_clause = repo.get_clause(cit.clause_id)
            if db_clause:
                valid_citation_identities += 1
            else:
                item_citations_valid = False

            # Check for regulatory leakage
            if applicable_docs and cit.document_id not in applicable_docs:
                leakage_count += 1

        if item_citations_valid and resp.citations:
            category_stats[cat]["citations_valid"] += 1

        # Check claims
        for claim in resp.claims:
            total_claims_emitted += 1
            if claim.is_verified:
                claims_covered += 1

        # Check abstentions
        if exp_status != "answered":
            total_abstention_expected += 1
            if actual_status == exp_status:
                abstention_matches += 1

        status_flag = "PASS" if is_status_match else "FAIL"
        print(f"[{i:02d}/{total_cases:02d}] {q_id} ({cat}): {actual_status} vs {exp_status} -> {status_flag} ({t_elapsed:.1f}ms)")

        results.append({
            "id": q_id,
            "category": cat,
            "question": q_text,
            "expected_status": exp_status,
            "actual_status": actual_status,
            "status_match": is_status_match,
            "latency_ms": t_elapsed,
            "citations_count": len(resp.citations),
            "citations": [c.clause_id for c in resp.citations],
            "abstention_reason": resp.abstention_reason,
        })

    # Summary Metrics Calculation
    avg_latency = float(np.mean(latencies))
    p50_latency = float(np.median(latencies))
    p95_latency = float(np.percentile(latencies, 95))

    status_accuracy = (status_matches / total_cases) * 100.0
    citation_validity_rate = (
        (valid_citation_identities / total_citations_emitted) * 100.0
        if total_citations_emitted > 0 else 100.0
    )
    claim_coverage_rate = (
        (claims_covered / total_claims_emitted) * 100.0
        if total_claims_emitted > 0 else 100.0
    )
    leakage_rate = (
        (leakage_count / total_citations_emitted) * 100.0
        if total_citations_emitted > 0 else 0.0
    )
    abstention_rate = (
        (abstention_matches / total_abstention_expected) * 100.0
        if total_abstention_expected > 0 else 100.0
    )

    report = {
        "benchmark_file": str(benchmark_file),
        "total_cases": total_cases,
        "metrics": {
            "status_accuracy_pct": status_accuracy,
            "citation_validity_pct": citation_validity_rate,
            "claim_coverage_pct": claim_coverage_rate,
            "regulatory_leakage_pct": leakage_rate,
            "appropriate_abstention_pct": abstention_rate,
            "total_citations_emitted": total_citations_emitted,
            "total_claims_emitted": total_claims_emitted,
            "latency_mean_ms": avg_latency,
            "latency_p50_ms": p50_latency,
            "latency_p95_ms": p95_latency,
        },
        "category_breakdown": category_stats,
        "detailed_results": results,
    }

    print("\n" + "=" * 60)
    print("CRICKETIQ GROUNDED ANSWER BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Total Test Cases:            {total_cases}")
    print(f"Status / Conclusion Match:   {status_accuracy:.1f}% ({status_matches}/{total_cases})")
    print(f"Citation Identity Validity:  {citation_validity_rate:.1f}% ({valid_citation_identities}/{total_citations_emitted})")
    print(f"Claim Citation Coverage:     {claim_coverage_rate:.1f}% ({claims_covered}/{total_claims_emitted})")
    print(f"Regulatory Leakage Rate:     {leakage_rate:.1f}% ({leakage_count}/{total_citations_emitted})")
    print(f"Appropriate Abstention Rate: {abstention_rate:.1f}% ({abstention_matches}/{total_abstention_expected})")
    print(f"Latency Mean / p50 / p95:    {avg_latency:.1f}ms / {p50_latency:.1f}ms / {p95_latency:.1f}ms")
    print("=" * 60)

    if output_report_file:
        with open(output_report_file, "w", encoding="utf-8") as rf:
            json.dump(report, rf, indent=2)
        print(f"\nSaved structured report to {output_report_file}")

    return report


if __name__ == "__main__":
    bench_file = PROJECT_ROOT / "evaluation" / "answers" / "grounded_answer_benchmark_v1.jsonl"
    database = PROJECT_ROOT / "data" / "cricketiq.db"
    out_rep = PROJECT_ROOT / "evaluation" / "answers" / "grounded_answer_benchmark_report_v1.json"
    run_benchmark(bench_file, database, out_rep)
