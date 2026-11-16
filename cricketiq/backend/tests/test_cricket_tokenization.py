"""Tests for Cricket Tokenization and Linguistic Diagnostics in CricketIQ."""

import pytest
from cricketiq.backend.app.nlp.tokenization_evaluator import (
    TokenizationEvaluator, CRICKET_EVAL_SAMPLES
)


@pytest.fixture
def evaluator():
    return TokenizationEvaluator(max_sequence_length=512)


def test_extract_exact_identifiers(evaluator):
    text = (
        "Under Clause 21.18.2, a striker cannot be out Bowled or Caught. "
        "Only Law 34, Law 37 or Law 38 dismissals apply on a free hit."
    )
    ids = evaluator.extract_identifiers(text)
    assert "21.18.2" in ids
    assert "34" in ids
    assert "37" in ids
    assert "38" in ids


def test_tokenization_preserves_negation_and_conditions(evaluator):
    sample = {
        "id": "test_negation",
        "category": "legal_semantics",
        "text": "Neither batter can be out, unless the ball is dead, except under Law 38.",
        "expected_identifiers": ["Law 38"],
        "critical_terms": ["neither", "unless", "except"]
    }
    res = evaluator.evaluate_sample(sample)
    assert res.negation_preserved is True
    assert res.identifiers_preserved is True
    assert "38" in res.identifiers_detected


def test_hyphenated_compound_evaluation(evaluator):
    sample = {
        "id": "test_hyphens",
        "category": "compounds",
        "text": "A no-ball delivery entitles the batter to a free-hit next ball.",
        "expected_identifiers": [],
        "critical_terms": ["no-ball", "free-hit"]
    }
    res = evaluator.evaluate_sample(sample)
    assert res.hyphens_handled is True


def test_batch_tokenization_evaluation(evaluator):
    results = evaluator.evaluate_all(CRICKET_EVAL_SAMPLES)
    assert results["total_samples"] == len(CRICKET_EVAL_SAMPLES)
    assert results["identifier_preservation_rate"] == 100.0
    assert results["negation_preservation_rate"] == 100.0
    assert results["hyphen_compound_handling_rate"] == 100.0
    assert results["truncation_risk_rate"] == 0.0
